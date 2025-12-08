# 受入テストコアプロンプト

このプロンプトは、スラッシュコマンドとサブエージェントの両方から実行されます。

---

## テストレベルの分類

受入テストは以下の2つのレベルに分類されます：

### CI検証（GitHub Actions実行可能）- Phase 2 (TDD) で実施済み

| 項目 | 内容 |
|------|------|
| L1 単体テスト | モック使用、外部依存なし |
| L2 結合テスト | Docker Compose、テスト用DB |
| 静的解析 | Ruff/MyPy エラーゼロ |

**これらはPhase 2 (TDD) で完了しているため、Phase 3では実施不要です。**

### ローカル受入テスト（APIキー必要）- Phase 3 で実施【必須】

| 項目 | 内容 |
|------|------|
| サービス起動確認 | 実際のサービスが起動し、ヘルスチェックが通ること |
| E2Eシナリオ | 実際のAPIエンドポイントを叩いて期待する応答を確認 |
| 外部サービス連携 | LLM API、Langfuse、Valkey等との連携動作確認 |

**Phase 3では必ずローカル受入テスト（L3）を実施してください。**

---

## スキップ条件

以下のラベルが付与されているIssueの場合のみ、L3テストをスキップできます：

| ラベル | 説明 | 例 |
|--------|------|-----|
| `docs-only` | ドキュメントのみの変更 | README更新、仕様書修正 |
| `internal` | 内部リファクタリング | コード整理、変数名変更 |
| `test-only` | テストコードのみの変更 | テスト追加、テスト修正 |
| `ci-only` | CI/CD設定のみの変更 | ワークフロー修正 |

**上記以外のIssueでは、L3テストは必須です。**

---

## 入力情報の取得

### スラッシュコマンドモードの場合

ユーザーから対話的に以下の情報を取得してください：

```bash
# Issue情報を取得
gh issue view {issue_number} --json number,title,body,labels
```

- Issue番号
- 機能概要（Feature Summary）
- 受入条件（Acceptance Criteria）
- テストシナリオ（Test Scenarios）
- ラベル（スキップ条件の判定に使用）

### サブエージェントモードの場合

コンテキストファイルから情報を取得してください：

```bash
# 最新のコンテキストファイルを探す
CONTEXT_FILE=$(find dev-reports/*/issue/*/pm-auto-dev/iteration-*/acceptance-context.json 2>/dev/null | sort -V | tail -1)

if [ -z "$CONTEXT_FILE" ]; then
    echo "❌ Error: acceptance-context.json not found"
    exit 1
fi

echo "📂 Context file: $CONTEXT_FILE"
cat "$CONTEXT_FILE"
```

コンテキストファイル構造:
```json
{
  "issue_number": 166,
  "feature_summary": "機能の概要",
  "acceptance_criteria": [
    "受入条件1",
    "受入条件2"
  ],
  "test_scenarios": [
    "シナリオ1: ...",
    "シナリオ2: ..."
  ],
  "labels": ["feature", "agent-layer"]
}
```

---

## 受入テスト実行フロー

### Step 0: スキップ条件の確認

```bash
# Issueのラベルを確認
gh issue view {issue_number} --json labels --jq '.labels[].name'
```

以下のラベルが含まれている場合、L3テストをスキップ：
- `docs-only`
- `internal`
- `test-only`
- `ci-only`

**スキップする場合の出力**:
```json
{
  "status": "skipped",
  "reason": "Issue has 'docs-only' label - L3 acceptance test not required",
  "label_found": "docs-only"
}
```

---

### Step 1: サービス起動確認

**必須**: 実際のサービスが起動していることを確認します。

```bash
# サービス起動（未起動の場合）
./scripts/dev-start.sh
# または
make dev-all
```

**ヘルスチェック実行**:

```bash
# expertAgent
curl -sf http://localhost:8104/health && echo "✅ expertAgent: healthy" || echo "❌ expertAgent: not running"

# myVault
curl -sf http://localhost:8103/health && echo "✅ myVault: healthy" || echo "❌ myVault: not running"

# jobqueue
curl -sf http://localhost:8101/health && echo "✅ jobqueue: healthy" || echo "❌ jobqueue: not running"

# graphAiServer
curl -sf http://localhost:8105/health && echo "✅ graphAiServer: healthy" || echo "❌ graphAiServer: not running"
```

**サービスが起動していない場合**:
```
❌ Error: Required services are not running.
Please start services with: ./scripts/dev-start.sh
```

