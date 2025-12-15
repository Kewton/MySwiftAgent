# 設計ポリシー: Issue #279 - myAgentDesk MVP再構築

## 1. 現状調査サマリー

### 1.1 プロジェクト概要

| 項目 | 内容 |
|------|------|
| Issue番号 | #279 |
| タイトル | myAgentDesk再構築 |
| タイプ | Epic（11個のサブIssue） |
| 優先度 | P1（高） |
| 影響範囲 | myAgentDesk全体 |

### 1.2 技術スタック

| カテゴリ | 技術 | バージョン |
|---------|------|-----------|
| **フレームワーク** | SvelteKit | 2.49.1 |
| **UIフレームワーク** | Svelte | 5.45.6（runes API） |
| **ビルドツール** | Vite | 7.2.6 |
| **言語** | TypeScript | 5.9.3 |
| **スタイリング** | TailwindCSS | 4.1.18 |
| **テスト** | Vitest | 4.0.15 |
| **E2Eテスト** | Playwright | 1.57.0 |
| **Lint** | ESLint | 9.x（flat config） |
| **フォーマット** | Prettier | 3.7.4 |

### 1.3 サブIssue一覧

| サブIssue | 説明 | 優先度 |
|-----------|------|--------|
| #279-1 | Project管理（CRUD、切り替え） | P1 |
| #279-2 | Workbench管理（リスト、詳細、CRUD） | P1 |
| #279-3 | Requirements管理（バージョン管理、Markdownエディタ） | P1 |
| #279-4 | Job生成・レビュー（ExpertAgent連携） | P1 |
| #279-5 | 実行監視（リアルタイム進捗、ログ） | P2 |
| #279-6 | スケジュール管理（CRON設定、有効/無効） | P2 |
| #279-7 | Vault設定（シークレット管理） | P2 |
| #279-8 | Langfuse連携（トレース可視化） | P3 |
| #279-9 | ダークモード対応 | P3 |
| #279-10 | レスポンシブデザイン | P3 |
| #279-11 | キーボードショートカット | P3 |

---

## 2. アーキテクチャ設計

### 2.1 全体構成

```
┌─────────────────────────────────────────────────────────────────┐
│                        myAgentDesk                               │
│                    (SvelteKit Frontend)                          │
│                    Port: 8000                                    │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTP/REST
          ┌───────────┴───────────────────────────────┐
          │                                           │
          ▼                                           ▼
┌─────────────────────┐                 ┌─────────────────────────┐
│    ExpertAgent      │                 │       JobQueue           │
│    Port: 8104       │                 │       Port: 8101         │
│  ・Job Generator    │                 │  ・JobMaster管理         │
│  ・Workflow Gen     │                 │  ・Run実行管理           │
│  ・Chat API         │                 │  ・実行履歴              │
└─────────────────────┘                 └─────────────────────────┘
          │                                           │
          │                                           │
          ▼                                           ▼
┌─────────────────────┐                 ┌─────────────────────────┐
│    MyVault          │                 │    MyScheduler           │
│    Port: 8103       │                 │    Port: 8102            │
│  ・シークレット管理  │                 │  ・CRONスケジューリング   │
│  ・プロジェクト設定  │                 │  ・スケジュール管理       │
└─────────────────────┘                 └─────────────────────────┘
          │
          ▼
┌─────────────────────┐                 ┌─────────────────────────┐
│   GraphAiServer     │                 │       Langfuse           │
│    Port: 8105       │                 │       Port: 3001         │
│  ・ワークフロー実行  │                 │  ・LLMトレーシング       │
│  ・GraphAI          │                 │  ・実行分析              │
└─────────────────────┘                 └─────────────────────────┘
```

### 2.2 レイヤー構成（Frontend内）

```
src/
├── routes/                    # ルーティング（URL設計）
│   ├── (app)/                # 認証必須ルート
│   │   ├── projects/         # プロジェクト管理
│   │   ├── workbenches/      # Workbench管理
│   │   ├── runs/             # 実行履歴
│   │   ├── schedules/        # スケジュール管理
│   │   └── settings/         # 設定
│   └── (preview)/            # プレビュー・モックアップ
├── lib/
│   ├── components/           # 再利用可能コンポーネント
│   │   ├── ui/               # 基本UIコンポーネント
│   │   ├── layout/           # レイアウトコンポーネント
│   │   └── domain/           # ドメイン固有コンポーネント
│   ├── stores/               # 状態管理（Svelte stores）
│   ├── api/                  # API クライアント
│   ├── types/                # TypeScript型定義
│   └── utils/                # ユーティリティ関数
└── app.css                   # グローバルスタイル
```

