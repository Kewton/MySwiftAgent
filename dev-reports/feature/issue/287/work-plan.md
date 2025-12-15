# 作業計画書: Issue #287 - APIクライアント境界（アダプタ層）

## 1. 基本情報

| 項目 | 内容 |
|------|------|
| Issue番号 | #287 |
| タイトル | [myAgentDesk] #279-3: APIクライアント境界（アダプタ層） |
| 親Issue | #279 (myAgentDesk MVP再構築) |
| サイズ | M (5 SP) |
| 見積時間 | 12時間 (1.5日) |
| 担当者 | Claude |
| 作成日 | 2025-12-16 |

## 2. スコープ

### 2.1 実装対象

| コンポーネント | 説明 | 優先度 |
|---------------|------|--------|
| **ApiClient基底クラス** | Service Token認証、リトライ、エラーハンドリング | P1 |
| **ExpertAgentClient** | Job Generator API連携 | P1 |
| **JobQueueClient** | JobMaster/Run管理 | P1 |
| **MySchedulerClient** | スケジュール管理 | P1 |
| **MyVaultClient** | Project/シークレット管理 | P1 |
| **LangfuseClient** | トレース取得 | P2 |
| **MockAdapterFactory** | 開発時モック切替 | P1 |
| **Result<T, E>型** | 統一エラーハンドリング | P1 |

### 2.2 設計準拠

- **design-policy.md 6.3**: エラーハンドリング方針
- **service-dependencies.md**: API仕様・認証方式
- **API_REFERENCE.md**: ExpertAgent API仕様

### 2.3 スコープ外

- 実際のバックエンドサービス接続テスト（受入テストで実施）
- UIコンポーネント実装
- 状態管理（stores）実装

## 3. 技術仕様

### 3.1 ディレクトリ構造

```
src/lib/api/
├── index.ts                    # エクスポート集約
├── types.ts                    # 共通型定義
├── result.ts                   # Result<T, E>型
├── errors.ts                   # エラー型定義
├── base/
│   ├── api-client.ts          # ApiClient基底クラス
│   ├── retry-handler.ts       # リトライロジック
│   └── circuit-breaker.ts     # サーキットブレーカー
├── clients/
│   ├── expert-agent.ts        # ExpertAgentClient
│   ├── job-queue.ts           # JobQueueClient
│   ├── my-scheduler.ts        # MySchedulerClient
│   ├── my-vault.ts            # MyVaultClient
│   └── langfuse.ts            # LangfuseClient
├── mock/
│   ├── adapter-factory.ts     # MockAdapterFactory
│   ├── expert-agent.mock.ts   # ExpertAgentClientMock
│   ├── job-queue.mock.ts      # JobQueueClientMock
│   ├── my-scheduler.mock.ts   # MySchedulerClientMock
│   ├── my-vault.mock.ts       # MyVaultClientMock
│   └── langfuse.mock.ts       # LangfuseClientMock
└── config.ts                   # API設定
```

### 3.2 共通型定義

```typescript
// src/lib/api/result.ts
export type Result<T, E = ApiError> =
  | { success: true; data: T }
  | { success: false; error: E };

// src/lib/api/errors.ts
export type ServiceErrorType =
  | 'network'
  | 'timeout'
  | 'server'
  | 'auth'
  | 'validation'
  | 'not_found'
  | 'rate_limit';

export interface ApiError {
  type: ServiceErrorType;
  message: string;
  code?: string;
  retryable: boolean;
  retryAfter?: number;
  details?: Record<string, string[]>;
}
```

### 3.3 基底クラス設計

```typescript
// src/lib/api/base/api-client.ts
export interface ApiClientConfig {
  baseUrl: string;
  serviceName?: string;
  serviceToken?: string;
  timeout?: number;
  maxRetries?: number;
  retryDelay?: number;
}

export abstract class ApiClient {
  protected config: ApiClientConfig;
  protected circuitBreaker: CircuitBreaker;

  constructor(config: ApiClientConfig) {
    this.config = {
      timeout: 30000,
      maxRetries: 3,
      retryDelay: 1000,
      ...config
    };
    this.circuitBreaker = new CircuitBreaker();
  }

  protected async fetch<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<Result<T>> {
    return this.circuitBreaker.execute(async () => {
      return fetchWithRetry<T>(
        () => this.doFetch<T>(endpoint, options),
        {
          maxAttempts: this.config.maxRetries!,
          baseDelay: this.config.retryDelay!,
        }
      );
    });
  }

  protected abstract getHeaders(): HeadersInit;
}
```

### 3.4 サービス別API仕様

#### ExpertAgentClient