---

### Step 2: E2Eシナリオ実行

受入条件とテストシナリオに基づいて、**実際のAPIを叩いて**動作を確認します。

#### 例1: APIエンドポイントのテスト

```bash
# 正常系テスト
curl -s -X POST http://localhost:8104/v1/endpoint \
  -H "Content-Type: application/json" \
  -d '{"param": "value"}' | jq .

# 期待する応答を確認
# - ステータスコード: 200
# - レスポンスに期待するフィールドが含まれる
```

#### 例2: エラーハンドリングのテスト

```bash
# 異常系テスト（存在しないリソース）
curl -s -X GET http://localhost:8104/v1/resource/nonexistent-id \
  -w "\nHTTP Status: %{http_code}\n"

# 期待する応答を確認
# - ステータスコード: 404
# - エラーメッセージが適切
```

#### 例3: 外部サービス連携のテスト

```bash
# LLM API連携（実際のAPIキーが必要）
curl -s -X POST http://localhost:8104/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, world!"}' | jq .

# Langfuse連携確認
curl -s http://localhost:3001/api/public/health

# Valkey連携確認
docker exec myswiftagent-valkey redis-cli PING
```

---

### Step 3: Pythonテストファイルの実行（オプション）

`tests/acceptance/` にテストファイルが存在する場合は実行します：

```bash
# 受入テスト実行
uv run pytest tests/acceptance/test_issue_{issue_number}_acceptance.py -v
```

**受入テストファイルの例**:

```python
# tests/acceptance/test_issue_{issue_number}_acceptance.py
import pytest
import requests

@pytest.mark.acceptance
class TestIssueXXXAcceptance:
    """
    ローカル受入テスト（APIキー必要）

    前提条件:
    - サービスが起動していること (./scripts/dev-start.sh)
    - .env に必要なAPIキーが設定されていること
    """

    BASE_URL = "http://localhost:8104"

    @pytest.fixture(autouse=True)
    def check_service_running(self):
        """サービス起動確認"""
        try:
            response = requests.get(f"{self.BASE_URL}/health", timeout=5)
            assert response.status_code == 200, "サービスが起動していません"
        except requests.exceptions.ConnectionError:
            pytest.skip("サービスが起動していません。./scripts/dev-start.sh を実行してください")

    def test_scenario_1_api_returns_expected_response(self):
        """シナリオ1: APIが期待する応答を返す"""
        response = requests.post(
            f"{self.BASE_URL}/v1/endpoint",
            json={"param": "value"},
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert "expected_field" in data

    def test_scenario_2_error_handling(self):
        """シナリオ2: エラーハンドリングが適切"""
        response = requests.get(
            f"{self.BASE_URL}/v1/resource/nonexistent",
            timeout=10
        )
        assert response.status_code == 404
        assert "error" in response.json() or "detail" in response.json()

    def test_scenario_3_external_service_integration(self):
        """シナリオ3: 外部サービス連携が正常動作"""
        # LLM API連携のテスト（実際のAPIキーが必要）
        response = requests.post(
            f"{self.BASE_URL}/v1/generate",
            json={"prompt": "Test prompt"},
            timeout=60
        )
        assert response.status_code == 200
        assert len(response.json().get("content", "")) > 0
```

---

### Step 4: エビデンス収集

テスト実行のエビデンスを収集します：

#### APIレスポンスログ

```bash
# レスポンスをファイルに保存
curl -s -X POST http://localhost:8104/v1/endpoint \
  -H "Content-Type: application/json" \
  -d '{"param": "value"}' > /tmp/acceptance_test_response.json

cat /tmp/acceptance_test_response.json | jq .
```

#### サービスログの確認

```bash
# expertAgentのログ確認
tail -50 expertAgent/logs/expertagent.log | grep -E "(ERROR|WARNING|INFO)"
```

#### Langfuseトレースの確認（該当する場合）

```bash
# Langfuse UIでトレースを確認
echo "Langfuse UI: http://localhost:3001"
```

---

## 出力

### スラッシュコマンドモードの場合

ターミナルに結果を表示してください：

