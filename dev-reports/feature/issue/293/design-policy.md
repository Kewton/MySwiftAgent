# Issue #293 設計方針書

## Runs画面（実行履歴・監視）

| 項目 | 値 |
|------|-----|
| Issue番号 | #293 |
| 親Issue | #279 (myAgentDesk画面実装) |
| サブIssue番号 | #279-9 |
| 優先度 | P1 |
| 見積 | L (8 SP) |
| 作成日 | 2025-12-26 |

---

## 1. 現状調査サマリ

### 1.1 Issue要件

**目的**: Job実行履歴の閲覧とリアルタイムステータス監視機能の実装

**主要機能**:
1. Runs一覧画面 (`/workbenches/:workbenchId/runs`)
2. Run詳細画面 (`/runs/:runId`)
3. Run開始機能（JobVersionから）
4. Rerun機能（失敗時）

**技術要件**:
- JobQueue APIとの連携
- ポーリングパターン（5秒間隔）でリアルタイム更新
- 依存Issue: #279-3 (APIクライアント), #279-8 (Review画面)

### 1.2 既存資産調査結果

#### データベーススキーマ（既存）

`run`テーブルが既に定義済み:

```typescript
// src/lib/server/db/schema.ts
export const run = sqliteTable('run', {
  id: text('id').primaryKey(),
  workbenchId: text('workbench_id').notNull().references(() => workbench.id),
  jobVersionId: text('job_version_id').notNull().references(() => jobVersion.id),
  status: text('status', {
    enum: ['queued', 'running', 'success', 'failed', 'canceled', 'timeout']
  }).default('queued'),
  externalJobId: text('external_job_id'),
  externalTraceId: text('external_trace_id'),
  executionParams: text('execution_params'),
  resultSummary: text('result_summary'),
  startedAt: integer('started_at', { mode: 'timestamp' }),
  completedAt: integer('completed_at', { mode: 'timestamp' }),
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
  updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull()
});
```

#### 既存ポーリング設定

```typescript
// src/lib/types/job-version.ts
export const POLLING_CONFIG = {
  intervalMs: 1000,       // 現在1秒間隔
  maxDurationMs: 900000   // 15分タイムアウト
} as const;
```

**設計判断**: Issue要件では5秒間隔だが、既存コードは1秒間隔。Runs画面では5秒間隔を採用し、用途別に設定を分離する。

#### JobQueueClient（既存）

```typescript
// src/lib/api/clients/job-queue.ts
export class JobQueueClient extends ApiClient {
  async createJob(request: CreateJobRequest): Promise<Result<JobResponse, ApiError>>
  async getJobs(filter?: JobListFilter): Promise<Result<JobResponse[], ApiError>>
  async getJob(jobId: string): Promise<Result<JobResponse, ApiError>>
  async updateJob(jobId: string, update: Partial<JobResponse>): Promise<Result<JobResponse, ApiError>>
}
```

#### 既存ポーリング実装パターン

```typescript
// src/routes/api/jobs/[jobId]/status/+server.ts
// サーバーサイド「スマートポーリング」パターン
export const GET: RequestHandler = async ({ params }) => {
  const maxWaitMs = 10000;  // 最大10秒待機
  const checkInterval = 500; // 500ms間隔でチェック
  // Long-polling的なアプローチ
};
```

---

## 2. アーキテクチャ設計

### 2.1 コンポーネント構成

```
myAgentDesk/src/
├── routes/
│   ├── projects/[projectId]/workbenches/[workbenchId]/runs/
│   │   ├── +page.svelte          # Runs一覧画面
│   │   ├── +page.server.ts       # サーバーサイドデータ取得
│   │   └── +layout.ts            # レイアウト設定
│   └── runs/[runId]/
│       ├── +page.svelte          # Run詳細画面
│       ├── +page.server.ts       # サーバーサイドデータ取得
│       └── components/
│           ├── RunStatusBadge.svelte
│           ├── RunTimeline.svelte
│           └── RunLogViewer.svelte
├── lib/
│   ├── components/runs/
│   │   ├── RunCard.svelte        # Run情報カード
│   │   ├── RunList.svelte        # Runs一覧コンポーネント
│   │   └── RunActions.svelte     # アクションボタン群
│   ├── server/
│   │   └── repositories/
│   │       └── run.ts            # Runリポジトリ（新規）
│   └── stores/
│       └── run-polling.svelte.ts # ポーリング状態管理
```

