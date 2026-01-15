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
| **pytest受入テスト** | `tests/acceptance/test_issue_{N}_acceptance.py` の実行【必須】 |
| **Playwrightテスト** | `myAgentDesk`/`commonUI` 対象時はブラウザUIテストの実行【条件付き必須】 |
| E2Eシナリオ | 実際のAPIエンドポイントを叩いて期待する応答を確認 |
| 外部サービス連携 | LLM API、Langfuse、Valkey等との連携動作確認 |

**Phase 3では必ずローカル受入テスト（L3）を実施してください。**

---

## プロジェクト別テスト方法

| プロジェクト | pytest | curl API | Playwright | 備考 |
|-------------|--------|----------|------------|------|
| **expertAgent** | ✅ 必須 | ✅ 必須 | ❌ 不要 | バックエンドAPI |
| **graphAiServer** | ✅ 必須 | ✅ 必須 | ❌ 不要 | ワークフローAPI |
| **myAgentDesk** | ✅ 必須 | ✅ 必須 | **✅ 必須** | フロントエンドUI |
| **jobqueue** | ✅ 必須 | ✅ 必須 | ❌ 不要 | ジョブキューAPI |
| **myVault** | ✅ 必須 | ✅ 必須 | ❌ 不要 | シークレット管理API |
| **myscheduler** | ✅ 必須 | ✅ 必須 | ❌ 不要 | スケジューラAPI |
| **commonUI** | ✅ 必須 | ❌ 不要 | **✅ 必須** | 共通UIコンポーネント |

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
  "labels": ["feature", "agent-layer"],
  "target_project": "myAgentDesk",
  "playwright_required": true,
  "l3_test_plan": {
    "source": "work-plan.md",
    "health_checks": [...],
    "test_commands": [...],
    "external_service_checks": [...]
  },
  "pytest_test_file": "tests/acceptance/test_issue_166_acceptance.py",
  "playwright_test_file": "myAgentDesk/tests/e2e/test_issue_166.spec.ts"
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
Please start services with: ./scripts/dev-start.sh or make dev-all
```

---

### Step 2: pytest受入テストファイル実行【必須】

**必須**: `tests/acceptance/test_issue_{issue_number}_acceptance.py` を実行します。

```bash
# pytest受入テスト実行
uv run pytest tests/acceptance/test_issue_{issue_number}_acceptance.py -v --tb=short

# 結果を保存
uv run pytest tests/acceptance/test_issue_{issue_number}_acceptance.py -v --tb=short > /tmp/acceptance_pytest_output.log 2>&1
echo "Exit code: $?"
```

**pytest結果の検証【必須】**:

| 項目 | 判定基準 |
|------|---------|
| Exit code | 0 であること |
| Failed tests | 0 であること |
| Passed tests | 1以上であること |

**pytestが失敗した場合**:
- `status: "failed"` を設定
- 失敗したテストメソッドとエラーメッセージを記録
- **Phase 3は失敗として終了**（Phase 2に戻る）

```json
{
  "status": "failed",
  "test_level": "L3",
  "pytest_results": {
    "test_file": "tests/acceptance/test_issue_166_acceptance.py",
    "total": 3,
    "passed": 1,
    "failed": 2,
    "failures": [
      {
        "method": "test_scenario_1_api_returns_expected_response",
        "error": "AssertionError: Expected 200, got 500"
      }
    ]
  },
  "error": "pytest受入テストが失敗しました"
}
```

---

### Step 3: 追加E2Eシナリオ実行（work-plan.mdのL3テスト計画）

pytestが成功した後、work-plan.mdのL3テスト計画に記載された追加のcurlコマンドを実行します。

#### コンテキストファイルから `l3_test_plan` を読み込み

```bash
# l3_test_plan.test_commands を順次実行
```

#### 各コマンドの実行と検証【必須】

**検証項目**:

| 項目 | 検証方法 |
|------|---------|
| HTTPステータスコード | `expected_status` と実際のステータスを比較 |
| レスポンスボディ | `expected_response_contains` の各文字列が含まれるか確認 |

**curlコマンドの実行例**:

```bash
# 正常系テスト
RESPONSE=$(curl -s -X POST http://localhost:8104/v1/endpoint \
  -H "Content-Type: application/json" \
  -d '{"param": "value"}' \
  -w '\nHTTP_STATUS:%{http_code}')

# HTTPステータスを抽出
HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)

# レスポンスボディを抽出
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')

