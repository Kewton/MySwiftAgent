# Task 3: Gmail送信ワークフロー バグ分析レポート

## 概要

- **タスク名**: メール送信
- **TaskMaster ID**: `tm_01KEF4YWQDBX8GJEEZTSS0NTVQ`
- **JobMaster ID**: `jm_01KEF4YWQMF3KG2BNSH0B7YAK3`
- **分析日**: 2026-01-09

## 症状

ジョブ実行時にHTTP 422エラーが発生し、Gmail送信APIの呼び出しに失敗。

```
HTTP 422: Validation Error - missing required fields
```

---

## 問題点一覧

### 問題1: ソースパス参照の誤り

| パラメータ | AI生成（誤） | 正解 |
|-----------|-------------|------|
| subject | `:extract_email.email_subject` | `:source.user_input.email_subject` |
| body | `:extract_email.email_body` | `:source.user_input.email_body` |

**原因**: AIは中間ノード経由でデータを参照しようとしたが、正しくは`source`から直接参照すべき。

### 問題2: 不要な中間ノードの作成

**AI生成コード（誤）**:
```yaml
extract_email:
  agent: copyAgent
  inputs:
    email_subject: :source.email_subject
    email_body: :source.email_body
  params:
    namedKey: email_data
```

この中間ノードは以下の問題がある：
1. `namedKey`パラメータの使用方法が誤っている
2. ソースパスが誤っている（`user_input`プレフィックスが欠落）
3. そもそも不要なノード

### 問題3: タスクチェーンのデータ構造理解不足

Task 2の出力がTask 3の`source`に注入される際の構造：

```json
{
  "user_input": {
    "email_subject": "件名",
    "email_body": "本文"
  },
  "job_params": {"query": "大谷翔平"},
  "model_name": "taskmaster/..."
}
```

AIは`source.email_subject`で直接アクセスできると誤解したが、実際は`source.user_input.email_subject`でアクセスする必要がある。

### 問題4: タイムアウト単位の誤り（共通問題）

| 項目 | AI生成（誤） | 正解 | 単位 |
|------|-------------|------|------|
| timeout | `60` | `60000` | ミリ秒 |

---

## 修正前後の比較

### 修正前（AI生成）

```yaml
version: '0.5'
nodes:
  source: {}
  extract_email:
    agent: copyAgent
    inputs:
      email_subject: :source.email_subject
      email_body: :source.email_body
    params:
      namedKey: email_data
  send_email:
    agent: fetchAgent
    inputs:
      url: ${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/gmail/send
      method: POST
      body:
        to: "newtons.boiled.clock@gmail.com"
        subject: :extract_email.email_subject
        body: :extract_email.email_body
    console:
      after: true
    timeout: 60
  output:
    agent: copyAgent
    inputs:
      message_id: :send_email.result.message_id
      status: :send_email.result.success
    isResult: true
```

### 修正後（手動修正）

```yaml
version: '0.5'
nodes:
  source: {}

  # メール送信
  send_email:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/utility/gmail/send
      method: POST
      body:
        to: "newtons.boiled.clock@gmail.com"
        subject: :source.user_input.email_subject
        body: :source.user_input.email_body
    console:
      after: true
    timeout: 60000

  # 出力をフォーマット
  output:
    agent: copyAgent
    inputs:
      message_id: :send_email.result.message_id
      status: :send_email.result.success
      sent_to: :send_email.result.sent_to
      subject: :send_email.result.subject
    isResult: true
```

---

## AIエージェント改善提案

### 1. タスクチェーンのデータフロー図示

マルチタスクジョブにおける各タスク間のデータフローを図示し、`source`に注入されるデータ構造を明確化。

```
Job Request Body
     ↓
[Task 1: Google検索]
     ↓ output_data
body_template変換: {"user_input": output_data, "job_params": job.body}
     ↓
[Task 2: メール生成]
     ↓ output_data
body_template変換: {"user_input": output_data, "job_params": job.body}
     ↓
[Task 3: メール送信]
```

### 2. 中間ノード不要化ルールの明確化

- `source`から直接アクセスできる場合、中間ノードは不要
- `copyAgent`の`namedKey`は出力キー名の変更に使用（入力変換ではない）

### 3. 出力フィールドの完全性

APIレスポンスの全フィールドを`output`ノードに含めることで、デバッグ情報を充実させる。

---

## 検証結果

修正後のワークフローでジョブを実行した結果、Task 3は成功：

```json
{
  "status": "SUCCEEDED",
  "output_data": {
    "message_id": "19...",
    "status": true,
    "sent_to": "newtons.boiled.clock@gmail.com",
    "subject": "大谷翔平選手 最新ニュースまとめ"
  },
  "duration_ms": 524
}
```
