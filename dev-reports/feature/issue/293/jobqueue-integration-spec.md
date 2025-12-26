# JobQueue連携機能仕様書

## Issue #293: Runs画面（実行履歴・監視）- JobQueue連携

---

## 1. 概要

### 1.1 目的

myAgentDeskのRuns機能において、JobQueueサービスと連携してジョブ実行を実現する。
現状はRunレコードが`queued`状態で作成されるのみで、実際のジョブ実行が行われていない。

### 1.2 現状の問題

| 項目 | 現状 | 必要な状態 |
|------|------|-----------|
| Run作成 | ✅ DBにレコード作成 | - |
| パラメータ入力 | ❌ 未実装 | インターフェースに基づく入力フォーム |
| JobQueue連携 | ❌ 未実装 | ジョブ送信必要 |
| ステータス同期 | ❌ 未実装 | ポーリングで同期必要 |
| タスク進捗表示 | ❌ 未実装 | タスクごとの実行状況表示 |
| **タスク出力確認** | ❌ 未実装 | 完了タスクの出力結果表示・コピー・ダウンロード |
| 結果取得 | ❌ 未実装 | 完了時に結果取得必要 |

### 1.3 関連コンポーネント

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  myAgentDesk    │────▶│    JobQueue     │────▶│  graphAiServer  │
│  (SvelteKit)    │     │   (FastAPI)     │     │   (FastAPI)     │
│                 │     │                 │     │                 │
│  - Runs UI      │     │  - Job管理      │     │  - Workflow実行 │
│  - Run API      │     │  - Task管理     │     │  - GraphAI      │
│  - Polling      │     │  - 実行制御     │     │                 │
│  - タスク進捗   │     │                 │     │                 │
│  - パラメータ入力│     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## 2. インターフェースベースのパラメータ入力

### 2.1 概要

ジョブ実行時に、JobVersionに定義されたインターフェース（`interfaceDefinitions`）に基づいて、
ユーザーが実行パラメータを手入力できる機能を提供する。

ワークフローの**最初のタスク（task_001）のinput_schema**を使用して、動的に入力フォームを生成する。

### 2.2 インターフェース定義の構造

JobVersionの`interfaceDefinitions`フィールドに格納されるJSON構造：

```typescript
// JobVersion.interfaceDefinitions (JSON文字列として保存)
interface InterfaceDefinitions {
  [taskId: string]: TaskInterface;
}

interface TaskInterface {
  interface_master_id: string;
  input_interface_id: string;
  output_interface_id: string;
  interface_name: string;
  input_schema: JSONSchema;   // ← 入力パラメータの定義
  output_schema: JSONSchema;
}

// JSON Schema形式
interface JSONSchema {
  type: 'object';
  properties: {
    [propertyName: string]: {
      type: 'string' | 'number' | 'boolean' | 'array' | 'object';
      description?: string;
      default?: unknown;
      enum?: unknown[];
    };
  };
  required?: string[];
  additionalProperties?: boolean;
}
```

### 2.3 サンプルデータ

```json
{
  "task_001": {
    "interface_master_id": "if_01KDD4YJ296FG1TXZDZSWRASWB",
    "interface_name": "google_search_financials_interface",
    "input_schema": {
      "type": "object",
      "properties": {
        "company_name": { "type": "string" },
        "target_years": { "type": "string" },
        "document_types": { "type": "string" }
      },
      "required": ["company_name", "target_years", "document_types"],
      "additionalProperties": false
    },
    "output_schema": { ... }
  },
  "task_002": { ... },
  "task_003": { ... }
}
```

### 2.4 入力パラメータの抽出ロジック

```typescript
/**
 * JobVersionのinterfaceDefinitionsから最初のタスクの入力スキーマを取得
 */
function getInputSchema(jobVersion: JobVersion): JSONSchema | null {
  if (!jobVersion.interfaceDefinitions) {
    return null;
  }

  try {
    const definitions = JSON.parse(jobVersion.interfaceDefinitions);

    // タスクIDでソートして最初のタスクを取得
    const taskIds = Object.keys(definitions).sort();
    if (taskIds.length === 0) {
      return null;
    }

    const firstTask = definitions[taskIds[0]];
    return firstTask?.input_schema || null;
  } catch (e) {
    console.error('Failed to parse interfaceDefinitions:', e);
    return null;
  }
}
```

---

## 3. タスクごとの実行状況追跡

### 3.1 概要

ジョブ実行中に、JobMasterに紐づく各タスクの実行状況をリアルタイムで表示する。
これにより、ユーザーはワークフローのどの部分が実行中・完了・失敗したかを把握できる。

### 3.2 JobQueue Task API

**エンドポイント**: `GET /api/v1/jobs/{job_id}/tasks`

```typescript
// レスポンス (TaskList)
interface TaskList {
  job_id: string;
  tasks: TaskDetail[];
  total: number;
}

// タスク詳細 (TaskDetail)
interface TaskDetail {
  id: string;              // タスクID
  job_id: string;          // 親ジョブID
  master_id: string;       // TaskMaster ID
  master_version?: number;
  order: number;           // 実行順序 (1, 2, 3, ...)
  status: TaskStatus;      // タスクステータス
  input_data?: object;     // 入力データ
  output_data?: object;    // 出力データ
  attempt: number;         // リトライ回数
  error?: string;          // エラーメッセージ
  started_at?: string;     // 開始時刻 (ISO8601)
  finished_at?: string;    // 終了時刻 (ISO8601)
  duration_ms?: number;    // 実行時間 (ミリ秒)
  created_at: string;
  updated_at: string;
}

// タスクステータス
type TaskStatus = 'pending' | 'running' | 'succeeded' | 'failed' | 'skipped';
```

### 3.3 タスク情報の取得フロー

```
Run詳細ページ表示
         │
         ▼
┌─────────────────────────────────────────────────────┐
│ GET /api/runs/{runId}/tasks                         │
│                                                     │
│ 1. Get Run from DB                                 │
│ 2. If externalJobId exists:                        │
│    Call JobQueue: GET /api/v1/jobs/{job_id}/tasks  │
│ 3. Map task info with interfaceDefinitions         │
│ 4. Return enriched task list                       │
└─────────────────────────────────────────────────────┘
         │
         ▼
   Display task progress in UI
```

