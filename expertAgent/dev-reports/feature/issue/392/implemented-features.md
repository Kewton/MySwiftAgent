# Issue #392 実装機能一覧

## Issue: Bug: workflow_name が重複形式 (task_task_001_task_001) になる

## 実装日: 2026-01-22

---

## 1. 実装された機能

### 機能1: generateWorkflowName 重複回避ロジック

| 項目 | 内容 |
|------|------|
| ファイル | `mySwiftAgentCore/src/taskflowGeneratorAgent/prompts/PromptBuilder.ts` |
| 関数名 | `generateWorkflowName(task: TaskGenerationRequest): string` |
| 行番号 | 283-301 |
| 目的 | ワークフロー名の重複（例: `task_task_001_task_001`）を回避 |

#### 実装詳細

```typescript
private generateWorkflowName(task: TaskGenerationRequest): string {
  const baseName = task.name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');

  // Issue #392: Avoid duplication when baseName equals or contains task_id
  if (baseName === task.task_id || baseName.includes(task.task_id)) {
    return task.task_id;
  }

  // Issue #392: Fallback for empty or generic names
  if (!baseName || baseName === 'task') {
    return task.task_id;
  }

  return `${baseName}_${task.task_id}`;
}
```

#### 呼び出し箇所
- `PromptBuilder.ts:191` - プロンプト生成時に使用

### 機能2: LLMプロンプト タスク命名規則

| 項目 | 内容 |
|------|------|
| ファイル | `expertAgent/prompts/task_breakdown/default.yaml` |
| セクション | `### タスク命名規則 (Issue #392)` |
| 行番号 | 95-103 |
| 目的 | LLMがID形式のタスク名を生成しないようにする |

#### 追加内容

```yaml
### タスク命名規則 (Issue #392)
- **name**: タスクの内容を表す**意味のある名前**を使用してください
- **絶対禁止**: `task_001`、`task_002` などの**ID形式の名前は禁止**です
- 名前は日本語または英語で、タスクの目的が明確に伝わるものにしてください

例:
- OK 正しい: "Gmail検索", "検索結果の分析", "レポート送信", "Web Search", "Data Analysis"
- NG 間違い: "task_001", "task_002", "Task 1" (IDと重複し、システムエラーになります)
```

---

## 2. テストケース

| テストファイル | `mySwiftAgentCore/tests/unit/taskflowGeneratorAgent/prompts/PromptBuilder.test.ts` |
|--------------|---|

### 追加されたテスト（6件）

| テスト名 | 検証内容 |
|---------|---------|
| `should not duplicate task_id in workflow name when task name equals task_id` | task.name = "task_001" の場合、`task_001` を返す |
| `should not duplicate task_id in workflow name when task name contains task_id` | task.name = "my_task_001_test" の場合、`task_001` を返す |
| `should generate proper workflow name when task name is meaningful` | task.name = "Gmail Search" の場合、`gmail_search_task_001` を返す |
| `should fallback to task_id when task name is empty` | task.name = "" の場合、`task_001` を返す |
| `should fallback to task_id when task name is generic "task"` | task.name = "task" の場合、`task_001` を返す |
| `should handle Japanese task names correctly` | task.name = "メール検索" の場合、正しく変換 |

---

## 3. デッドコード検出結果

| 対象 | 結果 |
|------|------|
| `generateWorkflowName` | ✅ 使用中（PromptBuilder.ts:191で呼び出し） |

**デッドコードなし**

---

## 4. 関連Issue

- Issue #390: E2Eテストで本問題を発見
- Issue #361: mySwiftAgentCore統合

---

## 5. ファイル変更サマリ

| ファイル | 変更種別 | 変更行数 |
|---------|---------|---------|
| `mySwiftAgentCore/src/taskflowGeneratorAgent/prompts/PromptBuilder.ts` | 修正 | +15行 |
| `expertAgent/prompts/task_breakdown/default.yaml` | 追加 | +10行 |
| `mySwiftAgentCore/tests/unit/taskflowGeneratorAgent/prompts/PromptBuilder.test.ts` | 追加 | +100行 |