### 2.3 状態管理方針

| 状態の種類 | 管理方法 | 理由 |
|-----------|---------|------|
| **URL状態** | `$page.url.searchParams` | ブックマーク可能、履歴連携 |
| **ローカル状態** | Svelte 5 `$state` | コンポーネント内の一時状態 |
| **派生状態** | Svelte 5 `$derived` | 自動計算・キャッシュ |
| **副作用** | Svelte 5 `$effect` | 状態変更時の同期処理 |
| **グローバル状態** | Svelte stores | ユーザー設定、認証情報 |
| **サーバー状態** | fetch + SWR パターン | API データのキャッシュ |

---

## 3. 技術選定

### 3.1 選定理由

#### SvelteKit 2 + Svelte 5

| 評価軸 | スコア | 理由 |
|-------|-------|------|
| パフォーマンス | ★★★★★ | コンパイル時最適化、バンドルサイズ最小 |
| 開発体験 | ★★★★★ | runes APIによる直感的な状態管理 |
| 学習コスト | ★★★★☆ | シンプルな構文、少ない概念 |
| エコシステム | ★★★☆☆ | Reactより小さいが十分 |
| 将来性 | ★★★★☆ | 活発な開発、安定したロードマップ |

#### TailwindCSS 4

| 評価軸 | スコア | 理由 |
|-------|-------|------|
| 一貫性 | ★★★★★ | ユーティリティクラスによる統一 |
| カスタマイズ性 | ★★★★★ | CSS変数との親和性 |
| パフォーマンス | ★★★★★ | JIT、未使用CSS削除 |
| 保守性 | ★★★★☆ | クラス名でスタイル把握可能 |

#### Drizzle ORM（将来のローカルDB用）

| 評価軸 | スコア | 理由 |
|-------|-------|------|
| 型安全性 | ★★★★★ | TypeScriptファースト |
| パフォーマンス | ★★★★★ | SQLに近いクエリ生成 |
| 学習コスト | ★★★★☆ | SQLの知識が活かせる |
| 柔軟性 | ★★★★☆ | SQLiteからPostgreSQL移行容易 |

### 3.2 採用しない技術と理由

| 技術 | 不採用理由 |
|------|-----------|
| React/Next.js | バンドルサイズ大、過剰な複雑性 |
| Vue/Nuxt | チーム経験不足、Svelteで十分 |
| Redux/Zustand | Svelte storesで十分、追加の複雑性不要 |
| CSS-in-JS | ランタイムコスト、TailwindCSS/CSS変数で十分 |
| GraphQL | バックエンドがREST、導入コスト高 |

---

## 4. デザインパターン

### 4.1 URL駆動状態管理

```typescript
// URL状態の読み取り（Svelte 5 runes）
const currentView = $derived($page.url.searchParams.get('view') || 'workbenches');
const selectedProjectId = $derived($page.url.searchParams.get('project') || 'proj_001');
const selectedWorkbenchId = $derived($page.url.searchParams.get('workbench') || 'wb_001');

// URL状態の更新
function navigateToTab(tabId: string) {
  const params = new URLSearchParams($page.url.searchParams);
  params.set('tab', tabId);
  goto(`${baseUrl}?${params.toString()}`);
}
```

**メリット:**
- ブックマーク可能
- ブラウザ履歴との連携
- 状態の永続化
- ディープリンク対応

### 4.2 コンポーネント設計パターン

#### Container/Presentational パターン

```
+page.svelte (Container)
├── データフェッチ
├── 状態管理
├── イベントハンドリング
└── Layout.svelte (Presentational)
    ├── Header.svelte
    ├── Sidebar.svelte
    └── Content.svelte
```

#### スロットパターン（Svelte 5 Snippets）

```svelte
<script lang="ts">
  import type { Snippet } from 'svelte';

  let { children, header, footer }: {
    children: Snippet;
    header?: Snippet;
    footer?: Snippet;
  } = $props();
</script>

<div class="layout">
  {#if header}
    <header>{@render header()}</header>
  {/if}

  <main>{@render children()}</main>

  {#if footer}
    <footer>{@render footer()}</footer>
  {/if}
</div>
```