| メソッド | エンドポイント | 説明 |
|---------|--------------|------|
| `generateJob()` | POST /aiagent-api/v1/job-generator | Job生成開始 |
| `getJobStatus()` | GET /aiagent-api/v1/jobs/{job_id}/status | 生成状態確認 |
| `generateWorkflow()` | POST /aiagent-api/v1/workflow-generator | Workflow生成 |
| `getMarpReport()` | POST /aiagent-api/v1/marp-report | Marpレポート生成 |

```typescript
// src/lib/api/clients/expert-agent.ts
export class ExpertAgentClient extends ApiClient {
  async generateJob(request: JobGeneratorRequest): Promise<Result<JobGeneratorResponse>>;
  async getJobStatus(jobId: string): Promise<Result<JobStatusResponse>>;
  async generateWorkflow(request: WorkflowGeneratorRequest): Promise<Result<WorkflowGeneratorResponse>>;
  async getMarpReport(request: MarpReportRequest): Promise<Result<MarpReportResponse>>;
}
```

#### JobQueueClient

| メソッド | エンドポイント | 説明 |
|---------|--------------|------|
| `getJobMasters()` | GET /api/v1/job-masters | JobMaster一覧 |
| `getJobMaster()` | GET /api/v1/job-masters/{id} | JobMaster詳細 |
| `createRun()` | POST /api/v1/job-masters/{id}/runs | Run作成 |
| `getRuns()` | GET /api/v1/runs | Run一覧 |
| `getRun()` | GET /api/v1/runs/{id} | Run詳細 |

```typescript
// src/lib/api/clients/job-queue.ts
export class JobQueueClient extends ApiClient {
  async getJobMasters(params?: JobMasterListParams): Promise<Result<JobMaster[]>>;
  async getJobMaster(id: string): Promise<Result<JobMaster>>;
  async createRun(jobMasterId: string, params?: RunCreateParams): Promise<Result<Run>>;
  async getRuns(params?: RunListParams): Promise<Result<Run[]>>;
  async getRun(id: string): Promise<Result<Run>>;
}
```

#### MySchedulerClient

| メソッド | エンドポイント | 説明 |
|---------|--------------|------|
| `getSchedules()` | GET /api/v1/schedules | スケジュール一覧 |
| `getSchedule()` | GET /api/v1/schedules/{id} | スケジュール詳細 |
| `createSchedule()` | POST /api/v1/schedules | スケジュール作成 |
| `updateSchedule()` | PUT /api/v1/schedules/{id} | スケジュール更新 |
| `enableSchedule()` | POST /api/v1/schedules/{id}/enable | 有効化 |
| `disableSchedule()` | POST /api/v1/schedules/{id}/disable | 無効化 |

```typescript
// src/lib/api/clients/my-scheduler.ts
export class MySchedulerClient extends ApiClient {
  async getSchedules(params?: ScheduleListParams): Promise<Result<Schedule[]>>;
  async getSchedule(id: string): Promise<Result<Schedule>>;
  async createSchedule(schedule: ScheduleCreate): Promise<Result<Schedule>>;
  async updateSchedule(id: string, schedule: ScheduleUpdate): Promise<Result<Schedule>>;
  async enableSchedule(id: string): Promise<Result<void>>;
  async disableSchedule(id: string): Promise<Result<void>>;
}
```

#### MyVaultClient

| メソッド | エンドポイント | 説明 |
|---------|--------------|------|
| `getProjects()` | GET /api/v1/projects | プロジェクト一覧 |
| `getProject()` | GET /api/v1/projects/{id} | プロジェクト詳細 |
| `createProject()` | POST /api/v1/projects | プロジェクト作成 |
| `getSecrets()` | GET /api/v1/secrets/{service}/{project} | シークレット一覧 |

```typescript
// src/lib/api/clients/my-vault.ts
export class MyVaultClient extends ApiClient {
  async getProjects(): Promise<Result<Project[]>>;
  async getProject(id: string): Promise<Result<Project>>;
  async createProject(project: ProjectCreate): Promise<Result<Project>>;
  async getSecrets(service: string, project: string): Promise<Result<Secret[]>>;
}
```

#### LangfuseClient

| メソッド | エンドポイント | 説明 |
|---------|--------------|------|
| `getTraces()` | GET /api/public/traces | トレース一覧 |
| `getTrace()` | GET /api/public/traces/{id} | トレース詳細 |

```typescript
// src/lib/api/clients/langfuse.ts
export class LangfuseClient extends ApiClient {
  async getTraces(params?: TraceListParams): Promise<Result<Trace[]>>;
  async getTrace(id: string): Promise<Result<TraceDetail>>;
}
```

### 3.5 モックアダプタ設計

