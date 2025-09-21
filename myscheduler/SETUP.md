# MyScheduler セットアップガイド

このガイドでは、uvを使用してMySchedulerの開発環境を構築する方法を説明します。

## 前提条件

- Python 3.12+
- uv（Python パッケージマネージャ）

## uvのインストール

uvがインストールされていない場合は、以下のコマンドでインストールしてください：

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.sh | iex"
```

## プロジェクトのセットアップ

1. **依存関係のインストール**

```bash
# 基本依存関係のみ
uv sync

# 開発用依存関係も含める（推奨）
uv sync --extra dev
```

2. **開発サーバーの起動**

```bash
# uvを使用して起動
uv run uvicorn app:app --reload

# または make コマンドを使用
make run
```

3. **テストの実行**

```bash
# uvを使用してテスト実行
uv run pytest test_app.py -v

# または make コマンドを使用
make test

# またはシェルスクリプトを使用
./run_tests.sh
```

## 利用可能なコマンド

### makeコマンド

```bash
make help          # ヘルプを表示
make install       # 基本依存関係をインストール
make dev           # 開発用依存関係をインストール
make test          # テストを実行
make run           # 開発サーバーを起動
make lint          # コードをlint
make format        # コードをフォーマット
make type-check    # 型チェックを実行
make check-all     # 全てのチェックを実行
make clean         # キャッシュファイルを削除
make example       # 使用例を実行
```

### uvコマンド

```bash
# 依存関係管理
uv add package-name              # パッケージを追加
uv add --dev package-name        # 開発用パッケージを追加
uv remove package-name           # パッケージを削除
uv sync                          # 依存関係を同期

# スクリプト実行
uv run python script.py          # Pythonスクリプトを実行
uv run uvicorn app:app --reload  # サーバーを起動
uv run pytest                    # テストを実行

# 環境管理
uv venv                          # 仮想環境を作成
uv pip install package           # pipコマンドの代替
```

## 開発ワークフロー

1. **新機能の開発**

```bash
# 開発用依存関係をインストール
make dev

# コードを編集
# ...

# テストとlintを実行
make check-all

# サーバーを起動して動作確認
make run
```

2. **コードの品質チェック**

```bash
# コードフォーマット
make format

# lintエラーのチェック
make lint

# 型チェック
make type-check

# テスト実行
make test
```

## Docker使用時

```bash
# Dockerイメージのビルド
make docker-build

# Dockerコンテナの実行
make docker-run
```

## API確認

サーバー起動後、以下のURLでAPIドキュメントを確認できます：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- ヘルスチェック: http://localhost:8000/

## トラブルシューティング

### uvが見つからない場合

```bash
# パスを再読み込み
source ~/.bashrc
# または
source ~/.zshrc
```

### 依存関係の問題

```bash
# ロックファイルを更新
uv lock

# 依存関係を再同期
uv sync --extra dev
```

### 古いキャッシュの問題

```bash
# キャッシュをクリア
make clean

# uvのキャッシュをクリア
uv cache clean
```

## 本番環境での実行

```bash
# 本番用の起動
uv run uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1

# または環境変数で設定
export HOST=0.0.0.0
export PORT=8000
uv run uvicorn app:app --host $HOST --port $PORT --workers 1
```

## その他のツール

### VS Code設定

`.vscode/settings.json` を作成して以下を設定：

```json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "ruff"
}
```

### pre-commitフック（任意）

```bash
# pre-commitのインストール
uv add --dev pre-commit

# フックの設定
uv run pre-commit install
```