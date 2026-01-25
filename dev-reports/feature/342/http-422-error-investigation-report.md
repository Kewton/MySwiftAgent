# HTTP 422 エラー調査レポート

**作成日**: 2026-01-09
**関連Issue**: #342
**ステータス**: Google検索エラー解決済み / メール送信エラー未解決

---

## 1. 概要

myAgentDeskからワークフロー実行時にHTTP 422エラーが発生する問題を調査・修正しました。

### 対象ワークフロー
- **Job Master**: `jm_01KEH9NMY2WHPPSBFV9W5D2R3V`
- **Task Master**: `tm_01KEH9NMX4QXABSWVDP6989650` (Google検索)
- **Workflow**: `taskmaster/tm_01KEH9NMX4QXABSWVDP6989650/workflow_jm_01KEH9NMY2WHPPSBFV9W5D2R3V.yml`

---

## 2. 解決済みの問題

### 2.1 問題1: `num`パラメータ制限違反

**症状**: Google Search APIがHTTP 422を返す

**原因**: ワークフロー内の`num: 10`が`SearchUtilityRequest`スキーマの制限`le=3`を超過

**修正内容**:
- 5つのワークフローファイルで`num: 10`を`num: 3`に修正
- myAgentDesk DBの`job_version`テーブルを更新

**修正ファイル**:
```
graphAiServer/config/graphai/taskmaster/tm_01KE8WDE5X24WZBWPEYNBJD5KW/weather_forecast_search.yml
graphAiServer/config/graphai/taskmaster/tm_01KEH9NMX4QXABSWVDP6989650/workflow_jm_01KEH9NMY2WHPPSBFV9W5D2R3V.yml
graphAiServer/config/graphai/taskmaster/tm_test456/ir_jouhou_shyutoku.yml
graphAiServer/config/graphai/taskmaster/tm_test456/ir_joho_shudoku.yml
graphAiServer/config/graphai/taskmaster/tm_test456/ir_financial_data_retrieval.yml
```

### 2.2 問題2: sourceノード参照エラー

**症状**: ワークフローが`query`パラメータを取得できない

**原因**: ワークフローが`:source.query`を参照していたが、graphAiServerは`:source.user_input.query`形式を期待

**修正内容**:
- ワークフローの参照を`:source.user_input.query`に修正
- myAgentDesk DBの対応するレコードも更新

### 2.3 問題3: タスクマスターのbody_templateエラー（主要原因）

**症状**: 直接API呼び出しは成功するが、jobqueue経由では失敗

**原因**: タスクマスターの`body_template`が`"{{job.body}}"`でジョブ全体を代入していたため、二重ネストが発生

**修正前の構造**:
```json
{
  "body_template": {
    "user_input": "{{job.body}}",  // ← job.body全体を代入
    ...
  }
}
```

これにより、graphAiServerへの実際のリクエストは：
```json
{
  "user_input": {
    "user_input": {"query": "大谷翔平の妻"},
    "model_name": "..."
  }
}
```
となり、`:source.user_input.query`が`undefined`になっていた。

**修正後の構造**:
```json
{
  "body_template": {
    "user_input": "{{job.body.user_input}}",  // ← user_input部分のみを代入
    "job_params": "{{job.body.user_input}}",
    "model_name": "taskmaster/tm_01KEH9NMX4QXABSWVDP6989650/workflow_jm_01KEH9NMY2WHPPSBFV9W5D2R3V"
  }
}
```

**修正方法**:
```bash
curl -X PUT "http://localhost:8001/api/v1/task-masters/tm_01KEH9NMX4QXABSWVDP6989650" \
  -H "Content-Type: application/json" \
  -d '{
    "body_template": {
      "user_input": "{{job.body.user_input}}",
      "job_params": "{{job.body.user_input}}",
      "model_name": "taskmaster/tm_01KEH9NMX4QXABSWVDP6989650/workflow_jm_01KEH9NMY2WHPPSBFV9W5D2R3V"
    },
    "timeout_sec": 180
  }'
```

### 2.4 問題4: myAgentDeskのジョブ作成時のbody構造