### 3.4 タスク情報とインターフェース定義の紐付け

```typescript
// interfaceDefinitionsからタスク名を取得して表示用データを生成
interface TaskProgressItem {
  taskId: string;           // task_001, task_002, ...
  taskName: string;         // interface_name から取得
  order: number;            // 実行順序
  status: TaskStatus;
  inputSchema?: JSONSchema; // 入力スキーマ
  outputSchema?: JSONSchema;// 出力スキーマ
  inputData?: object;       // 実際の入力値
  outputData?: object;      // 実際の出力値
  error?: string;
  startedAt?: Date;
  finishedAt?: Date;
  durationMs?: number;
}

function mergeTasksWithInterfaces(
  tasks: TaskDetail[],
  interfaceDefinitions: string | null
): TaskProgressItem[] {
  const interfaces = interfaceDefinitions
    ? JSON.parse(interfaceDefinitions)
    : {};

  return tasks.map(task => {
    const taskId = `task_${String(task.order).padStart(3, '0')}`;
    const iface = interfaces[taskId];

    return {
      taskId,
      taskName: iface?.interface_name || `Task ${task.order}`,
      order: task.order,
      status: task.status,
      inputSchema: iface?.input_schema,
      outputSchema: iface?.output_schema,
      inputData: task.input_data,
      outputData: task.output_data,
      error: task.error,
      startedAt: task.started_at ? new Date(task.started_at) : undefined,
      finishedAt: task.finished_at ? new Date(task.finished_at) : undefined,
      durationMs: task.duration_ms
    };
  });
}
```

### 3.5 APIエンドポイント追加

#### GET /api/runs/{runId}/tasks（新規）

```typescript
// src/routes/api/runs/[runId]/tasks/+server.ts

import { json, type RequestHandler } from '@sveltejs/kit';
import { runRepository } from '$lib/server/repositories/run';
import { jobVersionRepository } from '$lib/server/repositories/job-version';
import { getJobQueueClient } from '$lib/api/clients/job-queue';

export const GET: RequestHandler = async ({ params }) => {
  const run = await runRepository.findById(params.runId);
  if (!run) {
    return json({ error: 'Run not found' }, { status: 404 });
  }

  // externalJobIdがない場合は空のタスクリストを返す
  if (!run.externalJobId) {
    return json({
      runId: run.id,
      tasks: [],
      total: 0
    });
  }

  // JobQueueからタスク一覧を取得
  const jobQueueClient = getJobQueueClient();
  const tasksResult = await jobQueueClient.getJobTasks(run.externalJobId);

  if (tasksResult.isErr()) {
    return json({
      error: 'Failed to fetch tasks from JobQueue',
      message: tasksResult.error.message
    }, { status: 502 });
  }

  // JobVersionのinterfaceDefinitionsを取得
  const jobVersion = await jobVersionRepository.findById(run.jobVersionId);
  const interfaceDefinitions = jobVersion?.interfaceDefinitions || null;

  // タスク情報をインターフェース定義と紐付け
  const enrichedTasks = mergeTasksWithInterfaces(
    tasksResult.value.tasks,
    interfaceDefinitions
  );

  return json({
    runId: run.id,
    tasks: enrichedTasks,
    total: tasksResult.value.total
  });
};
```

---

## 4. UI仕様

### 4.1 Run作成モーダルの変更

現在のモーダル：
- JobVersion選択のみ

変更後のモーダル：
- Step 1: JobVersion選択
- Step 2: パラメータ入力（interfaceDefinitionsから動的生成）
- Step 3: 確認・実行

### 4.2 Run詳細ページ - タスク進捗表示

```
┌────────────────────────────────────────────────────────────────┐
│  Run Details: run_1766747451585_hlnsgga                        │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Status: [Running]     Started: 2024-12-26 20:30:00           │
│  Job Version: v1.0     Duration: 2m 34s                       │
│                                                                │
│  ═══════════════════════════════════════════════════════════  │
│                                                                │
│  Task Progress (3/8 completed)                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  # │ Task Name                    │ Status    │ Duration │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │  1 │ google_search_financials     │ ✅ Success │ 12.3s   │  │
│  │  2 │ file_reader_pdf              │ ✅ Success │ 8.7s    │  │
│  │  3 │ google_search_supplementary  │ ✅ Success │ 15.2s   │  │
│  │  4 │ json_output_revenue_analysis │ 🔄 Running │ 5.1s    │  │
│  │  5 │ json_output_business_analysis│ ⏳ Pending │ -       │  │
│  │  6 │ json_output_report_generation│ ⏳ Pending │ -       │  │
│  │  7 │ drive_upload_report          │ ⏳ Pending │ -       │  │
│  │  8 │ gmail_send_notification      │ ⏳ Pending │ -       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  [View Trace in Langfuse]                    [Cancel] [Rerun] │
└────────────────────────────────────────────────────────────────┘
```

### 4.3 タスクステータスアイコン

| ステータス | アイコン | 色 | 説明 |
|-----------|---------|-----|------|
| pending | ⏳ | gray | 待機中 |
| running | 🔄 | amber | 実行中 |
| succeeded | ✅ | green | 成功 |
| failed | ❌ | red | 失敗 |
| skipped | ⏭️ | gray | スキップ |

### 4.4 タスク詳細展開（クリック時）

```
┌──────────────────────────────────────────────────────────────┐
│  ▼ Task 1: google_search_financials              ✅ Success  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Input:                                                      │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ {                                                      │  │
│  │   "company_name": "Toyota Motor Corporation",          │  │
│  │   "target_years": "2020-2024",                         │  │
│  │   "document_types": "Annual Report, Financial..."      │  │
│  │ }                                                      │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  Output:                                                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ {                                                      │  │
│  │   "success": "true",                                   │  │
│  │   "documents": ["doc1.pdf", "doc2.pdf", ...]           │  │
│  │ }                                                      │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  Started: 2024-12-26 20:30:01    Finished: 2024-12-26 20:30:13│
│  Duration: 12.3s                 Attempt: 1                  │
└──────────────────────────────────────────────────────────────┘
```