### 4.3 API通信パターン

#### 非同期ポーリングパターン（Job生成）

```typescript
// Job生成リクエスト
const response = await fetch('/api/v1/job-generator', {
  method: 'POST',
  body: JSON.stringify({ requirements, project_id })
});
const { job_id } = await response.json();

// ステータスポーリング
const pollInterval = 2000; // 2秒
const maxAttempts = 150; // 5分

for (let i = 0; i < maxAttempts; i++) {
  const statusRes = await fetch(`/api/v1/job-generator/${job_id}/status`);
  const status = await statusRes.json();

  if (status.status === 'completed') {
    return status.result;
  }
  if (status.status === 'failed') {
    throw new Error(status.error);
  }

  await new Promise(resolve => setTimeout(resolve, pollInterval));
}
```

#### Service Token認証パターン

```typescript
// APIクライアント基底クラス
class ApiClient {
  private baseUrl: string;
  private serviceName: string;
  private serviceToken: string;

  async fetch(endpoint: string, options?: RequestInit) {
    return fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-Service': this.serviceName,
        'X-Token': this.serviceToken,
        ...options?.headers,
      }
    });
  }
}
```

### 4.4 エラーハンドリングパターン

```typescript
// Result型パターン
type Result<T, E = Error> =
  | { success: true; data: T }
  | { success: false; error: E };

// 使用例
async function fetchWorkbenches(projectId: string): Promise<Result<Workbench[]>> {
  try {
    const response = await api.get(`/projects/${projectId}/workbenches`);
    return { success: true, data: response.data };
  } catch (error) {
    return { success: false, error: error as Error };
  }
}

// コンポーネントでの利用
const result = await fetchWorkbenches(projectId);
if (!result.success) {
  showError(result.error.message);
  return;
}
const workbenches = result.data;
```

---

## 5. データモデル設計

### 5.1 エンティティ関係図

```
┌─────────────┐       ┌─────────────────────┐       ┌─────────────┐
│   Project   │───1:N─│     Workbench       │───1:N─│     Run     │
└─────────────┘       └─────────────────────┘       └─────────────┘
                              │
                              │ 1:N
                              ▼
                      ┌─────────────────────┐
                      │ RequirementVersion  │
                      └─────────────────────┘
                              │
                              │ 1:N
                              ▼
                      ┌─────────────────────┐
                      │    JobVersion       │
                      └─────────────────────┘
                              │
                              │ 1:N
                              ▼
                      ┌─────────────────────┐       ┌─────────────┐
                      │       Task          │       │  Schedule   │
                      └─────────────────────┘       └─────────────┘
```

### 5.2 バージョン管理体系

```
JobVersion: vN.M
  N = RequirementVersion（要件定義のバージョン）
  M = Job生成回数（同一要件からの生成回数）

例:
  v5.2 = 要件定義v5から2回目のJob生成
  v4.3 = 要件定義v4から3回目のJob生成
```

### 5.3 TypeScript型定義

```typescript
// エンティティ型定義
interface Project {
  id: string;
  name: string;
  description: string;
  workbenchCount: number;
  createdAt: string;
  updatedAt: string;
}

interface Workbench {
  id: string;
  projectId: string;
  name: string;
  description: string;
  status: 'active' | 'idle' | 'inactive';
  lastRunAt: string | null;
  createdAt: string;
}

interface RequirementVersion {
  id: string;
  workbenchId: string;
  version: number;
  status: 'active' | 'deprecated';
  content: string;  // Markdown形式
  changeSummary: string;
  createdAt: string;
}

interface JobVersion {
  id: string;
  workbenchId: string;
  sourceRequirementVersionId: string;
  majorVersion: number;  // RequirementVersion
  minorVersion: number;  // Generation count
  versionLabel: string;  // "v5.2"
  status: 'active' | 'deprecated';
  generationReason: string;
  taskBreakdown: Task[];
  generatedAt: string;
}

interface Task {
  id: string;
  name: string;
  description: string;
  agentType: string;
  status: TaskStatus;
  estimatedDuration: string;
  inputInterface: JSONSchema;
  outputInterface: JSONSchema;
}

interface Run {
  id: string;
  workbenchId: string;
  jobVersionId: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  progress: number;
  currentTask: string | null;
  startedAt: string;
  completedAt: string | null;
  duration: string | null;
  errorMessage: string | null;
  traceId: string;
  tasksCompleted: number;
  totalTasks: number;
}

interface Schedule {
  id: string;
  workbenchId: string;
  name: string;
  targetJobVersionId: string;
  cronExpression: string;
  isEnabled: boolean;
  nextRunAt: string | null;
  lastRunAt: string | null;
}
```

