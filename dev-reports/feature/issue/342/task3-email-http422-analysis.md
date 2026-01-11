# Task 3 (メール送信) HTTP 422 エラー分析レポート

**作成日**: 2026-01-09
**関連Issue**: #342
**ステータス**: 未解決 - 根本原因特定済み

---

## 1. エラー概要

```json
{
  "errors": {
    "send_email": {
      "message": "HTTP error: 422"
    }
  }
}
```

- **発生タスク**: Task 3 (メール送信)
- **タスクマスター**: `tm_01KEH9NMXSBJYCDR27KJ3FD7KC`
- **ワークフロー**: `taskmaster/tm_01KEH9NMXSBJYCDR27KJ3FD7KC/workflow_jm_01KEH9NMY2WHPPSBFV9W5D2R3V.yml`
- **エラーノード**: `send_email`

---

## 2. 根本原因（3つの問題）

### 問題1: `recipient`フィールドの欠落（致命的）

**症状**: Gmail Send APIの必須フィールド`to`が提供されていない

**Gmail Send API要件**:
```python
class GmailSendRequest(BaseModel):
    to: str | List[str]  # 必須
    subject: str         # 必須
    body: str            # 必須
```

**ワークフロー**:
```yaml
send_email:
  body:
    to: :source.recipient      # ← このフィールドが存在しない
    subject: :source.subject
    body: :source.body
```

**原因**:
- Job説明文に `newtons.boiled.clock@gmail.com` と記載されているが、データフローに組み込まれていない
- `recipient`フィールドを生成・伝達する仕組みがない

---

### 問題2: sourceパスの不一致

**ワークフローの期待するパス**:
```yaml
to: :source.recipient
subject: :source.subject
body: :source.body
```

**実際のデータ構造** (graphAiServer source injection):
```json
{
  "user_input": {
    "email_subject": "検索結果が未定義です",
    "email_body": "申し訳ありませんが..."
  },
  "job_params": {...}
}
```

**正しいパス**:
```yaml
to: :source.user_input.recipient     # または job_params から取得
subject: :source.user_input.email_subject
body: :source.user_input.email_body
```

---

### 問題3: Task 2の入力データ問題（連鎖的影響）

**Task 2のワークフロー**:
```yaml
build_prompt:
  inputs:
    results: :source.search_results    # ← このパスが間違っている
```

**Task 1の実際の出力データ**:
```json
{
  "source": {
    "user_input": {"query": "大谷翔平の妻"},
    "job_params": {...}
  },
  "google_search": {
    "search_results": [...]
  }
}
```

**問題**:
- Task 2は `:source.search_results` を期待
- しかし Task 1出力では `google_search.search_results` にデータがある
- jobqueueの`_extract_graphai_output()`が `output` ノードを探すが、Task 1ワークフローは `format_output` を使用
- 結果: Task 2は「検索結果が未定義です」というエラーメッセージを生成

**Task 2の出力** (実際):
```json
{
  "email_subject": "検索結果が未定義です",
  "email_body": "申し訳ありませんが、検索結果が存在しないため..."
}
```

---

## 3. データフロー図

```
Job Body
  │
  ├─ user_input: {"query": "大谷翔平の妻"}
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ Task 1: Google検索                                                │
│ ・body_template: user_input = {{job.body.user_input}}           │
│ ・ワークフロー: :source.user_input.query を使用                    │
│ ・出力: 全GraphAI結果（source, google_search含む）                 │
│   → 問題: output_dataにsearch_resultsが直接ない                   │
└─────────────────────────────────────────────────────────────────┘
  │
  │ output_data: {source: {...}, google_search: {search_results: [...]}}
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ Task 2: 検索結果の要約                                            │
│ ・body_template: user_input = {{tasks[0].output_data}}          │
│ ・ワークフロー: :source.search_results を期待                      │
│   → 問題: 実際は :source.user_input.google_search.search_results │
│ ・結果: "検索結果が未定義です" というエラー出力                      │
└─────────────────────────────────────────────────────────────────┘
  │
  │ output_data: {email_subject: "検索結果が未定義です", email_body: "..."}
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ Task 3: メール送信                                                │
│ ・body_template: user_input = {{tasks[1].output_data}}          │
│ ・ワークフロー:                                                   │
│   - to: :source.recipient       → 存在しない (HTTP 422)          │
│   - subject: :source.subject    → 存在しない                      │
│   - body: :source.body          → 存在しない                      │
│   正しいパス:                                                     │
│   - to: :source.job_params.recipient または定数                   │
│   - subject: :source.user_input.email_subject                    │
│   - body: :source.user_input.email_body                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. 修正方針

### 4.1 短期修正（ワークフロー修正）

#### Task 3 ワークフロー修正
```yaml
# 現在
send_email:
  body:
    to: :source.recipient
    subject: :source.subject
    body: :source.body