### 4.5 Svelteコンポーネント実装（タスク進捗）

```svelte
<!-- src/routes/projects/[projectId]/workbenches/[workbenchId]/runs/[runId]/TaskProgress.svelte -->

<script lang="ts">
  import type { TaskProgressItem } from '$lib/types/run';

  let { tasks, isPolling = false }: {
    tasks: TaskProgressItem[];
    isPolling?: boolean;
  } = $props();

  // タスク詳細の展開状態
  let expandedTaskId = $state<string | null>(null);

  const completedCount = $derived(
    tasks.filter(t => t.status === 'succeeded').length
  );

  const statusConfig = {
    pending: { icon: '⏳', label: 'Pending', color: '#64748b' },
    running: { icon: '🔄', label: 'Running', color: '#d97706' },
    succeeded: { icon: '✅', label: 'Success', color: '#16a34a' },
    failed: { icon: '❌', label: 'Failed', color: '#dc2626' },
    skipped: { icon: '⏭️', label: 'Skipped', color: '#64748b' }
  };

  function formatDuration(ms: number | undefined): string {
    if (!ms) return '-';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  }

  function toggleExpand(taskId: string) {
    expandedTaskId = expandedTaskId === taskId ? null : taskId;
  }
</script>

<div class="task-progress">
  <h3>
    Task Progress ({completedCount}/{tasks.length} completed)
    {#if isPolling}
      <span class="polling-indicator">●</span>
    {/if}
  </h3>

  <div class="task-list">
    {#each tasks as task (task.taskId)}
      {@const config = statusConfig[task.status]}
      <div
        class="task-item"
        class:expanded={expandedTaskId === task.taskId}
        class:running={task.status === 'running'}
      >
        <button
          class="task-header"
          onclick={() => toggleExpand(task.taskId)}
          aria-expanded={expandedTaskId === task.taskId}
        >
          <span class="task-order">{task.order}</span>
          <span class="task-name">{task.taskName}</span>
          <span class="task-status" style="color: {config.color}">
            {config.icon} {config.label}
          </span>
          <span class="task-duration">{formatDuration(task.durationMs)}</span>
          <span class="expand-icon">{expandedTaskId === task.taskId ? '▼' : '▶'}</span>
        </button>

        {#if expandedTaskId === task.taskId}
          <div class="task-details">
            {#if task.inputData}
              <div class="detail-section">
                <h4>Input</h4>
                <pre>{JSON.stringify(task.inputData, null, 2)}</pre>
              </div>
            {/if}

            {#if task.outputData}
              <div class="detail-section">
                <h4>Output</h4>
                <pre>{JSON.stringify(task.outputData, null, 2)}</pre>
              </div>
            {/if}

            {#if task.error}
              <div class="detail-section error">
                <h4>Error</h4>
                <pre>{task.error}</pre>
              </div>
            {/if}

            <div class="detail-meta">
              {#if task.startedAt}
                <span>Started: {task.startedAt.toLocaleString()}</span>
              {/if}
              {#if task.finishedAt}
                <span>Finished: {task.finishedAt.toLocaleString()}</span>
              {/if}
            </div>
          </div>
        {/if}
      </div>
    {/each}
  </div>
</div>

<style>
  .task-progress h3 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 1rem;
    margin-bottom: 1rem;
  }

  .polling-indicator {
    color: #16a34a;
    animation: pulse 1s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  .task-list {
    border: 1px solid #e2e8f0;
    border-radius: 0.5rem;
    overflow: hidden;
  }

  .task-item {
    border-bottom: 1px solid #e2e8f0;
  }

  .task-item:last-child {
    border-bottom: none;
  }

  .task-item.running {
    background: #fef3c7;
  }

  .task-header {
    display: grid;
    grid-template-columns: 2rem 1fr 7rem 5rem 1.5rem;
    gap: 0.75rem;
    align-items: center;
    width: 100%;
    padding: 0.75rem 1rem;
    background: none;
    border: none;
    cursor: pointer;
    text-align: left;
  }

  .task-header:hover {
    background: #f8fafc;
  }

  .task-order {
    font-weight: 600;
    color: #64748b;
  }

  .task-name {
    font-family: monospace;
    font-size: 0.875rem;
  }

  .task-status {
    font-size: 0.75rem;
    font-weight: 500;
  }

  .task-duration {
    font-family: monospace;
    font-size: 0.75rem;
    color: #64748b;
    text-align: right;
  }

  .expand-icon {
    color: #94a3b8;
    font-size: 0.625rem;
  }

  .task-details {
    padding: 1rem;
    background: #f8fafc;
    border-top: 1px solid #e2e8f0;
  }

  .detail-section {
    margin-bottom: 1rem;
  }

  .detail-section h4 {
    font-size: 0.75rem;
    font-weight: 600;
    color: #64748b;
    margin-bottom: 0.25rem;
  }

  .detail-section pre {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 0.25rem;
    padding: 0.5rem;
    font-size: 0.75rem;
    overflow-x: auto;
    max-height: 200px;
  }

  .detail-section.error pre {
    background: #fef2f2;
    border-color: #fecaca;
    color: #dc2626;
  }

  .detail-meta {
    display: flex;
    gap: 1.5rem;
    font-size: 0.75rem;
    color: #64748b;
  }
</style>
```

---

## 5. JobQueue API仕様

### 5.1 使用エンドポイント