# 検証
if [ "$HTTP_STATUS" != "200" ]; then
  echo "❌ FAILED: Expected 200, got $HTTP_STATUS"
  echo "Response: $BODY"
  exit 1
fi

# レスポンスに期待するフィールドが含まれるか確認
if ! echo "$BODY" | grep -q "result"; then
  echo "❌ FAILED: Response missing 'result' field"
  exit 1
fi

echo "✅ PASSED: HTTP 200, response contains 'result'"
```

**異常系テスト**:

```bash
# 404テスト
RESPONSE=$(curl -s -X GET http://localhost:8104/v1/resource/nonexistent \
  -w '\nHTTP_STATUS:%{http_code}')

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')

if [ "$HTTP_STATUS" != "404" ]; then
  echo "❌ FAILED: Expected 404, got $HTTP_STATUS"
  exit 1
fi

echo "✅ PASSED: HTTP 404 for nonexistent resource"
```

---

### Step 4: Playwrightテスト実行（myAgentDesk/commonUI対象時）【条件付き必須】

**対象プロジェクト**: `myAgentDesk`, `commonUI`

プロジェクトラベルが上記の場合、Playwrightによるブラウザテストを実行します。

#### プロジェクト判定

```bash
# Issueのラベルからプロジェクトを判定
PROJECT_LABEL=$(gh issue view {issue_number} --json labels --jq '.labels[] | select(.name | startswith("project:")) | .name')

echo "Target project: $PROJECT_LABEL"

# または、コンテキストファイルから判定（サブエージェントモード）
PLAYWRIGHT_REQUIRED=$(cat "$CONTEXT_FILE" | jq -r '.playwright_required // false')
```

#### Playwrightテスト実行

```bash
if [[ "$PROJECT_LABEL" == *"myAgentDesk"* ]] || [[ "$PROJECT_LABEL" == *"commonUI"* ]] || [[ "$PLAYWRIGHT_REQUIRED" == "true" ]]; then
  echo "🎭 Playwright test required"

  # myAgentDesk の場合
  cd myAgentDesk

  # 開発サーバー起動確認
  curl -sf http://localhost:5173 && echo "✅ Dev server: running" || echo "❌ Dev server: not running"

  # Playwrightテスト実行
  npm test -- --run tests/e2e/test_issue_{issue_number}.spec.ts

  # または全E2Eテスト実行
  npm test -- --run

  # 結果を保存
  npm test -- --run > /tmp/playwright_output.log 2>&1
  PLAYWRIGHT_EXIT_CODE=$?

  echo "Playwright exit code: $PLAYWRIGHT_EXIT_CODE"
  cat /tmp/playwright_output.log

  cd ..
else
  echo "⏭️ Playwright test skipped for: $PROJECT_LABEL"
fi
```

**Playwright結果の検証【条件付き必須】**:

| 項目 | 判定基準 |
|------|---------|
| Exit code | 0 であること |
| Failed tests | 0 であること |
| Passed tests | 1以上であること |

**Playwrightが失敗した場合**:
- `status: "failed"` を設定
- 失敗したテストとエラーメッセージを記録
- **Phase 3は失敗として終了**（Phase 2に戻る）

```json
{
  "status": "failed",
  "test_level": "L3",
  "target_project": "myAgentDesk",
  "pytest_results": {
    "total": 3,
    "passed": 3,
    "failed": 0
  },
  "playwright_results": {
    "required": true,
    "test_file": "myAgentDesk/tests/e2e/test_issue_166.spec.ts",
    "total": 5,
    "passed": 3,
    "failed": 2,
    "failures": [
      {
        "test": "test_ui_displays_result_correctly",
        "error": "Expected element to be visible, but it was not found"
      }
    ]
  },
  "error": "Playwrightテストが失敗しました（2/5テスト失敗）"
}
```

---

### Step 5: E2E統合テスト（Issue #359追加）

**Job Generation機能を含むIssueの場合、以下のE2Eテストを実行します**：

#### Job Generate API直接実行テスト

```bash
# Job Generate APIテストの実行（pytest）
cd expertAgent
uv run pytest tests/acceptance/test_job_generate_api.py -v -s