---

## 6. API設計

### 6.1 エンドポイント一覧

| サービス | エンドポイント | メソッド | 説明 |
|---------|--------------|---------|------|
| **ExpertAgent** | `/v1/job-generator` | POST | Job生成開始 |
| | `/v1/job-generator/{job_id}/status` | GET | 生成状態確認 |
| | `/v1/workflow-generator` | POST | Workflow生成 |
| | `/v1/chat/requirement-definition` | POST | 要件定義チャット |
| **JobQueue** | `/api/v1/job-masters` | GET/POST | JobMaster管理 |
| | `/api/v1/job-masters/{id}` | GET/PUT/DELETE | JobMaster操作 |
| | `/api/v1/job-masters/{id}/runs` | GET/POST | Run管理 |
| | `/api/v1/runs/{id}` | GET | Run詳細・ステータス |
| **MyScheduler** | `/api/v1/schedules` | GET/POST | スケジュール一覧・作成 |
| | `/api/v1/schedules/{id}` | GET/PUT/DELETE | スケジュール操作 |
| | `/api/v1/schedules/{id}/enable` | POST | 有効化 |
| | `/api/v1/schedules/{id}/disable` | POST | 無効化 |
| **MyVault** | `/api/v1/projects` | GET/POST | プロジェクト管理 |
| | `/api/v1/secrets/{service}/{project}` | GET/POST | シークレット管理 |
| **Langfuse** | `/api/public/traces` | GET | トレース一覧 |
| | `/api/public/traces/{id}` | GET | トレース詳細 |

### 6.2 APIクライアント設計

```typescript
// src/lib/api/index.ts
import { ExpertAgentClient } from './expert-agent';
import { JobQueueClient } from './job-queue';
import { MySchedulerClient } from './my-scheduler';
import { MyVaultClient } from './my-vault';
import { LangfuseClient } from './langfuse';

export const api = {
  expertAgent: new ExpertAgentClient({ baseUrl: 'http://localhost:8104' }),
  jobQueue: new JobQueueClient({ baseUrl: 'http://localhost:8101' }),
  scheduler: new MySchedulerClient({ baseUrl: 'http://localhost:8102' }),
  vault: new MyVaultClient({ baseUrl: 'http://localhost:8103' }),
  langfuse: new LangfuseClient({ baseUrl: 'http://localhost:3001' }),
};
```

### 6.3 サービス障害時のエラーハンドリング方針

#### エラー種別と対応

| エラー種別 | HTTPステータス | リトライ可能 | UI対応 |
|-----------|--------------|-------------|--------|
| **ネットワークエラー** | - | Yes (3回) | リトライボタン表示、オフライン警告 |
| **タイムアウト** | 408/504 | Yes (2回) | 「処理に時間がかかっています」表示 |
| **サーバーエラー** | 5xx | Yes (2回) | リトライボタン、サポート連絡先表示 |
| **認証エラー** | 401/403 | No | Vault設定画面へ誘導 |
| **バリデーションエラー** | 400/422 | No | フィールド別エラーメッセージ表示 |
| **リソース不在** | 404 | No | 前の画面へ戻る、作成導線表示 |
| **レート制限** | 429 | Yes (指数バックオフ) | 待機時間表示 |

#### エラーハンドリング実装