| メソッド | パス | 用途 |
|----------|------|------|
| POST | `/api/v1/jobs/from-master/{master_id}` | JobMasterからジョブ作成 |
| GET | `/api/v1/jobs/{job_id}` | ジョブ詳細取得 |
| GET | `/api/v1/jobs/{job_id}/tasks` | **タスク一覧取得（新規）** |
| GET | `/api/v1/jobs/{job_id}/result` | ジョブ結果取得 |
| POST | `/api/v1/jobs/{job_id}/cancel` | ジョブキャンセル |
| POST | `/api/v1/jobs/{job_id}/retry` | ジョブリトライ |
| POST | `/api/v1/tasks/{task_id}/retry` | **タスクリトライ（新規）** |

### 5.2 ジョブ作成リクエスト

**エンドポイント**: `POST /api/v1/jobs/from-master/{master_id}`

```typescript
// リクエスト (JobCreateFromMaster)
interface JobCreateFromMaster {
  name?: string;
  headers?: Record<string, string>;
  params?: Record<string, unknown>;
  body?: Record<string, unknown>;  // input_data を含む
  timeout_sec?: number;
  priority?: number;
  scheduled_at?: string;
  max_attempts?: number;
  tags?: string[];
  validate_interfaces?: boolean;
}

// レスポンス (JobResponse)
interface JobResponse {
  job_id: string;
  status: JobStatus;
}
```

### 5.3 ステータス列挙

```typescript
// ジョブステータス
type JobStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'canceled';

// タスクステータス
type TaskStatus = 'pending' | 'running' | 'succeeded' | 'failed' | 'skipped';

// Runステータス (myAgentDesk)
type RunStatus = 'queued' | 'running' | 'success' | 'failed' | 'canceled' | 'timeout';
```

### 5.4 ステータスマッピング

**ジョブステータス → Runステータス**

| JobQueue Status | Run Status |
|-----------------|------------|
| `queued` | `queued` |
| `running` | `running` |
| `succeeded` | `success` |
| `failed` | `failed` |
| `canceled` | `canceled` |

**タスクステータス（そのまま使用）**

| Task Status | 表示 |
|-------------|------|
| `pending` | ⏳ Pending |
| `running` | 🔄 Running |
| `succeeded` | ✅ Success |
| `failed` | ❌ Failed |
| `skipped` | ⏭️ Skipped |

---

## 6. 実装仕様

### 6.1 ポーリングでのタスク進捗取得

```typescript
// src/lib/stores/run-polling.svelte.ts に追加

import { getFirstTaskInputSchema } from '$lib/utils/interface-schema';

interface RunPollingState {
  run: RunDetail | null;
  tasks: TaskProgressItem[];  // ← 追加
  isPolling: boolean;
  error: string | null;
}

export function createRunPollingStore(runId: string) {
  let state = $state<RunPollingState>({
    run: null,
    tasks: [],
    isPolling: false,
    error: null
  });

  async function poll() {
    // Runステータスを取得
    const statusRes = await fetch(`/api/runs/${runId}/status`);
    const statusData = await statusRes.json();

    // タスク進捗を取得
    const tasksRes = await fetch(`/api/runs/${runId}/tasks`);
    const tasksData = await tasksRes.json();

    state = {
      ...state,
      run: statusData,
      tasks: tasksData.tasks || [],
      error: null
    };

    // ターミナルステータスでない場合は継続
    if (!isTerminalStatus(statusData.status)) {
      setTimeout(poll, POLLING_INTERVAL_MS);
    } else {
      state.isPolling = false;
    }
  }

  return {
    get state() { return state; },
    start() {
      state.isPolling = true;
      poll();
    },
    stop() {
      state.isPolling = false;
    }
  };
}
```

### 6.2 Run詳細ページでの使用

```svelte
<!-- src/routes/projects/[projectId]/workbenches/[workbenchId]/runs/[runId]/+page.svelte -->

<script lang="ts">
  import { createRunPollingStore } from '$lib/stores/run-polling.svelte';
  import TaskProgress from './TaskProgress.svelte';

  let { data } = $props();

  const polling = createRunPollingStore(data.run.id);

  $effect(() => {
    // running/queued状態の場合はポーリング開始
    if (data.run.status === 'queued' || data.run.status === 'running') {
      polling.start();
    }

    return () => polling.stop();
  });
</script>

<div class="run-detail">
  <header>
    <h1>Run Details</h1>
    <StatusBadge status={polling.state.run?.status ?? data.run.status} />
  </header>

  <!-- タスク進捗表示 -->
  <TaskProgress
    tasks={polling.state.tasks}
    isPolling={polling.state.isPolling}
  />

  <!-- その他の情報 -->
</div>
```

---

## 7. データモデル

### 7.1 Runテーブル（既存）

```sql
CREATE TABLE run (
  id TEXT PRIMARY KEY,
  workbench_id TEXT NOT NULL,
  job_version_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  external_job_id TEXT,      -- JobQueue job_id
  external_trace_id TEXT,    -- Langfuse trace_id
  execution_params TEXT,     -- ユーザー入力パラメータ (JSON)
  result_summary TEXT,
  started_at INTEGER,
  completed_at INTEGER,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
```

### 7.2 タスク進捗（非永続化）

タスク進捗はJobQueueから都度取得するため、myAgentDeskのDBには保存しない。
ただし、キャッシュやパフォーマンス向上のために将来的に保存を検討。

---

## 8. JobQueueClientの拡張

### 8.1 新規メソッド

```typescript
// src/lib/api/clients/job-queue.ts

export class JobQueueClient extends ApiClient {
  /**
   * Create a job from a master template
   */
  async createJobFromMaster(
    masterId: string,
    request: JobCreateFromMaster
  ): Promise<Result<JobResponse, ApiError>> {
    return this.post<JobResponse>(
      `/api/v1/jobs/from-master/${masterId}`,
      request
    );
  }

  /**
   * Get job details
   */
  async getJob(jobId: string): Promise<Result<JobDetail, ApiError>> {
    return this.get<JobDetail>(`/api/v1/jobs/${jobId}`);
  }

  /**
   * Get job tasks (タスク進捗取得)
   */
  async getJobTasks(jobId: string): Promise<Result<TaskList, ApiError>> {
    return this.get<TaskList>(`/api/v1/jobs/${jobId}/tasks`);
  }

  /**
   * Get job result
   */
  async getJobResult(jobId: string): Promise<Result<JobResultResponse, ApiError>> {
    return this.get<JobResultResponse>(`/api/v1/jobs/${jobId}/result`);
  }

  /**
   * Cancel a job
   */
  async cancelJob(jobId: string): Promise<Result<JobResponse, ApiError>> {
    return this.post<JobResponse>(`/api/v1/jobs/${jobId}/cancel`);
  }

  /**
   * Retry a failed task
   */
  async retryTask(taskId: string): Promise<Result<TaskRetryResponse, ApiError>> {
    return this.post<TaskRetryResponse>(`/api/v1/tasks/${taskId}/retry`);
  }
}
```