# または個別テスト
uv run pytest tests/acceptance/test_job_generate_api.py::test_job_generation_e2e -v -s
```

**検証項目**：
| 項目 | 検証内容 |
|------|---------|
| Job生成開始 | `POST /v1/job-generator` が成功し、job_idが返却される |
| ステータスポーリング | `GET /v1/jobs/{job_id}/status` が適切なフェーズを返す |
| タスク分析完了 | `task_breakdown` が生成される |
| ワークフロー生成 | `workflow_statuses` にワークフローが含まれる |
| 最終ステータス | `status: "success"` または意味のあるエラーメッセージ |

**E2Eテストの必須条件**：
- ❌ モックを使用したテストは不可
- ✅ 実際のLLM APIを呼び出すこと
- ✅ 実際のワークフロー生成を実行すること
- ✅ 生成されたTaskFlow JSONの妥当性を検証すること

### Step 6: 外部サービス連携確認（該当する場合）

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

### Step 7: エビデンス収集

テスト実行のエビデンスを収集します：

#### pytest出力ログ

```bash
# pytestの出力は既に /tmp/acceptance_pytest_output.log に保存済み
cat /tmp/acceptance_pytest_output.log
```

#### Playwright出力ログ（該当する場合）

```bash
# Playwrightの出力は既に /tmp/playwright_output.log に保存済み
cat /tmp/playwright_output.log
```

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

## pytest受入テスト結果【必須】
📂 テストファイル: tests/acceptance/test_issue_{issue_number}_acceptance.py
✅ Total: 3 tests
✅ Passed: 3
❌ Failed: 0
⏭️ Skipped: 0

## Playwrightテスト結果【条件付き必須】（myAgentDesk/commonUI対象時）
📂 テストファイル: myAgentDesk/tests/e2e/test_issue_{issue_number}.spec.ts
✅ Total: 5 tests
✅ Passed: 5
❌ Failed: 0
⏭️ Skipped: 0

## E2Eシナリオ結果（work-plan.mdのL3テスト計画）
✅ 正常系テスト
   - コマンド: curl -s -X POST http://localhost:8104/v1/endpoint ...
   - 期待ステータス: 200 → 実際: 200 ✅
   - 期待フィールド: ["result"] → 含まれている ✅

✅ 異常系テスト
   - コマンド: curl -s -X GET http://localhost:8104/v1/resource/nonexistent
   - 期待ステータス: 404 → 実際: 404 ✅
   - 期待フィールド: ["detail"] → 含まれている ✅

## 受入条件検証
✅ 受入条件1: APIエンドポイントが実装されている (pytest: test_scenario_1)
✅ 受入条件2: エラーハンドリングが適切 (pytest: test_scenario_2)

## エビデンス
- pytestログ: /tmp/acceptance_pytest_output.log
- Playwrightログ: /tmp/playwright_output.log（該当時）
- APIレスポンス: /tmp/acceptance_test_response.json
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

#### Playwright必須プロジェクトの場合（myAgentDesk/commonUI）

```json
{
  "status": "passed",
  "test_level": "L3",
  "test_type": "local_acceptance_test",
  "target_project": "myAgentDesk",
  "service_health": {
    "expertAgent": {"status": "healthy", "url": "http://localhost:8104"},
    "myVault": {"status": "healthy", "url": "http://localhost:8103"},
    "myAgentDesk": {"status": "healthy", "url": "http://localhost:5173"}
  },
  "pytest_results": {
    "test_file": "tests/acceptance/test_issue_166_acceptance.py",
    "total": 3,
    "passed": 3,
    "failed": 0,
    "skipped": 0,
    "output": "... pytest output ..."
  },
  "playwright_results": {
    "required": true,
    "test_file": "myAgentDesk/tests/e2e/test_issue_166.spec.ts",
    "total": 5,
    "passed": 5,
    "failed": 0,
    "skipped": 0,
    "output": "... playwright output ..."
  },
  "l3_test_plan_results": {
    "source": "work-plan.md",
    "test_commands": [
      {
        "name": "正常系テスト",
        "command": "curl -s -X POST http://localhost:8104/v1/endpoint ...",
        "expected_status": 200,
        "actual_status": 200,
        "expected_response_contains": ["result"],
        "response_validation": "passed",
        "result": "passed"
      }
    ]
  },
  "acceptance_criteria_status": [
    {
      "criterion": "受入条件1",
      "verified": true,
      "verification_method": "pytest",
      "test_method": "test_scenario_1_api_returns_expected_response"
    },
    {
      "criterion": "受入条件2（UI）",
      "verified": true,
      "verification_method": "playwright",
      "test_method": "test_ui_displays_result_correctly"
    }
  ],
  "evidence_files": [
    "tests/acceptance/test_issue_166_acceptance.py",
    "myAgentDesk/tests/e2e/test_issue_166.spec.ts",
    "/tmp/acceptance_pytest_output.log",
    "/tmp/playwright_output.log",
    "/tmp/acceptance_test_response.json"
  ],
  "message": "すべての受入条件を満たしています（L3ローカル受入テスト完了）"
}
```

#### Playwright不要プロジェクトの場合（expertAgent等）

```json
{
  "status": "passed",
  "test_level": "L3",
  "test_type": "local_acceptance_test",
  "target_project": "expertAgent",
  "service_health": {
    "expertAgent": {"status": "healthy", "url": "http://localhost:8104"},
    "myVault": {"status": "healthy", "url": "http://localhost:8103"}
  },
  "pytest_results": {
    "test_file": "tests/acceptance/test_issue_166_acceptance.py",
    "total": 3,
    "passed": 3,
    "failed": 0,
    "skipped": 0,
    "output": "... pytest output ..."
  },
  "playwright_results": {
    "required": false,
    "reason": "Project 'expertAgent' does not require Playwright testing"
  },
  "l3_test_plan_results": {
    "source": "work-plan.md",
    "test_commands": [
      {
        "name": "正常系テスト",
        "expected_status": 200,
        "actual_status": 200,
        "result": "passed"
      },
      {
        "name": "異常系テスト",
        "expected_status": 404,
        "actual_status": 404,
        "result": "passed"
      }
    ]
  },
  "acceptance_criteria_status": [
    {
      "criterion": "受入条件1",
      "verified": true,
      "verification_method": "pytest",
      "test_method": "test_scenario_1_api_returns_expected_response"
    },
    {
      "criterion": "受入条件2",
      "verified": true,
      "verification_method": "pytest",
      "test_method": "test_scenario_2_error_handling_returns_404"
    }
  ],
  "evidence_files": [
    "tests/acceptance/test_issue_166_acceptance.py",
    "/tmp/acceptance_pytest_output.log",
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
  "message": "サービスを起動してください: ./scripts/dev-start.sh or make dev-all"
}
```

### pytestが失敗した場合【最優先で報告】

```json
{
  "status": "failed",
  "test_level": "L3",
  "pytest_results": {
    "test_file": "tests/acceptance/test_issue_166_acceptance.py",
    "total": 3,
    "passed": 1,
    "failed": 2,
    "skipped": 0,
    "failures": [
      {
        "method": "test_scenario_1_api_returns_expected_response",
        "error": "AssertionError: Expected 200, got 500: Internal Server Error",
        "traceback": "..."
      },
      {
        "method": "test_scenario_2_error_handling_returns_404",
        "error": "AssertionError: Expected 404, got 500"
      }
    ]
  },
  "error": "pytest受入テストが失敗しました（2/3テスト失敗）",
  "suggested_fixes": [
    "エンドポイント /v1/endpoint の実装を確認してください",
    "エラーハンドリングのステータスコードを確認してください"
  ],
  "message": "pytest受入テストを修正してください"
}
```

### L3テスト計画のコマンドが失敗した場合

```json
{
  "status": "failed",
  "test_level": "L3",
  "pytest_results": {
    "total": 3,
    "passed": 3,
    "failed": 0
  },
  "l3_test_plan_results": {
    "test_commands": [
      {
        "name": "正常系テスト",
        "expected_status": 200,
        "actual_status": 500,
        "result": "failed",
        "error": "Expected HTTP 200, got 500"
      }
    ]
  },
  "error": "L3テスト計画のコマンドが失敗しました",
  "message": "work-plan.mdのL3テスト計画に記載されたAPIテストを確認してください"
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
- ✅ **pytest受入テスト全パス**（`tests/acceptance/test_issue_{N}_acceptance.py`）【必須】
- ✅ **Playwrightテスト全パス**（myAgentDesk/commonUI対象時）【条件付き必須】
- ✅ L3テスト計画のコマンドが全て成功（HTTPステータス・レスポンス検証）
- ✅ すべての受入条件が検証済み
- ✅ エビデンスが収集済み（pytestログ、Playwrightログ、レスポンス、サービスログ）
- ✅ 結果ファイルが作成済み（サブエージェントモード）

**重要**:
- 静的解析（Ruff/MyPy）や単体テストカバレッジの確認は Phase 2 (TDD) で完了しているため、Phase 3 では実施不要です。
- Phase 3 では **pytest受入テストの実行と、実際のサービスを動かしての動作確認** に集中してください。
- **pytest受入テストが失敗した場合、Phase 3は失敗として扱います。**
- **Playwrightテストが失敗した場合（myAgentDesk/commonUI対象時）、Phase 3は失敗として扱います。**
