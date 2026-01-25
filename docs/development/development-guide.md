# 開発ガイドライン

このガイドは、GitHub Actions エラーの再発防止とコード品質維持のためのベストプラクティスをまとめたものです。

## 🚀 開発環境セットアップ

### 1. Pre-commit Hooks のインストール

**必須**: すべての開発者はpre-commit hooksを設定してください。

```bash
# Pre-commit のインストール
pip install pre-commit

# Hooks の有効化
pre-commit install

# 全ファイルに対して手動実行（初回のみ推奨）
pre-commit run --all-files
```

### 2. VS Code 推奨拡張機能

`.vscode/extensions.json` に記載されている拡張機能をインストールしてください：

- **Ruff** (charliermarsh.ruff) - 必須
- **Python** (ms-python.python) - 必須
- **Pylance** (ms-python.vscode-pylance) - 推奨

## ✅ コミット前チェックリスト

コミット前に以下を確認してください：

### 自動チェック（Pre-commit Hooks）

- [ ] Ruff linting (自動修正あり)
- [ ] Ruff formatting (自動適用)
- [ ] Type checking (MyPy)
- [ ] Unit tests (高速)

### 手動チェック

- [ ] 新しいテストを追加したか？
- [ ] カバレッジは維持されているか？ (90%以上)
- [ ] コミットメッセージは規約に従っているか？

```bash
# コミット前の手動チェック
cd expertAgent
uv run ruff check .
uv run ruff format . --check
uv run mypy app/ core/
uv run pytest tests/unit/ -v
uv run pytest tests/ --cov=app --cov=core --cov-report=term
```

## 🔧 品質チェックコマンド

### Linting & Formatting

```bash
# Linting (自動修正付き)
uv run ruff check . --fix

# Formatting
uv run ruff format .

# 型チェック
uv run mypy app/ core/
```

### Testing

```bash
# ユニットテストのみ（高速）
uv run pytest tests/unit/ -v

# すべてのテスト
uv run pytest tests/ -v

# カバレッジ付き
uv run pytest tests/ --cov=app --cov=core --cov-report=term-missing

# カバレッジHTML レポート
uv run pytest tests/ --cov=app --cov=core --cov-report=html
open htmlcov/index.html
```

## 🚨 よくあるエラーと対策

### 1. Import 順序エラー (I001)

**エラー例:**
```
I001 Import block is un-sorted or un-formatted
```

**対策:**
- VS Code設定で保存時に自動整理: `"source.organizeImports": "explicit"`
- または手動実行: `uv run ruff check . --fix`

**正しいimport順序:**
```python
# 1. 標準ライブラリ
import json
from pathlib import Path

# 2. サードパーティ
import pytest
from fastapi import FastAPI

# 3. ローカルモジュール
from app.main import app
from core.config import settings
```

### 2. 未使用のimport (F401)

**エラー例:**
```
F401 `pathlib.Path` imported but unused
```

**対策:**
- Pre-commit hooksが自動削除
- VS Code設定で保存時に自動削除

### 3. 重複import (F811)

**エラー例:**
```
F811 Redefinition of unused `Path` from line 4
```

**対策:**
- トップレベルで一度だけimport
- 関数内でのimportは避ける

**悪い例:**
```python
from pathlib import Path  # トップレベル

def test_something():
    from pathlib import Path  # ❌ 重複！
```

**良い例:**
```python
from pathlib import Path  # トップレベルのみ

def test_something():
    # Pathを直接使用
    path = Path("/tmp/test")
```

### 4. Pytest Marker 未定義

**エラー例:**
```
'integration' not found in markers configuration option
```

**対策:**
- 新しいmarkerを追加したら、必ず `pyproject.toml` に登録:

```toml
[tool.pytest.ini_options]
markers = [
    "integration: marks tests as integration tests",
    "slow: marks tests as slow",  # 新しいmarker
]
```

### 5. カバレッジ不足

**エラー例:**
```
Coverage failure: total of 85.36 is less than fail-under=90.00
```

**対策:**
1. カバレッジレポートで未カバー箇所を確認:
   ```bash
   uv run pytest tests/ --cov=app --cov=core --cov-report=html
   open htmlcov/index.html
   ```

2. 欠落しているテストを追加:
   - エラーハンドリング
   - エッジケース
   - 例外パス

### 6. MyPy 型エラー (Type Checking)

#### 6.1 Pydantic Field() の構文エラー

**エラー例:**
```
No overload variant of "Field" matches argument types "str", "str"
```

**原因:** Pydantic v2では `Field()` は位置引数を受け付けません。