**症状**: ジョブbodyに`user_input`ラッパーが欠落

**原因**: myAgentDeskの`runs/+server.ts`が`executionParams`をそのまま送信していた

**修正内容**: `executionParams`を`user_input`でラップするよう修正

**修正ファイル**: `myAgentDesk/src/routes/api/runs/+server.ts`

```typescript
// 修正後のコード
const wrappedBody = { user_input: bodyParams };

const jobResult = await jobQueueClient.createJobFromMaster(jobVersion.externalJobMasterId, {
  name: `Run ${run.id}`,
  body: wrappedBody,  // user_inputでラップ
  tags: [`run:${run.id}`, `workbench:${body.workbenchId}`]
});
```

---

## 3. 未解決の問題

### 3.1 Task 3 (メール送信) のHTTP 422エラー

**症状**: `send_email`ノードでHTTP 422エラーが発生

**エラーメッセージ**:
```json
{
  "errors": {
    "send_email": {
      "message": "HTTP error: 422",
      "stack": "Error: HTTP error: 422\n    at fetchAgent ..."
    }
  }
}
```

**関連タスクマスター**: `tm_01KEH9NMXSBJYCDR27KJ3FD7KC`

**調査必要項目**:
1. メール送信ワークフローの入力パラメータ検証
2. Gmail API のリクエストボディ形式の確認
3. タスクチェーン間のデータ受け渡し確認

---

## 4. テスト結果

### 4.1 Google検索タスク（修正後）

| 項目 | 結果 |
|------|------|
| 直接API呼び出し | ✅ 成功 |
| jobqueue経由（Task 1） | ✅ 成功 (60秒) |
| jobqueue経由（Task 2） | ✅ 成功 (4.5秒) |
| jobqueue経由（Task 3 メール送信） | ❌ 失敗 (HTTP 422) |

### 4.2 テストジョブ
- **Job ID**: `j_01KEHFNGMXXBTE7ZF4T0FPR8ST`
- **Task Master Version**: 3 (修正済み)

---

## 5. 影響範囲

### 修正されたファイル
1. `graphAiServer/config/graphai/taskmaster/*/workflow_*.yml` - 5ファイル
2. `myAgentDesk/src/routes/api/runs/+server.ts`
3. jobqueue DB: `task_masters`テーブル (`tm_01KEH9NMX4QXABSWVDP6989650`)
4. jobqueue DB: `job_masters`テーブル (`jm_01KEH9NMY2WHPPSBFV9W5D2R3V`)
5. myAgentDesk DB: `job_version`テーブル

### バージョン更新
- `tm_01KEH9NMX4QXABSWVDP6989650`: version 1 → version 3

---

## 6. 推奨アクション

### 即時対応が必要
1. [ ] メール送信タスク(`tm_01KEH9NMXSBJYCDR27KJ3FD7KC`)のHTTP 422エラーを調査・修正

### 今後の改善
1. [ ] Job Generator V2でタスクマスター生成時の`body_template`形式を確認
2. [ ] テンプレート解決のE2Eテストを追加
3. [ ] `num`パラメータのデフォルト値をスキーマ制限内に設定

---

## 7. 再現手順

### 問題の再現
```bash
# 1. ジョブ作成
curl -X POST "http://localhost:8001/api/v1/jobs/from-master/jm_01KEH9NMY2WHPPSBFV9W5D2R3V" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "body": {"user_input": {"query": "大谷翔平の妻"}}}'

# 2. ジョブ状態確認
curl "http://localhost:8001/api/v1/jobs/{job_id}"

# 3. タスク詳細確認
curl "http://localhost:8001/api/v1/jobs/{job_id}/tasks"
```

### 直接API呼び出し（動作確認用）
```bash
curl "http://localhost:8005/api/v1/myagent" -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": {"query": "大谷翔平の妻"},
    "model_name": "taskmaster/tm_01KEH9NMX4QXABSWVDP6989650/workflow_jm_01KEH9NMY2WHPPSBFV9W5D2R3V"
  }'
```