```
✅ 受入テスト完了（L3: ローカル受入テスト）

## 機能概要
{feature_summary}

## サービス起動確認
✅ expertAgent: healthy (http://localhost:8104)
✅ myVault: healthy (http://localhost:8103)

## E2Eシナリオ結果
✅ シナリオ1: APIが期待する応答を返す
   - コマンド: curl -s -X POST http://localhost:8104/v1/endpoint ...
   - ステータス: 200 OK
   - レスポンス: {"result": "success", ...}

✅ シナリオ2: エラーハンドリングが適切
   - コマンド: curl -s -X GET http://localhost:8104/v1/resource/nonexistent
   - ステータス: 404 Not Found
   - レスポンス: {"detail": "Resource not found"}

## 受入条件検証
✅ 受入条件1: APIエンドポイントが実装されている
✅ 受入条件2: エラーハンドリングが適切

## エビデンス
- APIレスポンスログ: /tmp/acceptance_test_response.json
- サービスログ確認済み

🎉 すべての受入条件を満たしています（L3テスト完了）
```

### サブエージェントモードの場合

結果ファイルをJSON形式で作成してください：

```bash
# 結果ファイルパスを決定
RESULT_FILE=$(dirname "$CONTEXT_FILE")/acceptance-result.json
```

Writeツールで以下の内容を作成:

```json
{
  "status": "passed",
  "test_level": "L3",
  "test_type": "local_acceptance_test",
  "service_health": {
    "expertAgent": {"status": "healthy", "url": "http://localhost:8104"},
    "myVault": {"status": "healthy", "url": "http://localhost:8103"}
  },
  "test_cases": [
    {
      "scenario": "シナリオ1: APIが期待する応答を返す",
      "type": "practical_api_test",
      "command": "curl -s -X POST http://localhost:8104/v1/endpoint -H 'Content-Type: application/json' -d '{\"param\": \"value\"}'",
      "result": "passed",
      "http_status": 200,
      "evidence": "Response: {\"result\": \"success\", ...}"
    },
    {
      "scenario": "シナリオ2: エラーハンドリングが適切",
      "type": "practical_api_test",
      "command": "curl -s -X GET http://localhost:8104/v1/resource/nonexistent",
      "result": "passed",
      "http_status": 404,
      "evidence": "Response: {\"detail\": \"Resource not found\"}"
    }
  ],
  "acceptance_criteria_status": [
    {
      "criterion": "受入条件1",
      "verified": true,
      "verification_method": "practical_api_test"
    },
    {
      "criterion": "受入条件2",
      "verified": true,
      "verification_method": "practical_api_test"
    }
  ],
  "evidence_files": [
    "/tmp/acceptance_test_response.json"
  ],
  "message": "すべての受入条件を満たしています（L3ローカル受入テスト完了）"
}
```

---

## エラーハンドリング

### サービスが起動していない場合

```json
{
  "status": "failed",
  "test_level": "L3",
  "error": "Required services are not running",
  "service_health": {
    "expertAgent": {"status": "not_running", "url": "http://localhost:8104"},
    "myVault": {"status": "healthy", "url": "http://localhost:8103"}
  },
  "message": "サービスを起動してください: ./scripts/dev-start.sh"
}
```

### テストが失敗した場合

```json
{
  "status": "failed",
  "test_level": "L3",
  "test_cases": [
    {
      "scenario": "シナリオ1: APIが期待する応答を返す",
      "type": "practical_api_test",
      "result": "passed"
    },
    {
      "scenario": "シナリオ2: エラーハンドリングが適切",
      "type": "practical_api_test",
      "result": "failed",
      "http_status": 500,
      "evidence": "Expected 404, got 500: Internal Server Error"
    }
  ],
  "error": "受入テストの一部が失敗しました",
  "message": "実装を修正してください"
}
```

### スキップした場合

```json
{
  "status": "skipped",
  "test_level": "L3",
  "reason": "Issue has 'docs-only' label - L3 acceptance test not required",
  "label_found": "docs-only",
  "message": "ドキュメントのみの変更のため、L3テストをスキップしました"
}
```

---

## 完了条件

以下をすべて満たすこと：

- ✅ サービス起動確認（ヘルスチェック通過）
- ✅ すべてのE2Eシナリオが成功（実際のAPIを叩いて確認）
- ✅ すべての受入条件が検証済み
- ✅ エビデンスが収集済み（レスポンス、ログ）
- ✅ 結果ファイルが作成済み（サブエージェントモード）

**重要**: 静的解析（Ruff/MyPy）や単体テストカバレッジの確認は Phase 2 (TDD) で完了しているため、Phase 3 では実施不要です。Phase 3 では **実際のサービスを動かしての動作確認** に集中してください。