# 修正案
send_email:
  body:
    to: :source.job_params.recipient       # job.bodyからrecipientを取得
    subject: :source.user_input.email_subject
    body: :source.user_input.email_body
```

#### Job Bodyにrecipientを追加
Job作成時に`recipient`を含める:
```json
{
  "user_input": {"query": "大谷翔平の妻"},
  "recipient": "newtons.boiled.clock@gmail.com"
}
```

#### Task 2 ワークフロー修正
```yaml
# 現在
build_prompt:
  inputs:
    results: :source.search_results

# 修正案
build_prompt:
  inputs:
    results: :source.user_input.google_search.search_results
```

### 4.2 中期修正（アーキテクチャ改善）

1. **Task 1の出力正規化**:
   - `format_output`ノードを`output`にリネーム
   - またはjobqueue workerの`_extract_graphai_output()`を改善

2. **Interface-based変換の強化**:
   - output_interfaceに基づいてデータを正規化
   - `search_results`フィールドを直接抽出

3. **recipientの伝達メカニズム**:
   - Job Masterの`body`にデフォルト`recipient`を設定
   - または専用のパラメータインターフェースを追加

---

## 5. 影響を受けるファイル

| ファイル | 修正内容 |
|---------|---------|
| `graphAiServer/config/graphai/taskmaster/tm_01KEH9NMXSBJYCDR27KJ3FD7KC/workflow_jm_01KEH9NMY2WHPPSBFV9W5D2R3V.yml` | sourceパス修正 |
| `graphAiServer/config/graphai/taskmaster/tm_01KEH9NMXGDTH720AMYP1RG3J5/workflow_jm_01KEH9NMY2WHPPSBFV9W5D2R3V.yml` | search_resultsパス修正 |
| jobqueue DB: `job_masters` | body に recipient 追加 |
| myAgentDesk: 実行パラメータ | recipient フィールド追加 |

---

## 6. 検証手順

### 直接API呼び出しテスト
```bash
# Gmail Send API検証
curl -X POST "http://localhost:8004/aiagent-api/v1/utility/gmail/send" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "newtons.boiled.clock@gmail.com",
    "subject": "テスト件名",
    "body": "テスト本文"
  }'
```

### ワークフロー修正後のテスト
```bash
# graphAiServer直接呼び出し
curl -X POST "http://localhost:8005/api/v1/myagent" \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": {
      "email_subject": "テスト件名",
      "email_body": "テスト本文",
      "recipient": "newtons.boiled.clock@gmail.com"
    },
    "model_name": "taskmaster/tm_01KEH9NMXSBJYCDR27KJ3FD7KC/workflow_jm_01KEH9NMY2WHPPSBFV9W5D2R3V"
  }'
```

---

## 7. 推奨アクション（優先度順）

### 優先度: 高
1. [ ] Task 3ワークフローのsourceパスを修正
2. [ ] Job Masterのbodyにrecipientフィールドを追加
3. [ ] Task 2ワークフローのsearch_resultsパスを修正

### 優先度: 中
4. [ ] Task 1ワークフローの出力ノード名を`output`に変更
5. [ ] jobqueue workerの`_extract_graphai_output()`を改善

### 優先度: 低
6. [ ] Interface変換ロジックの強化
7. [ ] E2Eテストの追加

---

## 8. 関連情報

- **前回修正**: Task 1のHTTP 422エラー（body_template修正）
- **関連Issue**: #342 (V2 Workflow Generator)
- **関連ファイル**: `http-422-error-investigation-report.md`