```typescript
// src/lib/api/error-handler.ts

// エラー型定義
type ServiceErrorType =
  | 'network'
  | 'timeout'
  | 'server'
  | 'auth'
  | 'validation'
  | 'not_found'
  | 'rate_limit';

interface ServiceError {
  type: ServiceErrorType;
  message: string;
  retryable: boolean;
  retryAfter?: number;  // ミリ秒
  details?: Record<string, string[]>;  // バリデーションエラー詳細
}

// リトライ設定
const RETRY_CONFIG = {
  maxAttempts: 3,
  baseDelay: 1000,  // 1秒
  maxDelay: 10000,  // 10秒
  backoffFactor: 2,
};

// 指数バックオフ付きリトライ
async function fetchWithRetry<T>(
  fetcher: () => Promise<T>,
  config = RETRY_CONFIG
): Promise<Result<T, ServiceError>> {
  let lastError: ServiceError | null = null;

  for (let attempt = 0; attempt < config.maxAttempts; attempt++) {
    try {
      const result = await fetcher();
      return { success: true, data: result };
    } catch (error) {
      lastError = classifyError(error);

      if (!lastError.retryable) {
        return { success: false, error: lastError };
      }

      // 最後の試行では待機しない
      if (attempt < config.maxAttempts - 1) {
        const delay = Math.min(
          config.baseDelay * Math.pow(config.backoffFactor, attempt),
          config.maxDelay
        );
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }

  return { success: false, error: lastError! };
}

// エラー分類
function classifyError(error: unknown): ServiceError {
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return { type: 'network', message: 'ネットワーク接続を確認してください', retryable: true };
  }

  if (error instanceof Response) {
    switch (error.status) {
      case 401:
      case 403:
        return { type: 'auth', message: '認証情報を確認してください', retryable: false };
      case 404:
        return { type: 'not_found', message: 'リソースが見つかりません', retryable: false };
      case 408:
      case 504:
        return { type: 'timeout', message: '処理がタイムアウトしました', retryable: true };
      case 422:
        return { type: 'validation', message: '入力内容を確認してください', retryable: false };
      case 429:
        const retryAfter = parseInt(error.headers.get('Retry-After') || '5') * 1000;
        return { type: 'rate_limit', message: 'リクエスト制限中です', retryable: true, retryAfter };
      default:
        if (error.status >= 500) {
          return { type: 'server', message: 'サーバーエラーが発生しました', retryable: true };
        }
    }
  }

  return { type: 'server', message: '予期せぬエラーが発生しました', retryable: false };
}
```

#### サーキットブレーカーパターン

連続した障害時にサービスへのリクエストを一時停止し、システム全体の安定性を確保：

```typescript
// src/lib/api/circuit-breaker.ts

type CircuitState = 'closed' | 'open' | 'half-open';

class CircuitBreaker {
  private state: CircuitState = 'closed';
  private failureCount = 0;
  private lastFailureTime = 0;
  private readonly threshold = 5;          // 障害閾値
  private readonly resetTimeout = 30000;   // 30秒後にhalf-openへ

  async execute<T>(operation: () => Promise<T>): Promise<Result<T, ServiceError>> {
    // Open状態: 即座にエラー返却
    if (this.state === 'open') {
      if (Date.now() - this.lastFailureTime > this.resetTimeout) {
        this.state = 'half-open';
      } else {
        return {
          success: false,
          error: {
            type: 'server',
            message: 'サービスが一時的に利用できません。しばらくお待ちください。',
            retryable: true,
            retryAfter: this.resetTimeout - (Date.now() - this.lastFailureTime),
          }
        };
      }
    }

    try {
      const result = await operation();
      this.onSuccess();
      return { success: true, data: result };
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private onSuccess() {
    this.failureCount = 0;
    this.state = 'closed';
  }

  private onFailure() {
    this.failureCount++;
    this.lastFailureTime = Date.now();
    if (this.failureCount >= this.threshold) {
      this.state = 'open';
    }
  }
}

// サービス別サーキットブレーカー
export const circuitBreakers = {
  expertAgent: new CircuitBreaker(),
  jobQueue: new CircuitBreaker(),
  scheduler: new CircuitBreaker(),
  vault: new CircuitBreaker(),
  langfuse: new CircuitBreaker(),
};
```

#### UI側のエラー表示パターン