### 2.2 データフロー

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  ┌───────────────┐    ┌────────────────┐    ┌────────────┐ │
│  │ Runs一覧画面  │    │ Run詳細画面    │    │ Polling    │ │
│  │ +page.svelte  │◄───│ +page.svelte   │◄───│ Store      │ │
│  └───────┬───────┘    └───────┬────────┘    └─────┬──────┘ │
│          │                    │                    │        │
│          ▼                    ▼                    ▼        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              SvelteKit Server (+page.server.ts)         │ │
│  └───────────────────────────┬─────────────────────────────┘ │
│                              │                               │
└──────────────────────────────┼───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                     Backend Services                          │
│  ┌──────────────┐          ┌───────────────┐                 │
│  │ SQLite DB    │◄────────►│ JobQueue API  │                 │
│  │ (run table)  │          │ (port 8101)   │                 │
│  └──────────────┘          └───────────────┘                 │
└──────────────────────────────────────────────────────────────┘
```

### 2.3 状態同期戦略

| 画面 | 戦略 | 理由 |
|------|------|------|
| Runs一覧 | 初回SSR + 手動リフレッシュ | 大量データのポーリングは非効率 |
| Run詳細（実行中） | ポーリング（5秒間隔） | リアルタイム性が必要 |
| Run詳細（完了） | 静的表示 | 状態変化なし |

---

## 3. 技術選定

### 3.1 フロントエンド

| 技術 | バージョン | 用途 |
|------|-----------|------|
| SvelteKit | 2.49 | SSRフレームワーク |
| Svelte 5 | runes API | リアクティブUI |
| TailwindCSS | 4 | スタイリング |

### 3.2 バックエンド

| 技術 | 用途 |
|------|------|
| Drizzle ORM | SQLiteアクセス |
| SQLite | ローカルDB |
| JobQueue API | 外部ジョブ管理 |

### 3.3 Svelte 5 Runes API使用方針

```typescript
// 推奨パターン
let status = $state<RunStatus>('queued');           // リアクティブ変数
let isRunning = $derived(status === 'running');     // 派生値
$effect(() => {                                      // 副作用
  if (isRunning) startPolling();
  return () => stopPolling();
});
```

---

## 4. 設計パターン

### 4.1 ポーリングパターン

```typescript
// src/lib/stores/run-polling.svelte.ts
export const RUN_POLLING_CONFIG = {
  intervalMs: 5000,        // 5秒間隔（Issue要件）
  maxDurationMs: 1800000   // 30分タイムアウト
} as const;

export function createRunPollingStore(runId: string) {
  let status = $state<RunStatus>('queued');
  let isPolling = $state(false);
  let error = $state<string | null>(null);

  let intervalId: ReturnType<typeof setInterval> | null = null;

  function startPolling() {
    if (isPolling) return;
    isPolling = true;

    intervalId = setInterval(async () => {
      const result = await fetchRunStatus(runId);
      if (result.ok) {
        status = result.value.status;
        if (isTerminalStatus(status)) {
          stopPolling();
        }
      } else {
        error = result.error.message;
      }
    }, RUN_POLLING_CONFIG.intervalMs);
  }

  function stopPolling() {
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
    }
    isPolling = false;
  }

  return {
    get status() { return status; },
    get isPolling() { return isPolling; },
    get error() { return error; },
    startPolling,
    stopPolling
  };
}
```

### 4.2 リポジトリパターン

```typescript
// src/lib/server/repositories/run.ts
export class RunRepository {
  constructor(private db: Database) {}

  async findById(id: string): Promise<Run | null> {
    return this.db.query.run.findFirst({
      where: eq(run.id, id),
      with: { jobVersion: true }
    });
  }

  async findByWorkbenchId(
    workbenchId: string,
    options?: { limit?: number; offset?: number }
  ): Promise<Run[]> {
    return this.db.query.run.findMany({
      where: eq(run.workbenchId, workbenchId),
      orderBy: [desc(run.createdAt)],
      limit: options?.limit ?? 50,
      offset: options?.offset ?? 0
    });
  }

  async create(data: InsertRun): Promise<Run> {
    const [created] = await this.db.insert(run).values({
      ...data,
      id: generateId(),
      createdAt: new Date(),
      updatedAt: new Date()
    }).returning();
    return created;
  }

