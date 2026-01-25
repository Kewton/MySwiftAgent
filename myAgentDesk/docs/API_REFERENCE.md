# myAgentDesk API Reference

myAgentDeskが提供するフロントエンドAPI（内部API）の仕様です。

## 概要

myAgentDeskはSvelteKitベースのWeb UIです。
内部的にバックエンドAPIと通信し、ジョブ管理とワークフロー実行を提供します。

## フロントエンドルート

| パス | 説明 |
|------|------|
| `/` | ダッシュボード |
| `/jobs` | ジョブ一覧 |
| `/jobs/new` | 新規ジョブ作成 |
| `/jobs/{id}` | ジョブ詳細 |
| `/workflows` | ワークフロー一覧 |
| `/settings` | 設定 |

## バックエンド連携

### ExpertAgent API

ジョブ生成・実行はexpertAgentを経由します。

```typescript
// ジョブ生成
const response = await fetch('/api/jobs/generate', {
  method: 'POST',
  body: JSON.stringify({
    name: 'Job Name',
    prompt: 'User prompt'
  })
});
```

### mySwiftAgentCore API

ワークフロー実行はmySwiftAgentCoreを使用します。

```typescript
// ワークフロー実行
const response = await fetch('/api/workflows/execute', {
  method: 'POST',
  body: JSON.stringify({
    workflow_id: 'workflow-id',
    inputs: { ... }
  })
});
```

## コンポーネント

### ジョブカード

```svelte
<JobCard
  job={jobData}
  on:run={handleRun}
  on:delete={handleDelete}
/>
```

**Props**:
| Prop | 型 | 説明 |
|------|-----|------|
| `job` | `Job` | ジョブデータ |

**Events**:
| イベント | ペイロード | 説明 |
|---------|----------|------|
| `run` | `{ id: string }` | 実行ボタンクリック |
| `delete` | `{ id: string }` | 削除ボタンクリック |

### ワークフローエディタ

```svelte
<WorkflowEditor
  workflow={workflowData}
  on:save={handleSave}
/>
```

## ストア

### jobStore

```typescript
import { jobStore } from '$lib/stores/jobStore';

// ジョブ一覧取得
await jobStore.fetchAll();

// ジョブ作成
await jobStore.create({ name, prompt });

// ジョブ実行
await jobStore.run(jobId);
```

### workflowStore

```typescript
import { workflowStore } from '$lib/stores/workflowStore';

// ワークフロー一覧取得
await workflowStore.fetchAll();

// ワークフロー実行
await workflowStore.execute(workflowId, inputs);
```

## 環境変数

| 変数 | 説明 | デフォルト |
|------|------|----------|
| `PUBLIC_API_BASE_URL` | バックエンドAPIのURL | `http://localhost:8004` |
| `PUBLIC_WORKFLOW_API_URL` | ワークフローAPIのURL | `http://localhost:8006` |

## エラーハンドリング

```typescript
try {
  await jobStore.run(jobId);
} catch (error) {
  if (error instanceof ApiError) {
    // API エラー
    toast.error(error.message);
  } else {
    // その他のエラー
    toast.error('予期しないエラーが発生しました');
  }
}
```

## 関連ドキュメント

- [Getting Started Guide](./guides/getting-started.md)
- [expertAgent API](../../expertAgent/docs/API_REFERENCE.md)
- [mySwiftAgentCore API](../../mySwiftAgentCore/docs/API_REFERENCE.md)