```svelte
<!-- src/lib/components/ui/ErrorBoundary.svelte -->
<script lang="ts">
  import type { ServiceError } from '$lib/api/error-handler';
  import { AlertTriangle, RefreshCw, Settings, ArrowLeft } from 'lucide-svelte';

  let { error, onRetry, onBack }: {
    error: ServiceError;
    onRetry?: () => void;
    onBack?: () => void;
  } = $props();

  const errorConfig = {
    network: { icon: AlertTriangle, color: 'warning', showRetry: true },
    timeout: { icon: AlertTriangle, color: 'warning', showRetry: true },
    server: { icon: AlertTriangle, color: 'error', showRetry: true },
    auth: { icon: Settings, color: 'error', showRetry: false, action: 'vault' },
    validation: { icon: AlertTriangle, color: 'warning', showRetry: false },
    not_found: { icon: ArrowLeft, color: 'info', showRetry: false, action: 'back' },
    rate_limit: { icon: AlertTriangle, color: 'warning', showRetry: true },
  };

  const config = errorConfig[error.type];
</script>

<div class="error-container" data-color={config.color}>
  <svelte:component this={config.icon} size={24} />
  <p class="error-message">{error.message}</p>

  <div class="error-actions">
    {#if config.showRetry && onRetry}
      <button class="btn-retry" onclick={onRetry}>
        <RefreshCw size={16} />
        再試行
      </button>
    {/if}

    {#if config.action === 'vault'}
      <a href="/projects/{projectId}/vault" class="btn-secondary">
        Vault設定を確認
      </a>
    {/if}

    {#if config.action === 'back' && onBack}
      <button class="btn-secondary" onclick={onBack}>
        <ArrowLeft size={16} />
        戻る
      </button>
    {/if}
  </div>
</div>
```

#### フォールバック戦略

| サービス | 障害時のフォールバック |
|---------|---------------------|
| **ExpertAgent** | 生成ボタン無効化、「サービス復旧待ち」表示 |
| **JobQueue** | Run開始ボタン無効化、既存Run一覧はキャッシュ表示 |
| **MyScheduler** | スケジュール編集無効化、一覧はキャッシュ表示 |
| **MyVault** | キャッシュ済みProject情報を表示、更新操作を無効化 |
| **Langfuse** | 「トレース表示不可」メッセージ、リンクは非表示 |

---

## 7. セキュリティ設計

### 7.1 認証・認可

| 層 | 方式 | 実装 |
|----|------|------|
| **サービス間** | Service Token | `X-Service` + `X-Token` ヘッダー |
| **ユーザー認証** | 将来実装（Phase 2） | JWT / OAuth 2.0 検討 |
| **シークレット** | MyVault管理 | 暗号化保存、アクセス制御 |

### 7.2 入力検証

```typescript
// Zodによるスキーマ検証
import { z } from 'zod';

const requirementSchema = z.object({
  content: z.string().min(10).max(50000),
  changeSummary: z.string().max(200).optional(),
});

const scheduleSchema = z.object({
  name: z.string().min(1).max(100),
  cronExpression: z.string().regex(/^[\d\s\*\/\-\,]+$/),
  targetJobVersionId: z.string().uuid(),
});
```

### 7.3 XSS対策

- Svelteのデフォルトエスケープを活用
- `{@html}` ディレクティブは sanitize後のみ使用
- Markdownレンダリングは `marked` + `DOMPurify` を併用

---

## 8. パフォーマンス設計

### 8.1 目標指標

| 指標 | 目標値 | 測定方法 |
|------|-------|---------|
| **FCP** (First Contentful Paint) | < 1.5秒 | Lighthouse |
| **LCP** (Largest Contentful Paint) | < 2.5秒 | Lighthouse |
| **TTI** (Time to Interactive) | < 3.5秒 | Lighthouse |
| **バンドルサイズ** | < 200KB (gzip) | Vite build |
| **API応答時間** | < 500ms (p95) | 監視ツール |

### 8.2 最適化戦略

#### コード分割

```typescript
// ルートベースの遅延ロード（SvelteKit標準）
// src/routes/workbenches/[id]/+page.svelte
// → 自動的にルート単位でコード分割

// 動的インポート
const MarkdownEditor = import('$lib/components/MarkdownEditor.svelte');
```

#### リスト仮想化

```typescript
// 大量の実行履歴表示には仮想化を検討
// svelte-virtual-list-ce または自前実装
const ITEMS_PER_PAGE = 15;
const paginatedRuns = $derived(
  projectRuns.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE)
);
```

#### APIキャッシュ

```typescript
// SWRパターン（stale-while-revalidate）
function createCachedFetch<T>(key: string, fetcher: () => Promise<T>) {
  let cache: T | null = null;
  let lastFetch = 0;
  const STALE_TIME = 30000; // 30秒

  return async () => {
    const now = Date.now();
    if (cache && now - lastFetch < STALE_TIME) {
      return cache;
    }
    cache = await fetcher();
    lastFetch = now;
    return cache;
  };
}
```

---

## 9. 設計判断とトレードオフ

### 9.1 ADR (Architecture Decision Records)

#### ADR-001: URL駆動状態管理の採用

