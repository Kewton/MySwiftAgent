# タスクチェーン データ契約仕様書

**バージョン**: 1.0.0
**作成日**: 2026-01-09
**関連Issue**: #342
**ステータス**: Draft

---

## 1. 概要

本ドキュメントは、Job Generator V2 タスクチェーンにおけるコンポーネント間のデータ契約を定義する。
暗黙の前提を排除し、各コンポーネントが従うべきデータ形式を明文化する。

### 1.1 対象コンポーネント

| コンポーネント | 役割 | ファイル |
|--------------|------|---------|
| **expertAgent** | Job/TaskMaster生成、body_template定義 | `master_manager.py` |
| **jobqueue** | タスク実行、出力抽出・変換 | `worker.py` |
| **graphAiServer** | ワークフロー実行、source injection | `graphai.ts` |

### 1.2 データフロー概要

```
expertAgent (Job生成)
    ↓ body_template
jobqueue (タスク実行)
    ↓ HTTP Request
graphAiServer (ワークフロー実行)
    ↓ GraphAI Response
jobqueue (出力抽出)
    ↓ output_data
次タスク or 完了
```

---

## 2. Job Body 形式

### 2.1 標準形式（必須）

Job Masterの`body`フィールドは以下の形式に従う：

```json
{
  "user_input": {
    // 動的入力データ（必須）
    // ワークフロー実行に必要なパラメータ
  },
  "recipient": "email@example.com",  // 静的パラメータ（オプション）
  "other_static_param": "value"      // 静的パラメータ（オプション）
}
```

### 2.2 バリデーションルール

| フィールド | 必須 | 型 | 説明 |
|-----------|------|---|------|
| `user_input` | ✅ 必須 | `object` | 動的入力データのコンテナ |
| その他 | オプション | `any` | 静的パラメータ |

### 2.3 バリデーション実装

```python
# jobqueue/app/api/v1/jobs.py
def validate_job_body(body: dict) -> None:
    """Validate job body structure."""
    if not isinstance(body, dict):
        raise ValueError("job.body must be a dictionary")
    if "user_input" not in body:
        raise ValueError("job.body must contain 'user_input' field")
```

---

## 3. body_template 形式

### 3.1 Task 0（最初のタスク）

```json
{
  "user_input": "{{job.body.user_input}}",
  "job_params": "{{job.body}}"
}
```

**重要**: `{{job.body}}`ではなく`{{job.body.user_input}}`を使用すること。

### 3.2 Task N（2番目以降のタスク）

```json
{
  "user_input": "{{tasks[N-1].output_data}}",
  "job_params": "{{job.body}}"
}
```

### 3.3 テンプレート解決後のデータ構造

graphAiServerへ送信されるリクエストボディ：

```json
{
  "user_input": { /* 前タスクの出力 or job.body.user_input */ },
  "job_params": { /* job.body全体 */ },
  "model_name": "taskmaster/{task_master_id}/workflow_{job_master_id}"
}
```

---

## 4. graphAiServer source構造

### 4.1 source injection形式

graphAiServerは`source`ノードに以下の構造を注入する：

```javascript
// graphAiServer/src/services/graphai.ts
const sourceData = {
  user_input: mergedUserInput,  // リクエストのuser_input + job_params
  job_params: job_params || {}  // リクエストのjob_params
};
graph.injectValue("source", sourceData);
```

### 4.2 実際のsource構造

```yaml
source:
  user_input:
    # 動的データ（前タスクの出力または初期入力）
    query: "検索キーワード"
    url: "https://example.com"
    # job_paramsからマージされたデータ
    recipient: "email@example.com"
  job_params:
    # job.body全体
    user_input: {...}
    recipient: "email@example.com"
```

### 4.3 ワークフローからの参照ルール

| パス形式 | 用途 | 例 |
|---------|------|---|
| `:source.user_input.*` | 動的データへのアクセス | `:source.user_input.query` |
| `:source.job_params.*` | 静的パラメータへのアクセス | `:source.job_params.recipient` |
| `:source.*` | **非推奨** | 使用禁止 |

### 4.4 参照パス変換表

| ワークフローの参照 | 実際のデータパス | 備考 |
|------------------|-----------------|------|
| `:source.user_input.query` | `source.user_input.query` | ✅ 推奨 |
| `:source.user_input.recipient` | `source.user_input.recipient` | ✅ job_paramsからマージ |
| `:source.job_params.recipient` | `source.job_params.recipient` | ✅ 明示的参照 |
| `:source.query` | N/A | ❌ 動作しない |

---

## 5. GraphAI Response形式

### 5.1 標準レスポンス構造

```json
{
  "results": {
    "source": { /* 入力データ */ },
    "node_1": { /* ノード1の結果 */ },
    "node_2": { /* ノード2の結果 */ },
    "output": {
      "result": { /* 最終出力 */ }
    }
  },
  "logs": [
    {"nodeId": "source", "state": "completed"},
    {"nodeId": "node_1", "state": "completed"},
    {"nodeId": "output", "state": "completed"}
  ],
  "errors": {}
}
```

### 5.2 出力ノード命名規則

| ルール | 説明 |
|-------|------|
| **ノード名** | 最終出力ノードは `output` という名前を使用する（必須） |
| **isResult属性** | `isResult: true` を設定する（必須） |

**ワークフロー例**:
```yaml
output:
  agent: copyAgent
  inputs:
    result: :previous_node.result
  isResult: true
```

### 5.3 出力ノード構造