### 8.2 型定義

```typescript
// src/lib/api/clients/job-queue.ts

export interface TaskList {
  job_id: string;
  tasks: TaskDetail[];
  total: number;
}

export interface TaskDetail {
  id: string;
  job_id: string;
  master_id: string;
  master_version?: number;
  order: number;
  status: TaskStatus;
  input_data?: Record<string, unknown>;
  output_data?: Record<string, unknown>;
  attempt: number;
  error?: string;
  started_at?: string;
  finished_at?: string;
  duration_ms?: number;
  created_at: string;
  updated_at: string;
}

export type TaskStatus = 'pending' | 'running' | 'succeeded' | 'failed' | 'skipped';

export interface TaskRetryResponse {
  task_id: string;
  status: string;
  message: string;
}
```

---

## 9. テスト計画

### 9.1 単体テスト

| テストファイル | テストケース |
|--------------|-------------|
| `tests/unit/utils/interface-schema.test.ts` | getFirstTaskInputSchema - 正常系 |
| | schemaToFormFields - 全フィールドタイプ |
| | mergeTasksWithInterfaces - タスク紐付け |
| `tests/unit/routes/api/runs-tasks.test.ts` | GET /runs/{id}/tasks - 正常系 |
| | GET /runs/{id}/tasks - externalJobIdなし |
| | GET /runs/{id}/tasks - JobQueue取得エラー |
| `tests/unit/components/TaskProgress.test.ts` | タスク一覧表示 |
| | ステータスアイコン表示 |
| | 詳細展開/折りたたみ |
| `tests/unit/api/job-queue.test.ts` | getJobTasks - 正常系 |
| | retryTask - 正常系 |

### 9.2 受入テスト

```python
# tests/acceptance/test_issue_293_task_progress.py

def test_task_progress_displayed():
    """タスク進捗がRun詳細ページに表示される"""
    pass

def test_task_status_updates_in_realtime():
    """タスクステータスがリアルタイムで更新される"""
    pass

def test_task_details_expandable():
    """タスク詳細が展開可能"""
    pass

def test_failed_task_shows_error():
    """失敗タスクのエラーメッセージが表示される"""
    pass
```

---

## 10. 実装タスク

### 10.1 タスク一覧

| # | タスク | 工数 | 優先度 |
|---|--------|------|--------|
| 1 | interface-schema.ts ヘルパー実装 | 1h | P1 |
| 2 | +page.server.ts にinterfaceDefinitions追加 | 0.5h | P1 |
| 3 | Run作成モーダルにパラメータ入力フォーム追加 | 2h | P1 |
| 4 | POST /api/runs にパラメータ処理・JobQueue連携追加 | 1.5h | P1 |
| 5 | JobQueueClient拡張（createJobFromMaster, getJobTasks等） | 1h | P1 |
| 6 | GET /api/runs/{runId}/tasks 実装 | 1h | P1 |
| 7 | TaskProgressコンポーネント実装 | 2h | P1 |
| 8 | run-polling.svelte.ts にタスク進捗取得追加 | 1h | P1 |
| 9 | Run詳細ページにTaskProgress統合 | 1h | P1 |
| 10 | **OutputViewerコンポーネント実装** | 1.5h | P1 |
| 11 | **出力データのコピー・ダウンロード機能** | 0.5h | P1 |
| 12 | **表示モード切替（Formatted/Raw/Table）** | 1h | P1 |
| 13 | **大容量データの省略表示・ページング** | 1h | P2 |
| 14 | **データフロー分析・表示機能** | 1.5h | P2 |
| 15 | 単体テスト（OutputViewer、DataFlow含む） | 2h | P2 |
| 16 | 受入テストの追加 | 1h | P2 |

**合計工数**: 18時間

### 10.2 依存関係

```
Task 1 ──▶ Task 2 ──▶ Task 3
                        │
Task 5 ──┬──▶ Task 4 ◀──┘
         │
         ├──▶ Task 6 ──▶ Task 7 ──┐
         │                        │
         └──▶ Task 8 ──▶ Task 9 ──┼──▶ Task 10 ──▶ Task 11 ──▶ Task 12
                                  │
                                  └──▶ Task 13
                                  │
                                  └──▶ Task 14
                                        │
                                        ▼
                                     Task 15 ──▶ Task 16
```

**依存関係説明:**
- Task 10 (OutputViewer): Task 7 (TaskProgress) と Task 9 (ページ統合) に依存
- Task 11 (コピー・ダウンロード): Task 10 (OutputViewer) に依存
- Task 12 (表示モード切替): Task 11 に依存
- Task 13 (大容量データ): Task 10 に依存（並列可能）
- Task 14 (データフロー): Task 10 に依存（並列可能）
- Task 15 (単体テスト): Task 12, 13, 14 完了後
- Task 16 (受入テスト): Task 15 完了後

---

## 11. 制約と前提条件

### 11.1 前提条件

1. JobQueueサービスが起動していること
2. graphAiServerサービスが起動していること
3. JobMasterが事前に登録されていること（Job Generation完了済み）
4. `jobVersion.externalJobMasterId` が設定されていること
5. `jobVersion.interfaceDefinitions` が設定されていること
6. JobQueueのタスクAPIが利用可能であること

### 11.2 制約