```typescript
// src/lib/api/mock/adapter-factory.ts
export type ApiMode = 'mock' | 'real';

export interface ApiClients {
  expertAgent: ExpertAgentClient;
  jobQueue: JobQueueClient;
  scheduler: MySchedulerClient;
  vault: MyVaultClient;
  langfuse: LangfuseClient;
}

export function createApiClients(mode: ApiMode = 'real'): ApiClients {
  if (mode === 'mock') {
    return {
      expertAgent: new ExpertAgentClientMock(),
      jobQueue: new JobQueueClientMock(),
      scheduler: new MySchedulerClientMock(),
      vault: new MyVaultClientMock(),
      langfuse: new LangfuseClientMock(),
    };
  }

  return {
    expertAgent: new ExpertAgentClient({ baseUrl: env.EXPERT_AGENT_URL }),
    jobQueue: new JobQueueClient({ baseUrl: env.JOB_QUEUE_URL }),
    scheduler: new MySchedulerClient({ baseUrl: env.MY_SCHEDULER_URL }),
    vault: new MyVaultClient({ baseUrl: env.MY_VAULT_URL }),
    langfuse: new LangfuseClient({ baseUrl: env.LANGFUSE_URL }),
  };
}
```

### 3.6 エラーハンドリング仕様

| エラー種別 | HTTPステータス | リトライ | UI対応 |
|-----------|--------------|---------|--------|
| network | - | Yes (3回) | リトライボタン表示 |
| timeout | 408/504 | Yes (2回) | 「処理に時間がかかっています」 |
| server | 5xx | Yes (2回) | リトライボタン |
| auth | 401/403 | No | Vault設定画面へ誘導 |
| validation | 400/422 | No | フィールド別エラー表示 |
| not_found | 404 | No | 前の画面へ戻る |
| rate_limit | 429 | Yes (指数バックオフ) | 待機時間表示 |

## 4. 実装フェーズ

### Phase 1: 基盤実装 (4時間)

| タスク | 成果物 | 所要時間 |
|--------|--------|---------|
| Result<T, E>型定義 | `result.ts` | 0.5h |
| ApiError型定義 | `errors.ts` | 0.5h |
| RetryHandler実装 | `retry-handler.ts` | 1h |
| CircuitBreaker実装 | `circuit-breaker.ts` | 1h |
| ApiClient基底クラス | `api-client.ts` | 1h |

### Phase 2: クライアント実装 (4時間)

| タスク | 成果物 | 所要時間 |
|--------|--------|---------|
| ExpertAgentClient | `expert-agent.ts` | 1h |
| JobQueueClient | `job-queue.ts` | 1h |
| MySchedulerClient | `my-scheduler.ts` | 0.75h |
| MyVaultClient | `my-vault.ts` | 0.5h |
| LangfuseClient | `langfuse.ts` | 0.5h |
| API設定・エクスポート | `config.ts`, `index.ts` | 0.25h |

### Phase 3: モック実装 (2時間)

| タスク | 成果物 | 所要時間 |
|--------|--------|---------|
| ExpertAgentClientMock | `expert-agent.mock.ts` | 0.5h |
| JobQueueClientMock | `job-queue.mock.ts` | 0.5h |
| MySchedulerClientMock | `my-scheduler.mock.ts` | 0.25h |
| MyVaultClientMock | `my-vault.mock.ts` | 0.25h |
| LangfuseClientMock | `langfuse.mock.ts` | 0.25h |
| MockAdapterFactory | `adapter-factory.ts` | 0.25h |

### Phase 4: 単体テスト (1.5時間)

| テスト対象 | テストファイル | テストケース数 |
|-----------|--------------|--------------|
| Result型 | `result.test.ts` | 5 |
| RetryHandler | `retry-handler.test.ts` | 8 |
| CircuitBreaker | `circuit-breaker.test.ts` | 10 |
| ExpertAgentClient | `expert-agent.test.ts` | 12 |
| JobQueueClient | `job-queue.test.ts` | 10 |
| MySchedulerClient | `my-scheduler.test.ts` | 8 |
| MyVaultClient | `my-vault.test.ts` | 6 |
| LangfuseClient | `langfuse.test.ts` | 5 |
| MockAdapterFactory | `adapter-factory.test.ts` | 4 |

合計: 68テストケース

### Phase 5: L3受入テスト (0.5時間)

```bash
#!/bin/bash
# tests/acceptance/issue-287-api-client.sh

echo "=== Issue #287: APIクライアント境界 受入テスト ==="

# 前提: npm run devでmyAgentDeskが起動していること

# 1. モック切替テスト
echo "1. モック切替テスト..."
curl -s http://localhost:8000/api/test/mode | grep -q "mock" && echo "✅ モックモード動作確認" || echo "❌ モックモード失敗"

# 2. Result型エラーハンドリングテスト
echo "2. エラーハンドリングテスト..."
# 404エラーが適切にハンドリングされることを確認
curl -s http://localhost:8000/api/projects/nonexistent | grep -q "not_found" && echo "✅ 404エラーハンドリング" || echo "❌ 404エラーハンドリング失敗"

# 3. リトライ動作テスト
echo "3. リトライ動作テスト..."
# サーバーエラー時のリトライ動作確認

# 4. サーキットブレーカーテスト
echo "4. サーキットブレーカーテスト..."
# 連続障害時のサーキットオープン確認

echo "=== 受入テスト完了 ==="
```

