# TDD実装コアプロンプト

このプロンプトは、スラッシュコマンドとサブエージェントの両方から実行されます。

---

## 入力情報の取得

### スラッシュコマンドモードの場合

ユーザーから対話的に以下の情報を取得してください：

```bash
# Issue番号を取得
gh issue view {issue_number} --json number,title,body
```

- Issue番号
- 受入条件（Acceptance Criteria）
- 実装タスク（Implementation Tasks）
- 目標カバレッジ（デフォルト: 90%）

### サブエージェントモードの場合

コンテキストファイルから情報を取得してください：

```bash
# 最新のコンテキストファイルを探す
CONTEXT_FILE=$(find dev-reports/*/issue/*/pm-auto-dev/iteration-*/tdd-context.json 2>/dev/null | sort -V | tail -1)

if [ -z "$CONTEXT_FILE" ]; then
    echo "❌ Error: tdd-context.json not found"
    exit 1
fi

echo "📂 Context file: $CONTEXT_FILE"
cat "$CONTEXT_FILE"
```

コンテキストファイル構造:
```json
{
  "issue_number": 166,
  "acceptance_criteria": [
    "jobqueue/.env にDATABASE_URLが設定されていること",
    "形式は sqlite+aiosqlite:///./data/jobqueue.db であること"
  ],
  "implementation_tasks": [
    "jobqueue/.env ファイル作成",
    "DATABASE_URL環境変数設定"
  ],
  "target_coverage": 90
}
```

---

## TDD実装フロー

### Phase 1: Red - 失敗するテストを作成

受入条件に基づいてテストケースを設計します。

```bash
# テストファイル作成
mkdir -p tests/unit
```

例（Python/pytest）:
```python
# tests/unit/test_issue_{issue_number}_*.py
import pytest
from pathlib import Path

def test_database_url_exists():
    """jobqueue/.env にDATABASE_URLが存在すること"""
    env_file = Path("jobqueue/.env")
    assert env_file.exists(), "jobqueue/.env が存在しません"

    content = env_file.read_text()
    assert "DATABASE_URL" in content, "DATABASE_URL が設定されていません"

def test_database_url_format():
    """DATABASE_URLの形式が sqlite+aiosqlite:/// であること"""
    env_file = Path("jobqueue/.env")
    content = env_file.read_text()

    # DATABASE_URL行を抽出
    for line in content.splitlines():
        if line.startswith("DATABASE_URL="):
            url = line.split("=", 1)[1]
            assert url.startswith("sqlite+aiosqlite:///"), \
                f"DATABASE_URLの形式が不正です: {url}"
            break
    else:
        pytest.fail("DATABASE_URL が見つかりません")
```

**テストを実行して失敗を確認**:
```bash
uv run pytest tests/unit/test_issue_{issue_number}_*.py -v
```

---

### Phase 2: Green - 最小限の実装

テストを通すための最小限のコードを実装します。

```bash
# jobqueue/.env ファイル作成
cat > jobqueue/.env <<'EOF'
DATABASE_URL=sqlite+aiosqlite:///./data/jobqueue.db
EOF
```

**テストを実行して成功を確認**:
```bash
uv run pytest tests/unit/test_issue_{issue_number}_*.py -v
```

すべてのテストが通ることを確認してください。

---

### Phase 3: Refactor - コード整理

実装を改善します：

- 重複コードの削除
- 命名の改善
- コメントの追加
- 設計パターンの適用

**リファクタリング後もテストが通ることを確認**:
```bash
uv run pytest tests/unit/test_issue_{issue_number}_*.py -v
```

---

### Phase 4: Coverage Check

カバレッジを測定します：

```bash
uv run pytest tests/unit/test_issue_{issue_number}_*.py \
  --cov=app \
  --cov=jobqueue \
  --cov-report=json \
  --cov-report=term-missing
```

目標カバレッジ（デフォルト90%）を達成しているか確認してください。

達成していない場合は、追加のテストケースを作成してください。

---

### Phase 5: Static Analysis

静的解析を実行してコード品質を確認します：

```bash
# Ruff (Linter)
uv run ruff check .

# Ruff (Formatter)
uv run ruff format --check .

# MyPy (Type Checker)
uv run mypy app/
```

エラーが出た場合は修正してください。

---

### Phase 6: Commit

実装をコミットします：

```bash
git add .
git commit -m "$(cat <<'EOF'
fix(jobqueue): set aiosqlite DATABASE_URL in .env

Add DATABASE_URL=sqlite+aiosqlite:///./data/jobqueue.db to jobqueue/.env
to support async SQLite operations.

- Add tests for DATABASE_URL existence and format validation
- Coverage: 92.5%
- All static analysis checks passed

Resolves #166

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 出力

### スラッシュコマンドモードの場合

ターミナルに結果を表示してください：

```
✅ TDD実装完了

## 実装内容
- jobqueue/.env ファイル作成
- DATABASE_URL環境変数設定

## テスト結果
- Total: 2 tests
- Passed: 2
- Failed: 0
- Coverage: 92.5%

## 静的解析
- Ruff: 0 errors
- MyPy: 0 errors

## Commits
- abc1234: fix(jobqueue): set aiosqlite DATABASE_URL in .env
```

### サブエージェントモードの場合

結果ファイルをJSON形式で作成してください：

```bash
# 結果ファイルパスを決定
RESULT_FILE=$(dirname "$CONTEXT_FILE")/tdd-result.json
```

Writeツールで以下の内容を作成:

```json
{
  "status": "success",
  "coverage": 92.5,
  "unit_tests": {
    "total": 2,
    "passed": 2,
    "failed": 0
  },
  "static_analysis": {
    "ruff_errors": 0,
    "mypy_errors": 0
  },
  "files_changed": [
    "jobqueue/.env",
    "tests/unit/test_issue_166_database_url.py"
  ],
  "commits": [
    "abc1234: fix(jobqueue): set aiosqlite DATABASE_URL in .env"
  ],
  "message": "TDD実装完了。カバレッジ92.5%達成。"
}
```

**重要**: 結果ファイルが作成されたことを報告してください。

---

## エラーハンドリング

### テストが失敗した場合

```json
{
  "status": "failed",
  "error": "テストが失敗しました",
  "failed_tests": [
    "test_database_url_format: AssertionError: DATABASE_URLの形式が不正です"
  ],
  "message": "実装を修正してください"
}
```

### カバレッジ不足の場合

```json
{
  "status": "failed",
  "coverage": 75.0,
  "error": "目標カバレッジ90%に達していません（現在: 75.0%）",
  "message": "追加のテストケースが必要です"
}
```

### 静的解析エラーの場合

```json
{
  "status": "failed",
  "static_analysis": {
    "ruff_errors": 3,
    "mypy_errors": 1
  },
  "error": "静的解析エラーがあります",
  "message": "コードを修正してください"
}
```

---

## 完了条件

以下をすべて満たすこと：

- ✅ すべてのテストが成功
- ✅ カバレッジが目標値以上
- ✅ 静的解析エラーがゼロ
- ✅ コミットが完了（スラッシュコマンドモード）
- ✅ 結果ファイルが作成済み（サブエージェントモード）