1. 最初のタスク（task_001）の`input_schema`のみをパラメータ入力対象とする
2. JSONスキーマの基本型（string, number, boolean）のみサポート
3. タスク進捗はJobQueueから都度取得（ローカルキャッシュなし）
4. ポーリング間隔は5秒固定

### 11.3 将来拡張

1. 複雑な型（array, nested object）のサポート
2. タスク進捗のローカルキャッシュ
3. 失敗タスクの個別リトライUI
4. タスク出力のダウンロード機能
5. WebSocket によるリアルタイム更新

---

## 12. タスク出力結果の確認機能

### 12.1 概要

完了したタスクの出力結果を確認できる機能を提供する。
出力データは以下の方法で確認できる：

1. **タスク詳細展開** - 各タスクをクリックして出力を確認
2. **スキーマ連携表示** - 出力スキーマに基づいたフィールド名・説明付き表示
3. **コピー・ダウンロード** - 出力データのクリップボードコピーとJSONダウンロード
4. **タスク間データフロー表示** - 前タスクの出力→次タスクの入力の連携を視覚化

### 12.2 出力結果表示UI

#### 12.2.1 出力結果の確認方法

```
┌────────────────────────────────────────────────────────────────┐
│  ▼ Task 1: google_search_financials              ✅ Success    │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Input                                            [Copy] [⤓]  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ company_name      "Toyota Motor Corporation"             │  │
│  │ target_years      "2020-2024"                            │  │
│  │ document_types    "Annual Report, Financial Statement"   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  Output (3 fields)                    [View Raw] [Copy] [⤓]   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ ▸ success         true                                   │  │
│  │ ▸ documents       Array[12]                  [Expand]    │  │
│  │ ▸ search_summary  "Found 12 documents..."               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  Duration: 12.3s   |   Attempt: 1                             │
│  Started: 20:30:01   Finished: 20:30:13                       │
└────────────────────────────────────────────────────────────────┘
```

#### 12.2.2 出力データの表示モード

| モード | 説明 | 用途 |
|--------|------|------|
| **Key-Value表示** | スキーマのプロパティごとに整形表示（デフォルト） | 素早い確認 |
| **Raw JSON表示** | JSONをそのまま表示 | 開発者向け・詳細確認 |
| **Table表示** | 配列データをテーブルで表示 | リスト系データの確認 |

### 12.3 出力スキーマとの連携表示

#### 12.3.1 スキーマ情報の活用

output_schemaの情報を使って、出力結果をより分かりやすく表示する：

```typescript
// 出力スキーマの例
{
  "type": "object",
  "properties": {
    "success": {
      "type": "boolean",
      "description": "検索が成功したかどうか"
    },
    "documents": {
      "type": "array",
      "description": "発見したドキュメントのリスト",
      "items": {
        "type": "object",
        "properties": {
          "title": { "type": "string" },
          "url": { "type": "string" },
          "file_type": { "type": "string" }
        }
      }
    },
    "search_summary": {
      "type": "string",
      "description": "検索結果のサマリー"
    }
  }
}
```

#### 12.3.2 表示コンポーネント実装

```svelte
<!-- src/lib/components/OutputViewer.svelte -->

<script lang="ts">
  import type { JSONSchema } from '$lib/types/json-schema';

  let {
    outputData,
    outputSchema = null,
    taskName
  }: {
    outputData: Record<string, unknown> | null;
    outputSchema?: JSONSchema | null;
    taskName: string;
  } = $props();

  // 表示モード
  let viewMode = $state<'formatted' | 'raw' | 'table'>('formatted');

  // 展開状態（配列やオブジェクトの展開）
  let expandedFields = $state<Set<string>>(new Set());

  // クリップボードにコピー
  async function copyToClipboard() {
    if (outputData) {
      await navigator.clipboard.writeText(JSON.stringify(outputData, null, 2));
      showCopyNotification = true;
      setTimeout(() => showCopyNotification = false, 2000);
    }
  }

  // JSONファイルとしてダウンロード
  function downloadAsJson() {
    if (outputData) {
      const blob = new Blob([JSON.stringify(outputData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${taskName}-output.json`;
      a.click();
      URL.revokeObjectURL(url);
    }
  }

  // スキーマからフィールドの説明を取得
  function getFieldDescription(fieldName: string): string | undefined {
    return outputSchema?.properties?.[fieldName]?.description;
  }

  // 値の型を判定して表示形式を決定
  function getValueDisplay(value: unknown): { type: string; display: string; expandable: boolean } {
    if (value === null) return { type: 'null', display: 'null', expandable: false };
    if (typeof value === 'boolean') return { type: 'boolean', display: String(value), expandable: false };
    if (typeof value === 'number') return { type: 'number', display: String(value), expandable: false };
    if (typeof value === 'string') {
      if (value.length > 100) {
        return { type: 'string', display: `"${value.slice(0, 100)}..."`, expandable: true };
      }
      return { type: 'string', display: `"${value}"`, expandable: false };
    }
    if (Array.isArray(value)) {
      return { type: 'array', display: `Array[${value.length}]`, expandable: true };
    }
    if (typeof value === 'object') {
      return { type: 'object', display: `Object{${Object.keys(value).length}}`, expandable: true };
    }
    return { type: 'unknown', display: String(value), expandable: false };
  }

  let showCopyNotification = $state(false);
</script>