| パターン | 構造 | 抽出結果 |
|---------|------|---------|
| ネストあり | `{"output": {"result": {...}}}` | `{...}` |
| ネストなし | `{"output": {...}}` | `{...}` |

---

## 6. 出力抽出・変換ルール

### 6.1 抽出フロー

```
GraphAI Response
    ↓
_extract_graphai_output()
    ↓ "output"ノードを抽出
    ↓ "result"フィールドがあればアンラップ
_transform_to_interface()
    ↓ output_interfaceに基づき変換
task.output_data
```

### 6.2 抽出ロジック（優先順位）

1. `results.output.result` が存在 → これを抽出
2. `results.output` が存在 → これを抽出
3. どちらも存在しない → `results`全体を返す（フォールバック）

### 6.3 Interface変換ルール

`output_interface`が定義されている場合：

```python
# 入力: raw_output = {"search_results": [...], "metadata": {...}}
# output_interface = {"properties": {"search_results": {...}}}
# 出力: {"search_results": [...]}
```

---

## 7. タスクチェーン データ受け渡し

### 7.1 Task 0 → Task 1

```
Task 0:
  body_template: {"user_input": "{{job.body.user_input}}", ...}
  ワークフロー実行
  出力: {"search_results": [...]}

Task 1:
  body_template: {"user_input": "{{tasks[0].output_data}}", ...}
  source.user_input = {"search_results": [...]}
  ワークフロー参照: :source.user_input.search_results
```

### 7.2 完全なデータフロー図

```
┌─────────────────────────────────────────────────────────────────┐
│ Job Master                                                       │
│ body: {"user_input": {"query": "..."}, "recipient": "..."}     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Task 0 (Google検索)                                              │
│ body_template: {"user_input": "{{job.body.user_input}}", ...}  │
│                                                                  │
│ graphAiServer Request:                                          │
│ {"user_input": {"query": "..."}, "job_params": {...}}          │
│                                                                  │
│ source構造:                                                      │
│ {user_input: {query: "...", recipient: "..."}, job_params: {...}}│
│                                                                  │
│ ワークフロー: :source.user_input.query                           │
│                                                                  │
│ 出力: {"search_results": [...]}                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Task 1 (要約)                                                    │
│ body_template: {"user_input": "{{tasks[0].output_data}}", ...} │
│                                                                  │
│ graphAiServer Request:                                          │
│ {"user_input": {"search_results": [...]}, "job_params": {...}} │
│                                                                  │
│ source構造:                                                      │
│ {user_input: {search_results: [...], recipient: "..."}, ...}   │
│                                                                  │
│ ワークフロー: :source.user_input.search_results                  │
│                                                                  │
│ 出力: {"email_subject": "...", "email_body": "..."}            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Task 2 (メール送信)                                              │
│ body_template: {"user_input": "{{tasks[1].output_data}}", ...} │
│                                                                  │
│ source構造:                                                      │
│ {user_input: {email_subject: "...", email_body: "...",         │
│               recipient: "..."}, job_params: {...}}             │
│                                                                  │
│ ワークフロー:                                                    │
│   to: :source.user_input.recipient                              │
│   subject: :source.user_input.email_subject                     │
│   body: :source.user_input.email_body                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. エラーケースと対応

### 8.1 データ契約違反のエラー

| エラー | 原因 | 対応 |
|-------|------|------|
| `job.body must contain 'user_input' field` | Job bodyにuser_inputがない | Job body形式を修正 |
| `No 'output' node found` | ワークフローにoutputノードがない | ワークフローを修正 |
| `:source.X is undefined` | sourceパスが間違っている | `:source.user_input.X`形式に修正 |
| `HTTP 422: field required` | 必須フィールドが欠落 | データフローを確認 |

### 8.2 デバッグ手順

```bash
# 1. Job bodyの確認
curl "http://localhost:8001/api/v1/job-masters/{id}" | jq '.body'

# 2. Task Master body_templateの確認
curl "http://localhost:8001/api/v1/task-masters/{id}" | jq '.body_template'

# 3. タスク出力の確認
curl "http://localhost:8001/api/v1/jobs/{job_id}/tasks" | jq '.tasks[] | {order, output_data}'

# 4. ワークフローsourceパスの確認
grep -r ":source" graphAiServer/config/graphai/taskmaster/{task_master_id}/
```

---

## 9. 移行ガイド

### 9.1 既存ワークフローの移行

1. **出力ノード名の変更**
   ```yaml
   # Before
   format_output:
     isResult: true

   # After
   output:
     isResult: true
   ```

2. **sourceパスの変更**
   ```yaml
   # Before
   inputs:
     query: :source.query

   # After
   inputs:
     query: :source.user_input.query
   ```

### 9.2 既存Job Masterの移行

```bash
# body形式の更新
curl -X PUT "http://localhost:8001/api/v1/job-masters/{id}" \
  -H "Content-Type: application/json" \
  -d '{
    "body": {
      "user_input": {},
      "recipient": "email@example.com"
    }
  }'
```

---

## 10. 変更履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|---------|
| 1.0.0 | 2026-01-09 | 初版作成 |

---

## 11. 関連ドキュメント

- [V2タスクチェーン根本原因分析](../../dev-reports/feature/issue/342/v2-taskchain-root-cause-analysis.md)
- [V2タスクチェーン対策案](../../dev-reports/feature/issue/342/v2-taskchain-remediation-plan.md)
- [GraphAIワークフロー生成ルール](../../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)
- [サービス依存関係](../arch/service-dependencies.md)