**状況**: アプリケーション状態の管理方法を決定する必要がある。

**決定**: URL searchParamsを主要な状態管理手段として採用する。

**理由**:
- ブックマーク・共有可能
- ブラウザの戻る/進むと自然に連携
- SSR/SSGとの親和性
- デバッグの容易さ

**トレードオフ**:
- URLが長くなる可能性
- 複雑なネストした状態には不向き
- セキュアでない情報は含められない

**代替案**:
- Svelte stores のみ → ブックマーク不可
- LocalStorage → タブ間同期が複雑

---

#### ADR-002: CSSフレームワークにTailwindCSS採用

**状況**: スタイリング方法を統一する必要がある。

**決定**: TailwindCSS 4 + CSS変数によるテーマ管理を採用。

**理由**:
- ユーティリティファーストで一貫性確保
- JITによる最適なバンドルサイズ
- ダークモード対応が容易
- デザインシステムとの親和性

**トレードオフ**:
- HTMLが冗長になる
- 学習コスト（チーム）
- 動的スタイルには追加の工夫が必要

---

#### ADR-003: モックファーストアプローチ

**状況**: フロントエンドとバックエンドの並行開発が必要。

**決定**: 完全なモックデータを含むUIモックアップを先行開発。

**理由**:
- UIの早期検証が可能
- バックエンド開発と並行可能
- ユーザーフィードバックを早期に取得
- API仕様の明確化に貢献

**トレードオフ**:
- モックと実APIの乖離リスク
- モック保守のコスト
- 統合テスト遅延

---

#### ADR-004: Svelte 5 runes APIの全面採用

**状況**: Svelte 4の$:構文からの移行を検討。

**決定**: Svelte 5のrunes API（$state, $derived, $effect）を全面採用。

**理由**:
- より明示的な状態管理
- TypeScript型推論の改善
- 将来の互換性
- デバッグの容易さ

**トレードオフ**:
- 移行コスト
- 既存Svelteユーザーの学習コスト
- 一部サードパーティライブラリの互換性

---

### 9.2 リスクと軽減策

| リスク | 影響度 | 発生確率 | 軽減策 |
|-------|-------|---------|-------|
| API仕様の変更 | 高 | 中 | APIクライアント抽象化、型定義 |
| パフォーマンス劣化 | 中 | 低 | 早期ベンチマーク、遅延ロード |
| 認証機能の後付け | 中 | 高 | 認証ガードの設計準備 |
| ダークモード実装遅延 | 低 | 中 | CSS変数による設計 |

---

## 10. 実装計画

### 10.1 フェーズ分割

| フェーズ | スコープ | 目標 |
|---------|---------|------|
| **Phase 1** | 基盤構築 | ルーティング、レイアウト、APIクライアント |
| **Phase 2** | コア機能 | Project、Workbench、Requirements管理 |
| **Phase 3** | Job管理 | Job生成、レビュー、実行監視 |
| **Phase 4** | 運用機能 | スケジュール、Vault、Langfuse連携 |
| **Phase 5** | UX向上 | ダークモード、レスポンシブ、ショートカット |

### 10.2 テスト戦略

| テスト種別 | ツール | カバレッジ目標 |
|-----------|-------|--------------|
| **単体テスト** | Vitest | 90% |
| **コンポーネントテスト** | Vitest + Testing Library | 80% |
| **E2Eテスト** | Playwright | 主要ユーザーフロー100% |
| **ビジュアルリグレッション** | Playwright + screenshot | 主要画面 |

---

## 11. 参照ドキュメント

| ドキュメント | 内容 |
|-------------|------|
| [requirements.md](./requirements.md) | 機能要件、ユーザーストーリー |
| [screen-transition.md](./screen-transition.md) | URL設計、画面遷移 |
| [er-diagram.md](./er-diagram.md) | データモデル |
| [design-system.md](./design-system.md) | デザインシステム |
| [index.md](./index.md) | ドキュメントインデックス |
| [API_REFERENCE.md](../../../expertAgent/docs/API_REFERENCE.md) | ExpertAgent API仕様 |
| [service-dependencies.md](../../../docs/arch/service-dependencies.md) | サービス間依存関係 |

---

## 12. 変更履歴

| 日付 | バージョン | 変更内容 | 担当者 |
|------|-----------|---------|-------|
| 2024-12-15 | 1.0.0 | 初版作成 | Claude |