{#if outputData}
  <div class="output-viewer">
    <div class="output-header">
      <h4>Output ({Object.keys(outputData).length} fields)</h4>
      <div class="output-actions">
        <div class="view-mode-toggle">
          <button
            class:active={viewMode === 'formatted'}
            onclick={() => viewMode = 'formatted'}
          >Formatted</button>
          <button
            class:active={viewMode === 'raw'}
            onclick={() => viewMode = 'raw'}
          >Raw</button>
          {#if Object.values(outputData).some(v => Array.isArray(v))}
            <button
              class:active={viewMode === 'table'}
              onclick={() => viewMode = 'table'}
            >Table</button>
          {/if}
        </div>
        <button class="action-btn" onclick={copyToClipboard} title="Copy to clipboard">
          📋 Copy
        </button>
        <button class="action-btn" onclick={downloadAsJson} title="Download as JSON">
          ⤓ Download
        </button>
      </div>
    </div>

    {#if showCopyNotification}
      <div class="copy-notification">Copied to clipboard!</div>
    {/if}

    <div class="output-content">
      {#if viewMode === 'raw'}
        <pre class="raw-json">{JSON.stringify(outputData, null, 2)}</pre>
      {:else if viewMode === 'formatted'}
        <div class="formatted-output">
          {#each Object.entries(outputData) as [key, value]}
            {@const display = getValueDisplay(value)}
            {@const description = getFieldDescription(key)}
            <div class="output-field">
              <div class="field-row">
                <span class="field-key">{key}</span>
                {#if description}
                  <span class="field-description" title={description}>ⓘ</span>
                {/if}
                <span class="field-value {display.type}">
                  {display.display}
                </span>
                {#if display.expandable}
                  <button
                    class="expand-btn"
                    onclick={() => {
                      if (expandedFields.has(key)) {
                        expandedFields.delete(key);
                        expandedFields = expandedFields;
                      } else {
                        expandedFields.add(key);
                        expandedFields = expandedFields;
                      }
                    }}
                  >
                    {expandedFields.has(key) ? '▼' : '▶'}
                  </button>
                {/if}
              </div>
              {#if expandedFields.has(key)}
                <div class="expanded-content">
                  <pre>{JSON.stringify(value, null, 2)}</pre>
                </div>
              {/if}
            </div>
          {/each}
        </div>
      {:else if viewMode === 'table'}
        {#each Object.entries(outputData) as [key, value]}
          {#if Array.isArray(value) && value.length > 0 && typeof value[0] === 'object'}
            <div class="table-section">
              <h5>{key} ({value.length} items)</h5>
              <table>
                <thead>
                  <tr>
                    {#each Object.keys(value[0]) as colKey}
                      <th>{colKey}</th>
                    {/each}
                  </tr>
                </thead>
                <tbody>
                  {#each value.slice(0, 10) as row}
                    <tr>
                      {#each Object.values(row) as cell}
                        <td>{typeof cell === 'object' ? JSON.stringify(cell) : cell}</td>
                      {/each}
                    </tr>
                  {/each}
                </tbody>
              </table>
              {#if value.length > 10}
                <div class="table-truncated">
                  ... and {value.length - 10} more items
                </div>
              {/if}
            </div>
          {/if}
        {/each}
      {/if}
    </div>
  </div>
{:else}
  <div class="no-output">
    <span class="no-output-icon">📭</span>
    <span>No output data available</span>
  </div>
{/if}

<style>
  .output-viewer {
    border: 1px solid #e2e8f0;
    border-radius: 0.5rem;
    overflow: hidden;
  }

  .output-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    background: #f8fafc;
    border-bottom: 1px solid #e2e8f0;
  }

  .output-header h4 {
    font-size: 0.875rem;
    font-weight: 600;
    color: #475569;
    margin: 0;
  }

  .output-actions {
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }

  .view-mode-toggle {
    display: flex;
    border: 1px solid #e2e8f0;
    border-radius: 0.375rem;
    overflow: hidden;
  }

  .view-mode-toggle button {
    padding: 0.25rem 0.5rem;
    font-size: 0.75rem;
    background: white;
    border: none;
    cursor: pointer;
  }

  .view-mode-toggle button.active {
    background: #3b82f6;
    color: white;
  }

  .action-btn {
    padding: 0.25rem 0.5rem;
    font-size: 0.75rem;
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 0.375rem;
    cursor: pointer;
  }

  .action-btn:hover {
    background: #f1f5f9;
  }

  .copy-notification {
    background: #16a34a;
    color: white;
    text-align: center;
    padding: 0.25rem;
    font-size: 0.75rem;
  }

  .output-content {
    padding: 0.75rem 1rem;
    max-height: 400px;
    overflow: auto;
  }

  .raw-json {
    font-family: monospace;
    font-size: 0.75rem;
    margin: 0;
    white-space: pre-wrap;
    word-break: break-all;
  }

  .formatted-output {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .output-field {
    border-bottom: 1px solid #f1f5f9;
    padding-bottom: 0.5rem;
  }

  .field-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .field-key {
    font-family: monospace;
    font-size: 0.875rem;
    font-weight: 600;
    color: #1e40af;
    min-width: 120px;
  }

  .field-description {
    color: #94a3b8;
    cursor: help;
    font-size: 0.75rem;
  }

  .field-value {
    font-family: monospace;
    font-size: 0.875rem;
    flex: 1;
  }

  .field-value.string { color: #16a34a; }
  .field-value.number { color: #2563eb; }
  .field-value.boolean { color: #9333ea; }
  .field-value.null { color: #64748b; }
  .field-value.array, .field-value.object { color: #64748b; }

  .expand-btn {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 0.625rem;
    color: #94a3b8;
    padding: 0.25rem;
  }

  .expanded-content {
    margin-top: 0.5rem;
    margin-left: 1rem;
    padding: 0.5rem;
    background: #f8fafc;
    border-radius: 0.375rem;
    border: 1px solid #e2e8f0;
  }

  .expanded-content pre {
    font-size: 0.75rem;
    margin: 0;
  }

  .table-section {
    margin-bottom: 1rem;
  }

  .table-section h5 {
    font-size: 0.75rem;
    color: #64748b;
    margin-bottom: 0.5rem;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.75rem;
  }

  th, td {
    border: 1px solid #e2e8f0;
    padding: 0.5rem;
    text-align: left;
  }

  th {
    background: #f8fafc;
    font-weight: 600;
  }

  .table-truncated {
    font-size: 0.75rem;
    color: #64748b;
    margin-top: 0.5rem;
    font-style: italic;
  }

  .no-output {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 1rem;
    color: #64748b;
    font-size: 0.875rem;
  }

  .no-output-icon {
    font-size: 1.25rem;
  }
</style>
```

### 12.4 タスク間データフロー表示

#### 12.4.1 概要

ワークフローにおいて、前タスクの出力が次タスクの入力としてどのように使用されているかを視覚化する。

```
┌──────────────────────────────────────────────────────────────────┐
│  Data Flow                                                        │
│                                                                   │
│  Task 1: google_search                                           │
│  ├─ output.documents ────────────▶ Task 2: file_reader.input.files│
│  └─ output.search_summary ───────▶ Task 4: report.input.summary  │
│                                                                   │
│  Task 2: file_reader                                             │
│  └─ output.content ──────────────▶ Task 3: analyzer.input.text   │
│                                                                   │
│  Task 3: analyzer                                                │
│  └─ output.analysis ─────────────▶ Task 4: report.input.data     │
└──────────────────────────────────────────────────────────────────┘
```

#### 12.4.2 データフロー取得ロジック

```typescript
// src/lib/utils/data-flow-analyzer.ts

interface DataFlowEdge {
  fromTask: string;
  fromField: string;
  toTask: string;
  toField: string;
}

/**
 * interfaceDefinitionsとタスクの入出力データから
 * データフローの関係を分析する
 */
export function analyzeDataFlow(
  tasks: TaskProgressItem[],
  interfaceDefinitions: InterfaceDefinitions
): DataFlowEdge[] {
  const edges: DataFlowEdge[] = [];

  // 各タスクの入力データを確認
  for (let i = 1; i < tasks.length; i++) {
    const currentTask = tasks[i];
    const inputData = currentTask.inputData;

    if (!inputData) continue;

    // 入力データの各フィールドについて、
    // 前のタスクの出力データと値を比較
    for (const [inputField, inputValue] of Object.entries(inputData)) {
      for (let j = 0; j < i; j++) {
        const prevTask = tasks[j];
        const outputData = prevTask.outputData;

        if (!outputData) continue;

        for (const [outputField, outputValue] of Object.entries(outputData)) {
          if (JSON.stringify(inputValue) === JSON.stringify(outputValue)) {
            edges.push({
              fromTask: prevTask.taskId,
              fromField: outputField,
              toTask: currentTask.taskId,
              toField: inputField
            });
          }
        }
      }
    }
  }

  return edges;
}
```

### 12.5 出力結果の状態別表示

| タスクステータス | 出力表示 | アクション |
|-----------------|---------|----------|
| `pending` | 「タスク実行待ち」メッセージ | なし |
| `running` | 「実行中...」 + スピナー | なし |
| `succeeded` | 出力データを表示 | Copy, Download |
| `failed` | エラーメッセージを赤色で表示 | Retry, View Error |
| `skipped` | 「スキップされました」メッセージ | なし |

### 12.6 大容量出力データの取り扱い

#### 12.6.1 制限値

| 項目 | 制限 |
|------|------|
| 表示上限 | 100KB (それ以上は省略表示) |
| 配列表示上限 | 100件 (それ以上はページング) |
| 文字列表示上限 | 10,000文字 (それ以上は折りたたみ) |
| ダウンロード上限 | なし (フルデータをダウンロード可能) |

#### 12.6.2 省略表示UI

```
┌──────────────────────────────────────────────────────────────┐
│  Output (Large Data: 2.3MB)                                  │
│                                                              │
│  ⚠️ Output data is too large to display fully.               │
│                                                              │
│  Preview (first 100KB):                                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ {                                                      │  │
│  │   "items": [/* 1,234 items */],                       │  │
│  │   "total": 1234,                                      │  │
│  │   ...                                                 │  │
│  │ }                                                      │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  [Download Full Output (2.3MB)]                             │
└──────────────────────────────────────────────────────────────┘
```

### 12.7 TaskProgressコンポーネントへの統合

Section 4.5 の TaskProgress コンポーネントを以下のように更新：

```svelte
<!-- 更新版: タスク詳細展開部分 -->
{#if expandedTaskId === task.taskId}
  <div class="task-details">
    <!-- 入力データ -->
    {#if task.inputData}
      <div class="detail-section">
        <div class="section-header">
          <h4>Input</h4>
          <div class="section-actions">
            <button onclick={() => copyJson(task.inputData)}>📋</button>
            <button onclick={() => downloadJson(task.inputData, `${task.taskId}-input`)}>⤓</button>
          </div>
        </div>
        <pre>{JSON.stringify(task.inputData, null, 2)}</pre>
      </div>
    {/if}

    <!-- 出力データ（OutputViewerコンポーネント使用） -->
    {#if task.status === 'succeeded' || task.outputData}
      <OutputViewer
        outputData={task.outputData}
        outputSchema={task.outputSchema}
        taskName={task.taskName}
      />
    {:else if task.status === 'running'}
      <div class="output-placeholder running">
        <span class="spinner">🔄</span>
        <span>タスク実行中...</span>
      </div>
    {:else if task.status === 'pending'}
      <div class="output-placeholder pending">
        <span>⏳</span>
        <span>タスク実行待ち</span>
      </div>
    {/if}

    <!-- エラー情報 -->
    {#if task.error}
      <div class="detail-section error">
        <h4>Error</h4>
        <pre class="error-message">{task.error}</pre>
        {#if task.status === 'failed'}
          <button class="retry-btn" onclick={() => retryTask(task.taskId)}>
            🔄 Retry This Task
          </button>
        {/if}
      </div>
    {/if}

    <!-- 実行時間情報 -->
    <div class="detail-meta">
      {#if task.startedAt}
        <span>Started: {task.startedAt.toLocaleString()}</span>
      {/if}
      {#if task.finishedAt}
        <span>Finished: {task.finishedAt.toLocaleString()}</span>
      {/if}
      {#if task.durationMs}
        <span>Duration: {formatDuration(task.durationMs)}</span>
      {/if}
    </div>
  </div>
{/if}
```

---

## 13. 参考資料

- [JobQueue OpenAPI Spec](http://localhost:8001/docs)
- [JSON Schema Specification](https://json-schema.org/)
- [Issue #293 作業計画書](./work-plan.md)
- [Issue #293 設計方針書](./design-policy.md)
