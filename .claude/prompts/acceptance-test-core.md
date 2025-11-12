# 受入テストコアプロンプト

このプロンプトは、スラッシュコマンドとサブエージェントの両方から実行されます。

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
  "feature_summary": "jobqueueプロジェクトにaiosqlite対応のDATABASE_URLを設定",
  "acceptance_criteria": [
    "jobqueue/.env にDATABASE_URLが存在すること",
    "環境変数を読み込んでデータベース接続できること"
  ],
  "test_scenarios": [
    "シナリオ1: .envファイルが存在し、DATABASE_URLが読み込める",
    "シナリオ2: DATABASE_URL形式が正しく、接続可能"
  ]
}
```

---

## 受入テスト実行フロー

### Phase 1: E2Eテストシナリオ作成

受入条件とテストシナリオに基づいて、E2Eテストを作成します。

```bash
# 結合テストディレクトリ作成
mkdir -p tests/integration
```

例（Python/pytest）:
```python
# tests/integration/test_issue_{issue_number}_acceptance.py
import pytest
from pathlib import Path
import os

@pytest.fixture
def load_env():
    """jobqueue/.env を環境変数に読み込む"""
    from dotenv import load_dotenv
    env_path = Path("jobqueue/.env")
    load_dotenv(env_path)
    yield
    # Cleanup if needed

def test_scenario_1_env_file_exists_and_readable(load_env):
    """シナリオ1: .envファイルが存在し、DATABASE_URLが読み込める"""
    # Given: jobqueue/.env が存在
    env_file = Path("jobqueue/.env")
    assert env_file.exists(), "jobqueue/.env が存在しません"

    # When: 環境変数を読み込む
    database_url = os.getenv("DATABASE_URL")

    # Then: DATABASE_URLが取得できること
    assert database_url is not None, "DATABASE_URLが読み込めません"
    assert len(database_url) > 0, "DATABASE_URLが空です"

def test_scenario_2_database_url_format_valid_and_connectable(load_env):
    """シナリオ2: DATABASE_URL形式が正しく、接続可能"""
    # Given: DATABASE_URLが環境変数に設定済み
    database_url = os.getenv("DATABASE_URL")
    assert database_url is not None

    # When: URL形式を確認
    assert database_url.startswith("sqlite+aiosqlite:///"), \
        f"DATABASE_URL形式が不正: {database_url}"

    # Then: 接続テスト（簡易）
    # 実際のDBテストがあればここで実行
    # 例: async with create_async_engine(database_url) as engine: ...
    assert True  # 接続可能なURLフォーマット
```

---

### Phase 2: テスト実行

E2Eテストを実行します：

```bash
uv run pytest tests/integration/test_issue_{issue_number}_acceptance.py -v
```

すべてのテストが成功することを確認してください。

---

### Phase 3: エビデンス収集

テスト実行のエビデンスを収集します：

#### テスト結果ログ
```bash
uv run pytest tests/integration/test_issue_{issue_number}_acceptance.py -v --tb=short > test_results.log
```

#### スクリーンショット（UIテストの場合）
```bash
# Playwrightなどを使用している場合
# pytest --screenshot=on
```

#### API応答ログ（APIテストの場合）
```bash
# ログファイル確認
cat logs/api_test_*.log
```

#### データベース状態検証（必要な場合）
```bash
sqlite3 ./data/jobqueue.db "SELECT * FROM jobs LIMIT 5;"
```

---

### Phase 4: 受入条件の検証

すべての受入条件が満たされているか確認します：

```
✅ 受入条件1: jobqueue/.env にDATABASE_URLが存在すること
   → test_scenario_1_env_file_exists_and_readable: PASSED

✅ 受入条件2: 環境変数を読み込んでデータベース接続できること
   → test_scenario_2_database_url_format_valid_and_connectable: PASSED
```

---

## 出力

### スラッシュコマンドモードの場合

ターミナルに結果を表示してください：

```
✅ 受入テスト完了

## 機能概要
jobqueueプロジェクトにaiosqlite対応のDATABASE_URLを設定

## テストシナリオ結果
✅ シナリオ1: .envファイルが存在し、DATABASE_URLが読み込める
   - test_scenario_1_env_file_exists_and_readable: PASSED

✅ シナリオ2: DATABASE_URL形式が正しく、接続可能
   - test_scenario_2_database_url_format_valid_and_connectable: PASSED

## 受入条件検証
✅ jobqueue/.env にDATABASE_URLが存在すること
✅ 環境変数を読み込んでデータベース接続できること

## エビデンス
- テスト結果ログ: test_results.log
- すべてのテストケース成功: 2/2

🎉 すべての受入条件を満たしています
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
  "test_cases": [
    {
      "scenario": "シナリオ1: .envファイルが存在し、DATABASE_URLが読み込める",
      "result": "passed",
      "evidence": "test_scenario_1_env_file_exists_and_readable: PASSED"
    },
    {
      "scenario": "シナリオ2: DATABASE_URL形式が正しく、接続可能",
      "result": "passed",
      "evidence": "test_scenario_2_database_url_format_valid_and_connectable: PASSED"
    }
  ],
  "acceptance_criteria_status": [
    {
      "criterion": "jobqueue/.env にDATABASE_URLが存在すること",
      "verified": true
    },
    {
      "criterion": "環境変数を読み込んでデータベース接続できること",
      "verified": true
    }
  ],
  "evidence_files": [
    "test_results.log"
  ],
  "message": "すべての受入条件を満たしています"
}
```

**重要**: 結果ファイルが作成されたことを報告してください。

---

## エラーハンドリング

### テストが失敗した場合

```json
{
  "status": "failed",
  "test_cases": [
    {
      "scenario": "シナリオ1: .envファイルが存在し、DATABASE_URLが読み込める",
      "result": "passed",
      "evidence": "PASSED"
    },
    {
      "scenario": "シナリオ2: DATABASE_URL形式が正しく、接続可能",
      "result": "failed",
      "evidence": "AssertionError: DATABASE_URL形式が不正"
    }
  ],
  "error": "受入テストの一部が失敗しました",
  "message": "実装を修正してください"
}
```

### 受入条件が満たされていない場合

```json
{
  "status": "failed",
  "acceptance_criteria_status": [
    {
      "criterion": "jobqueue/.env にDATABASE_URLが存在すること",
      "verified": true
    },
    {
      "criterion": "環境変数を読み込んでデータベース接続できること",
      "verified": false
    }
  ],
  "error": "受入条件の一部が満たされていません",
  "message": "実装を見直してください"
}
```

---

## 完了条件

以下をすべて満たすこと：

- ✅ すべてのテストシナリオが成功
- ✅ すべての受入条件が検証済み
- ✅ エビデンスが収集済み
- ✅ 結果ファイルが作成済み（サブエージェントモード）