  async updateStatus(id: string, status: RunStatus): Promise<Run | null> {
    const now = new Date();
    const updates: Partial<Run> = {
      status,
      updatedAt: now
    };

    if (status === 'running') {
      updates.startedAt = now;
    } else if (isTerminalStatus(status)) {
      updates.completedAt = now;
    }

    const [updated] = await this.db.update(run)
      .set(updates)
      .where(eq(run.id, id))
      .returning();
    return updated ?? null;
  }
}
```

### 4.3 結果型パターン（既存踏襲）

```typescript
// src/lib/types/result.ts
export type Result<T, E> =
  | { ok: true; value: T }
  | { ok: false; error: E };

// 使用例
async function startRun(jobVersionId: string): Promise<Result<Run, ApiError>> {
  try {
    const run = await runRepository.create({ jobVersionId });
    const jobResult = await jobQueueClient.createJob({ runId: run.id });

    if (!jobResult.ok) {
      return { ok: false, error: jobResult.error };
    }

    return { ok: true, value: run };
  } catch (e) {
    return { ok: false, error: { code: 'INTERNAL', message: String(e) } };
  }
}
```

---

## 5. データモデル設計

### 5.1 型定義

```typescript
// src/lib/types/run.ts
export type RunStatus =
  | 'queued'
  | 'running'
  | 'success'
  | 'failed'
  | 'canceled'
  | 'timeout';

export interface Run {
  id: string;
  workbenchId: string;
  jobVersionId: string;
  status: RunStatus;
  externalJobId: string | null;
  externalTraceId: string | null;
  executionParams: Record<string, unknown> | null;
  resultSummary: string | null;
  startedAt: Date | null;
  completedAt: Date | null;
  createdAt: Date;
  updatedAt: Date;
}

export interface RunWithJobVersion extends Run {
  jobVersion: JobVersion;
}

export interface RunListItem {
  id: string;
  status: RunStatus;
  jobVersionName: string;
  startedAt: Date | null;
  completedAt: Date | null;
  duration: number | null;  // ミリ秒
}
```

### 5.2 ステータス遷移図

```
          ┌──────────────────────────────────────────┐
          │                                          │
          ▼                                          │
     ┌────────┐                                      │
     │ queued │───────────────┐                      │
     └────────┘               │                      │
          │                   │                      │
          ▼                   ▼                      │
     ┌─────────┐         ┌──────────┐               │
     │ running │────────►│ canceled │               │
     └─────────┘         └──────────┘               │
          │                                          │
          ├─────────────────────────────────────────┘
          │               │               │
          ▼               ▼               ▼
     ┌─────────┐    ┌──────────┐    ┌─────────┐
     │ success │    │  failed  │    │ timeout │
     └─────────┘    └──────────┘    └─────────┘
```

### 5.3 終了ステータス判定

```typescript
const TERMINAL_STATUSES: RunStatus[] = ['success', 'failed', 'canceled', 'timeout'];

export function isTerminalStatus(status: RunStatus): boolean {
  return TERMINAL_STATUSES.includes(status);
}

export function isRerunnable(status: RunStatus): boolean {
  return status === 'failed' || status === 'timeout';
}
```

---

## 6. API設計

### 6.1 内部API（SvelteKit）

#### Runs一覧取得

```
GET /api/workbenches/:workbenchId/runs
Query: ?page=1&limit=20&status=running

Response:
{
  "runs": RunListItem[],
  "total": number,
  "page": number,
  "limit": number
}
```

#### Run詳細取得

```
GET /api/runs/:runId

Response: RunWithJobVersion
```

#### Run開始

```
POST /api/runs
Body: { "jobVersionId": string, "params"?: object }

Response: Run
```

#### Rerun

```
POST /api/runs/:runId/rerun

Response: Run  // 新しいRunが作成される
```

#### ステータスポーリング

```
GET /api/runs/:runId/status

Response: { "status": RunStatus, "updatedAt": string }
```

### 6.2 外部API連携（JobQueue）

```typescript
// JobQueue APIとの連携
interface JobQueueIntegration {
  // Run開始時
  createJob(runId: string, params: object): Promise<{ jobId: string }>;

  // ステータス同期
  getJobStatus(jobId: string): Promise<{ status: string; result?: object }>;

  // キャンセル
  cancelJob(jobId: string): Promise<void>;
}
```

---

## 7. セキュリティ設計

### 7.1 認証・認可

| 項目 | 実装方針 |
|------|----------|
| 認証 | セッションベース（既存踏襲） |
| 認可 | Workbench所有者のみアクセス可能 |
| CSRF | SvelteKit標準機能使用 |

### 7.2 入力検証

```typescript
// src/lib/validation/run.ts
import { z } from 'zod';