**悪い例 (Pydantic v1スタイル):**
```python
from pydantic import BaseModel, Field

class Settings(BaseModel):
    api_key: str = Field("", env="API_KEY")  # ❌ 位置引数
    base_url: str = Field(..., description="Base URL")  # ❌ ... を位置引数で使用
```

**良い例 (Pydantic v2スタイル):**
```python
from pydantic import BaseModel, Field

class Settings(BaseModel):
    api_key: str = Field(default="")  # ✅ キーワード引数のみ
    base_url: str = Field(description="Base URL")  # ✅ default不要なら省略
```

**pydantic_settings の場合:**
```python
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # envパラメータは不要 - フィールド名が自動的に環境変数名になる
    api_key: str = Field(default="")  # ✅ API_KEY環境変数から読み込まれる
    base_url: str = Field(default="http://localhost:8000")
```

#### 6.2 Literal 型のキャストエラー

**エラー例:**
```
Argument has incompatible type "str"; expected "Literal['JobQueue', 'MyScheduler']"
```

**対策:** 明示的に型キャストする

```python
from typing import Literal, cast

def get_service_name() -> str:
    return "JobQueue"  # 実行時は文字列を返す

# ❌ 型エラー
service: Literal["JobQueue", "MyScheduler"] = get_service_name()

# ✅ 型キャストで解決
service: Literal["JobQueue", "MyScheduler"] = cast(
    Literal["JobQueue", "MyScheduler"],
    get_service_name()
)
```

#### 6.3 Any 型からの返却エラー

**エラー例:**
```
Returning Any from function declared to return "str"
```

**対策:** 明示的に型キャストする

```python
def get_dict_value(data: dict) -> str:
    # ❌ dict[key] は Any 型を返す
    return data["key"]

    # ✅ 明示的にstr()でキャスト
    return str(data["key"])
```

#### 6.4 サードパーティライブラリの型警告

**エラー例:**
```
Skipping analyzing "google_auth_oauthlib.flow": module is installed, but missing library stubs
```

**対策:** `type: ignore` コメントで警告を抑制

```python
from google_auth_oauthlib.flow import Flow  # type: ignore[import-untyped]
```

#### 6.5 環境変数読み込みの型エラー

**CommonUI での dotenv 読み込み:**

```python
"""Configuration management for CommonUI Streamlit application."""

import os
from pathlib import Path
from typing import Literal, cast

import streamlit as st
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables from .env file
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

class Config:
    def _get_setting(self, key: str, default: str = "") -> str:
        """Get setting from Streamlit secrets or environment variables."""
        try:
            if hasattr(st, "secrets") and key in st.secrets:
                return str(st.secrets[key])  # ✅ 明示的にstr()でキャスト
        except Exception:
            pass
        return os.getenv(key, default)
```

## 📋 コミットメッセージ規約

Conventional Commits 形式に従ってください:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type

- `feat`: 新機能
- `fix`: バグ修正
- `test`: テスト追加・修正
- `refactor`: リファクタリング
- `docs`: ドキュメント
- `ci`: CI/CD設定変更
- `chore`: その他

### 例

```
feat(expertAgent): add Google OAuth2 support

- Implement OAuth2 flow with PKCE
- Add token encryption with Fernet
- Integrate with MyVault for token storage

Fixes #71

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## 🎯 GitHub Actions 対策

### Fast Fail 戦略

1. **Linting を最初に実行**: 構文エラーを早期発見
2. **Type checking を2番目**: 型エラーを早期発見
3. **Tests を最後**: 時間がかかるため

### ローカルでの事前検証

**プッシュ前に必ず実行:**

```bash
# すべての品質チェックを一度に実行
./scripts/pre-push-check.sh
```

または手動で:

```bash
cd expertAgent
uv run ruff check .
uv run ruff format . --check
uv run mypy app/ core/
uv run pytest tests/ --cov=app --cov=core
```

## 🔄 CI/CD エラー発生時の対応

1. **エラーログを確認**
   ```bash
   gh run view <run-id> --log-failed
   ```

2. **ローカルで再現**
   ```bash
   uv run ruff check .  # Linting エラーの場合
   uv run mypy app/ core/  # 型エラーの場合
   uv run pytest tests/  # Test エラーの場合
   ```

3. **修正して再プッシュ**
   ```bash
   uv run ruff check . --fix
   git add -u
   git commit -m "fix: resolve linting errors"
   git push
   ```

## 📚 参考リンク

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Pre-commit Hooks](https://pre-commit.com/)
- [Pytest Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Pydantic V2 Migration Guide](https://docs.pydantic.dev/latest/migration/)
- [MyPy Documentation](https://mypy.readthedocs.io/)