## 5. 受入基準

### 5.1 機能要件

- [ ] Result<T, E>型でAPI応答を統一的にラップ
- [ ] 5つのAPIクライアント(ExpertAgent, JobQueue, MyScheduler, MyVault, Langfuse)が実装
- [ ] モック/リアル切替が環境変数で制御可能
- [ ] リトライロジックが指数バックオフで動作
- [ ] サーキットブレーカーが連続障害を検知

### 5.2 品質要件

- [ ] 単体テストカバレッジ 90%以上
- [ ] Ruff lintエラーなし
- [ ] TypeScript型チェックエラーなし
- [ ] 全テストケースPASS

### 5.3 コード品質

- [ ] SOLID原則準拠
- [ ] DRY原則準拠（共通ロジックの抽出）
- [ ] 適切なエラーメッセージ（日本語）

## 6. リスクと対策

| リスク | 影響度 | 発生確率 | 対策 |
|-------|-------|---------|------|
| API仕様変更 | 中 | 低 | 型定義を分離、変更に強い設計 |
| モックデータ不整合 | 低 | 中 | 共通型定義からモックデータ生成 |
| リトライ無限ループ | 高 | 低 | 最大リトライ回数制限、タイムアウト設定 |

## 7. 参照ドキュメント

| ドキュメント | 参照箇所 |
|-------------|---------|
| [design-policy.md](../279/design-policy.md) | 6.3 エラーハンドリング方針 |
| [service-dependencies.md](../../../docs/arch/service-dependencies.md) | API仕様・認証方式 |
| [API_REFERENCE.md](../../../expertAgent/docs/API_REFERENCE.md) | ExpertAgent API仕様 |
| [er-diagram.md](../279/er-diagram.md) | エンティティ定義 |

## 8. タイムライン

| フェーズ | 開始 | 終了 | 所要時間 |
|---------|------|------|---------|
| Phase 1: 基盤実装 | Day 1 AM | Day 1 PM | 4h |
| Phase 2: クライアント実装 | Day 1 PM | Day 2 AM | 4h |
| Phase 3: モック実装 | Day 2 AM | Day 2 PM | 2h |
| Phase 4: 単体テスト | Day 2 PM | Day 2 PM | 1.5h |
| Phase 5: L3受入テスト | Day 2 PM | Day 2 PM | 0.5h |

**合計: 12時間 (1.5日)**

## 9. 成果物一覧

### 9.1 ソースコード

| ファイル | 説明 | 行数(推定) |
|---------|------|-----------|
| `src/lib/api/result.ts` | Result型定義 | 30 |
| `src/lib/api/errors.ts` | エラー型定義 | 50 |
| `src/lib/api/base/api-client.ts` | 基底クラス | 100 |
| `src/lib/api/base/retry-handler.ts` | リトライ | 80 |
| `src/lib/api/base/circuit-breaker.ts` | サーキットブレーカー | 80 |
| `src/lib/api/clients/expert-agent.ts` | ExpertAgentClient | 120 |
| `src/lib/api/clients/job-queue.ts` | JobQueueClient | 100 |
| `src/lib/api/clients/my-scheduler.ts` | MySchedulerClient | 80 |
| `src/lib/api/clients/my-vault.ts` | MyVaultClient | 60 |
| `src/lib/api/clients/langfuse.ts` | LangfuseClient | 50 |
| `src/lib/api/mock/*.ts` | モック実装 (6ファイル) | 300 |
| `src/lib/api/types.ts` | 共通型定義 | 150 |
| `src/lib/api/config.ts` | API設定 | 40 |
| `src/lib/api/index.ts` | エクスポート | 30 |

合計: 約1,270行

### 9.2 テストコード

| ファイル | テストケース数 |
|---------|--------------|
| `src/lib/api/__tests__/result.test.ts` | 5 |
| `src/lib/api/__tests__/retry-handler.test.ts` | 8 |
| `src/lib/api/__tests__/circuit-breaker.test.ts` | 10 |
| `src/lib/api/__tests__/expert-agent.test.ts` | 12 |
| `src/lib/api/__tests__/job-queue.test.ts` | 10 |
| `src/lib/api/__tests__/my-scheduler.test.ts` | 8 |
| `src/lib/api/__tests__/my-vault.test.ts` | 6 |
| `src/lib/api/__tests__/langfuse.test.ts` | 5 |
| `src/lib/api/__tests__/adapter-factory.test.ts` | 4 |

合計: 68テストケース

---

**作成者**: Claude
**作成日**: 2025-12-16
**ステータス**: レビュー待ち