export const createRunSchema = z.object({
  jobVersionId: z.string().uuid(),
  params: z.record(z.unknown()).optional()
});

export const runIdSchema = z.string().uuid();
```

### 7.3 外部API通信

- JobQueue APIへは`X-API-Token`ヘッダーで認証
- TLS必須（本番環境）
- タイムアウト設定: 30秒

---

## 8. パフォーマンス設計

### 8.1 ポーリング最適化

| 戦略 | 実装 |
|------|------|
| 条件付きポーリング | 実行中ステータスのみポーリング |
| バックオフ | エラー時は間隔を2倍に延長 |
| 画面離脱時停止 | `$effect`のクリーンアップで自動停止 |

```typescript
$effect(() => {
  if (run.status === 'running') {
    const polling = createRunPollingStore(run.id);
    polling.startPolling();
    return () => polling.stopPolling();
  }
});
```

### 8.2 データ取得最適化

| 画面 | 戦略 |
|------|------|
| Runs一覧 | ページネーション（20件/ページ） |
| Run詳細 | 必要フィールドのみ取得 |
| ステータス更新 | 軽量エンドポイント使用 |

### 8.3 キャッシュ戦略

```typescript
// SvelteKit load関数でのキャッシュ
export const load: PageServerLoad = async ({ params, setHeaders }) => {
  const run = await runRepository.findById(params.runId);

  if (isTerminalStatus(run.status)) {
    // 完了済みRunは長期キャッシュ
    setHeaders({
      'Cache-Control': 'max-age=3600'
    });
  }

  return { run };
};
```

---

## 9. 設計判断とトレードオフ

### 9.1 ポーリング間隔

| 選択肢 | メリット | デメリット |
|--------|---------|-----------|
| 1秒（既存） | 即時性が高い | サーバー負荷大 |
| **5秒（採用）** | バランス良好 | 最大5秒の遅延 |
| WebSocket | 真のリアルタイム | 実装複雑性増大 |

**判断**: Issue要件通り5秒を採用。将来的にWebSocket化の余地を残すため、ポーリングロジックを`store`に分離。

### 9.2 状態管理

| 選択肢 | メリット | デメリット |
|--------|---------|-----------|
| **Svelte 5 Runes** | シンプル、型安全 | 新API学習コスト |
| Svelte Store | 実績あり | 旧API |
| 外部ライブラリ | 高機能 | 依存増加 |

**判断**: プロジェクト方針に従いSvelte 5 Runesを採用。

### 9.3 Rerun実装

| 選択肢 | メリット | デメリット |
|--------|---------|-----------|
| **新Run作成** | 履歴保持、シンプル | データ増加 |
| 既存Run再実行 | データ効率 | 履歴喪失 |

**判断**: 監査ログ・履歴追跡の観点から新Run作成を採用。

---

## 10. 実装優先順位

### フェーズ1: 基盤（必須）
1. [ ] Runリポジトリ実装
2. [ ] Runs一覧画面（静的表示）
3. [ ] Run詳細画面（静的表示）

### フェーズ2: 動的機能
4. [ ] Run開始機能
5. [ ] ポーリングによるステータス更新
6. [ ] JobQueue API連携

### フェーズ3: 拡張機能
7. [ ] Rerun機能
8. [ ] フィルタリング・検索
9. [ ] ログビューア

---

## 11. 受入基準

### 11.1 機能要件
- [ ] Runs一覧画面でWorkbench配下の全Runを表示できる
- [ ] Run詳細画面でステータス、開始/終了時刻、結果を確認できる
- [ ] JobVersionからRunを開始できる
- [ ] 実行中Runのステータスが5秒間隔で更新される
- [ ] 失敗したRunをRerunできる

### 11.2 非機能要件
- [ ] ページ読み込み: 1秒以内
- [ ] ポーリングによるCPU使用率: 5%未満
- [ ] TypeScript型チェック: エラーなし
- [ ] 単体テストカバレッジ: 90%以上

---

## 付録A: 参照ドキュメント

- [Issue #293](https://github.com/kewton/MySwiftAgent/issues/293)
- [Issue #279 分割計画](../279/issue-split.md)
- [myAgentDesk README](../../myAgentDesk/README.md)
- [サービス依存関係](../../docs/arch/service-dependencies.md)
- [アーキテクチャ概要](../../docs/design/architecture-overview.md)
