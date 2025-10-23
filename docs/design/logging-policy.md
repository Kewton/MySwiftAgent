# ログ設定ポリシー

**最終更新日**: 2025-10-24（SQLAlchemy ログ抑制・dev-start.sh による環境変数管理を追加）
**対象プロジェクト**: expertAgent, jobqueue, myscheduler, myVault, commonUI

---

## 概要

MySwiftAgentの全Pythonプロジェクトは、統一されたログ設定方針に従います。マルチワーカー環境でも正常に動作する`logging.basicConfig(force=True)`方式を採用し、プロジェクト固有のログファイル名で管理します。

---

## 設計原則

### 1. **マルチワーカー対応**

Uvicorn の `--workers N` オプションによるマルチワーカーモードでも正常にログ出力が可能な設計とする。

**採用方式**: `logging.basicConfig(force=True)`

#### なぜ `force=True` が必要か

| 設定方法 | マルチワーカー対応 | 説明 |
|---------|---------------|------|
| `logging.config.dictConfig()` | ❌ 非対応 | 既存の設定を保持するため、ワーカープロセスで再設定されない |
| `logging.basicConfig()` | ⚠️ 部分対応 | 初回のみ設定。2回目以降はスキップされる |
| `logging.basicConfig(force=True)` | ✅ 完全対応 | **既存の設定を破棄して強制的に再設定** |

**結論**: マルチワーカー環境では `force=True` が必須。

---

### 2. **プロジェクト固有のログファイル名**

各プロジェクトは独自のログファイル名を使用し、ログの混在を防ぐ。

| プロジェクト | ログファイル名 | エラーログファイル名 |
|------------|-------------|------------------|
| expertAgent | `expertagent.log` | `expertagent_rotation.log` |
| jobqueue | `jobqueue.log` | `jobqueue_rotation.log` |
| myscheduler | `myscheduler.log` | `myscheduler_rotation.log` |
| myVault | `myvault.log` | `myvault_rotation.log` |
| commonUI | `commonui.log` | `commonui_rotation.log` |

**命名規則**: `{プロジェクト名小文字}.log`

---

### 3. **3種類のログハンドラー**

全プロジェクトで以下の3つのハンドラーを標準実装する。

#### **StreamHandler（標準出力）**

```python
stream_handler = logging.StreamHandler(sys.stdout)
```

- **用途**: コンソール出力、開発時のリアルタイム確認
- **出力先**: `stdout`
- **レベル**: ルートロガーのレベルに従う

#### **RotatingFileHandler（メインログ）**

```python
rotating_handler = logging.handlers.RotatingFileHandler(
    log_file,
    mode="a",
    maxBytes=1024 * 1024,  # 1MB
    backupCount=5,
    encoding="utf-8",
)
```

- **用途**: 全レベルのログを記録
- **ローテーション**: ファイルサイズ1MBで自動ローテーション
- **保存世代数**: 5世代（.1, .2, .3, .4, .5）
- **レベル**: ルートロガーのレベルに従う

#### **TimedRotatingFileHandler（エラーログ）**

```python
error_handler = logging.handlers.TimedRotatingFileHandler(
    error_log_file,
    when="S",
    interval=1,
    backupCount=5,
    encoding="utf-8",
)
error_handler.setLevel(logging.ERROR)
```

- **用途**: ERROR以上のログのみ記録
- **ローテーション**: 1秒ごと（テスト用）
- **保存世代数**: 5世代
- **レベル**: `ERROR` 以上

**注**: `when="S"` はテスト・開発用。本番環境では `when="D"` (日次) を推奨。

---

### 4. **特定ロガーのログレベル調整**

プロジェクトで使用するライブラリによっては、大量のDEBUGログが出力される場合があります。特定のロガーのレベルを調整することで、不要なログを抑制できます。

#### **よくあるログ抑制対象**

| ライブラリ | ロガー名 | 推奨レベル | 理由 |
|-----------|---------|----------|------|
| **SQLAlchemy** | `sqlalchemy.engine`<br/>`sqlalchemy.pool`<br/>`sqlalchemy.dialects`<br/>`sqlalchemy.orm` | `WARNING` | SQL実行の詳細ログ（rollback, fetchall, close等）が大量に出力される。**全サブロガーを設定推奨** |
| **APScheduler** | `apscheduler` | `WARNING` | スケジューラーの内部処理ログが多い |
| **httpx/aiohttp** | `httpx`, `aiohttp` | `WARNING` | HTTP通信の詳細ログが多い |
| **LangChain** | `langchain` | `INFO` | LLM呼び出しの詳細ログが多い |

#### **実装例**

```python
# logging.basicConfig() の直後に追加
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="[%(process)d-%(thread)d]-%(asctime)s-%(levelname)s-%(message)s",
    handlers=handlers,
    force=True,
)

# 特定ロガーのレベルを調整
# SQLAlchemy の全サブロガーを抑制
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.orm").setLevel(logging.WARNING)
# APScheduler のログを抑制
logging.getLogger("apscheduler").setLevel(logging.WARNING)
```

#### **プロジェクト別の設定例**

| プロジェクト | 抑制対象 | 設定場所 | 備考 |
|------------|---------|---------|------|
| **jobqueue** | SQLAlchemy (全サブロガー) | `app/main.py` | engine, pool, dialects, orm を設定 |
| **myscheduler** | APScheduler | `app/core/logging.py` | スケジューラーログ抑制 |
| **myVault** | SQLAlchemy (全サブロガー) | `app/main.py` | SQLiteアクセスログ抑制 |
| **expertAgent** | LangChain (任意) | `core/logger.py` | LLM呼び出しログの調整 |

---

### 5. **統一ログフォーマット**

全プロジェクトで以下のフォーマットを使用する。

```python
format="[%(process)d-%(thread)d]-%(asctime)s-%(levelname)s-%(message)s"
```

**出力例**:
```
[70294-8280197120]-2025-10-23 23:16:24,918-INFO-Evaluation completed: is_valid=True
```

**フィールド説明**:
- `%(process)d`: プロセスID（マルチワーカー環境での識別に重要）
- `%(thread)d`: スレッドID
- `%(asctime)s`: タイムスタンプ (YYYY-MM-DD HH:MM:SS,mmm)
- `%(levelname)s`: ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `%(message)s`: ログメッセージ

---

## 実装パターン

### パターンA: モジュールレベル初期化（expertAgent, jobqueue, myVault）

**適用プロジェクト**: モジュールレベルで`import`時にログ設定を実行するプロジェクト

```python
# app/main.py（モジュールレベル）
import logging
import logging.handlers
import os
import sys
from pathlib import Path

from app.core.config import settings

# Configure logging (multi-worker compatible)
log_dir = Path(settings.LOG_DIR)
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "projectname.log"
error_log_file = log_dir / "projectname_rotation.log"

# Create handlers
stream_handler = logging.StreamHandler(sys.stdout)
rotating_handler = logging.handlers.RotatingFileHandler(
    log_file,
    mode="a",
    maxBytes=1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
error_handler = logging.handlers.TimedRotatingFileHandler(
    error_log_file,
    when="S",
    interval=1,
    backupCount=5,
    encoding="utf-8",
)
error_handler.setLevel(logging.ERROR)

handlers: list[logging.Handler] = [stream_handler, rotating_handler, error_handler]

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="[%(process)d-%(thread)d]-%(asctime)s-%(levelname)s-%(message)s",
    handlers=handlers,
    force=True,  # Force reconfiguration for multi-worker mode
)

# 特定ロガーのレベルを調整（任意）
# 例: SQLAlchemyのDEBUGログを抑制（全サブロガー）
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.orm").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
logger.info(
    f"Logging configured: log_dir={log_dir}, log_level={settings.LOG_LEVEL}, PID={os.getpid()}"
)
```

**メリット**:
- ✅ import時に確実に実行される
- ✅ マルチワーカー環境で各プロセスが個別に設定
- ✅ シンプルで理解しやすい
- ✅ 特定ロガーのレベル調整も同じファイルで完結

---

### パターンB: 関数化（myscheduler, expertAgent/core/logger.py）

**適用プロジェクト**: `setup_logging()`関数を`lifespan`イベント内で呼び出すプロジェクト

```python
# app/core/logging.py
import logging
import logging.handlers
import os
import sys
from pathlib import Path

from .config import settings


def setup_logging() -> None:
    """ログ設定を初期化（マルチワーカー対応）"""
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "projectname.log"
    error_log_file = log_dir / "projectname_rotation.log"

    # Create handlers
    stream_handler = logging.StreamHandler(sys.stdout)
    rotating_handler = logging.handlers.RotatingFileHandler(
        log_file,
        mode="a",
        maxBytes=1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    error_handler = logging.handlers.TimedRotatingFileHandler(
        error_log_file,
        when="S",
        interval=1,
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)

    handlers: list[logging.Handler] = [stream_handler, rotating_handler, error_handler]

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="[%(process)d-%(thread)d]-%(asctime)s-%(levelname)s-%(message)s",
        handlers=handlers,
        force=True,  # Force reconfiguration for multi-worker mode
    )

    # 特定ロガーのレベルを調整（任意）
    # 例: APSchedulerのDEBUGログを抑制
    logging.getLogger("apscheduler").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured: log_dir={log_dir}, log_level={settings.log_level}, PID={os.getpid()}"
    )
```

**呼び出し例**:
```python
# app/main.py
from app.core.logging import setup_logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield
```

**メリット**:
- ✅ 関数化により再利用性が高い
- ✅ `force=True`によりマルチワーカー対応
- ✅ lifespanイベント内で初期化タイミングを制御
- ✅ 特定ロガーのレベル調整も関数内で完結

---

## 環境変数設定

### **開発環境での起動方法（推奨）**

開発環境では `quick-start.sh` または `dev-start.sh` を使用して起動します。これらのスクリプトが自動的にログディレクトリとログレベルを設定します。

```bash
# 全サービス起動（推奨）
./scripts/quick-start.sh

# または個別サービス起動
./scripts/dev-start.sh start --jobqueue-only
```

### **環境変数の優先順位**

起動スクリプトは以下の優先順位で環境変数を設定します：

| 優先度 | 設定方法 | 用途 | 例 |
|-------|---------|------|-----|
| **1. 最優先** | `dev-start.sh` の環境変数 | プロジェクト横断的な統一設定 | `LOG_DIR=$PROJECT_ROOT/logs` |
| **2. 中間** | プロジェクトの `.env` ファイル | プロジェクト固有の設定 | `LOG_LEVEL=INFO` |
| **3. 最低** | `config.py` のデフォルト値 | フォールバック値 | `LOG_LEVEL="INFO"` |

**重要**: `dev-start.sh` が LOG_DIR を自動設定するため、各プロジェクトの `.env` ファイルには LOG_DIR を**記載しません**。

### `.env` ファイル設定

各プロジェクトの `.env` ファイルには **LOG_LEVEL のみ** を設定:

```bash
# ===== ログ設定 =====
LOG_LEVEL=INFO  # 開発時はDEBUG、本番時はINFO
# LOG_DIR is automatically set by dev-start.sh to $PROJECT_ROOT/logs
```

**プロジェクト別の推奨 LOG_LEVEL**:

| プロジェクト | 推奨 LOG_LEVEL | 理由 |
|------------|--------------|------|
| **jobqueue** | `INFO` | ジョブ処理状況の可視化 |
| **myscheduler** | `INFO` | スケジュール実行状況の確認 |
| **myVault** | `INFO` | セキュリティ監査用 |
| **expertAgent** | `DEBUG` | LLMエージェントのデバッグに必要 |
| **graphAiServer** | `INFO` | ワークフロー実行状況の確認 |

### LOG_LEVEL の推奨設定（環境別）

| 環境 | LOG_LEVEL | 理由 |
|-----|----------|------|
| **開発環境** | `DEBUG` (expertAgent)<br/>`INFO` (その他) | expertAgentは詳細デバッグ情報が必要 |
| **ステージング環境** | `INFO` | 動作確認に十分な情報 |
| **本番環境** | `INFO` または `WARNING` | パフォーマンスと情報量のバランス |

### 手動起動時の環境変数設定

`dev-start.sh` を使わずに手動で起動する場合は、以下のように環境変数を明示的に設定:

```bash
# 例: jobqueue を手動起動
cd jobqueue
LOG_DIR=/Users/your-name/MySwiftAgent/logs \
LOG_LEVEL=INFO \
uv run uvicorn app.main:app --host 0.0.0.0 --port 8101 --workers 4
```

---

## ワーカー数の設定

### 推奨ワーカー数

| プロジェクト | 推奨ワーカー数 | 理由 |
|------------|-------------|------|
| **expertAgent** | 4 | LLM APIコールが多く、並列処理が効果的 |
| **jobqueue** | 4 | 非同期ジョブ実行で並列度を高める |
| **myscheduler** | 1 | APSchedulerはシングルプロセス推奨 |
| **myVault** | 1 | SQLite使用のためシングルプロセス |

### 起動コマンド例

#### **推奨: スクリプトによる起動**

```bash
# 全サービス起動（推奨）
./scripts/quick-start.sh

# 個別サービス起動
./scripts/dev-start.sh start --jobqueue-only
./scripts/dev-start.sh start --myscheduler-only
./scripts/dev-start.sh start --expertagent-only

# サービス停止
./scripts/dev-start.sh stop

# ログ確認
./scripts/dev-start.sh logs jobqueue
```

**メリット**:
- ✅ LOG_DIR が自動的に `$PROJECT_ROOT/logs` に設定される
- ✅ 各プロジェクトの LOG_LEVEL が `.env` から正しく読み込まれる
- ✅ ワーカー数が自動的に最適値に設定される
- ✅ サービス間の依存関係が自動的に解決される

#### **手動起動（非推奨）**

スクリプトを使わずに手動で起動する場合は、環境変数を明示的に設定する必要があります：

```bash
# expertAgent (4 workers)
cd expertAgent
LOG_DIR=$PROJECT_ROOT/logs LOG_LEVEL=DEBUG \
uv run uvicorn app.main:app --host 0.0.0.0 --port 8104 --workers 4

# jobqueue (4 workers)
cd jobqueue
LOG_DIR=$PROJECT_ROOT/logs LOG_LEVEL=INFO \
uv run uvicorn app.main:app --host 0.0.0.0 --port 8101 --workers 4

# myscheduler (1 worker)
cd myscheduler
LOG_DIR=$PROJECT_ROOT/logs LOG_LEVEL=INFO \
uv run uvicorn app.main:app --host 0.0.0.0 --port 8102

# myVault (1 worker)
cd myVault
LOG_DIR=$PROJECT_ROOT/logs LOG_LEVEL=INFO \
uv run uvicorn app.main:app --host 0.0.0.0 --port 8103
```

**注意**: 手動起動では LOG_DIR と LOG_LEVEL を必ず設定してください。

---

## トラブルシューティング

### 問題1: ログが出力されない

**症状**: `app.log` や `{プロジェクト名}.log` にログが出力されない

**原因**:
1. `force=True` がない
2. マルチワーカーモードで `logging.config.dictConfig()` を使用
3. `logging_setup_done` フラグによる2回目以降のスキップ

**解決策**:
```python
# ❌ 間違い
logging.config.dictConfig(config)

# ✅ 正しい
logging.basicConfig(..., force=True)
```

---

### 問題2: 複数プロジェクトのログが混在

**症状**: `app.log` に複数プロジェクトのログが混在している

**原因**: 全プロジェクトで同じログファイル名 `app.log` を使用

**解決策**: プロジェクト固有のログファイル名を使用
```python
# expertAgent
log_file = log_dir / "expertagent.log"

# jobqueue
log_file = log_dir / "jobqueue.log"
```

---

### 問題3: マルチワーカーで一部のプロセスのログが出ない

**症状**: 4ワーカーのうち1つだけログが出力されない

**原因**: `force=True` がないため、最初のワーカーのみ設定が適用される

**解決策**:
```python
logging.basicConfig(
    ...,
    force=True,  # ← これが必須
)
```

---

### 問題4: SQLAlchemyの大量のDEBUGログが出力される

**症状**: `jobqueue.log` に以下のようなログが大量に出力され、重要なログが埋もれる

```
[78449-6252326912]-2025-10-23 23:39:24,926-DEBUG-executing functools.partial(<built-in method rollback...
[78449-6184923136]-2025-10-23 23:38:01,913-DEBUG-operation functools.partial(<built-in method close...
```

**原因**: SQLAlchemy のログレベルが DEBUG になっており、SQL実行の詳細ログが出力されている

**解決策**: app/main.py に SQLAlchemy ロガーの抑制を追加
```python
# SQLAlchemyのログレベルを調整（DEBUGログを抑制）
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.orm").setLevel(logging.WARNING)
```

**注意**: 4つのサブロガーすべてを設定する必要があります。

---

### 問題5: 誤った LOG_LEVEL が使用される

**症状**: jobqueue の LOG_LEVEL を INFO に設定しているのに、DEBUG ログが出力される

**原因**: `quick-start.sh` が全プロジェクトの `.env` ファイルを順番に読み込むため、expertAgent の `LOG_LEVEL=DEBUG` が最終的に使用される

**解決策**: `dev-start.sh` を使用して起動する（推奨）
```bash
# dev-start.sh が各プロジェクトの LOG_LEVEL を個別に設定
./scripts/dev-start.sh start --jobqueue-only
```

**または**: 手動起動時に環境変数を明示的に設定
```bash
cd jobqueue
LOG_DIR=$PROJECT_ROOT/logs LOG_LEVEL=INFO \
uv run uvicorn app.main:app --host 0.0.0.0 --port 8101 --workers 4
```

---

### 問題6: ログファイルが間違った場所に出力される

**症状**:
- `jobqueue/logs/jobqueue.log` にログが出力される（期待: `$PROJECT_ROOT/logs/jobqueue.log`）
- または `jobqueue/jobqueue.log` に出力される

**原因**:
1. `.env` ファイルに誤った LOG_DIR 設定がある（例: `LOG_DIR=./logs` または `LOG_DIR=../logs`）
2. `dev-start.sh` が LOG_DIR 環境変数を設定していない

**解決策**:
1. `.env` ファイルから LOG_DIR を削除し、コメントを追加
   ```bash
   # LOG_DIR is automatically set by dev-start.sh to $PROJECT_ROOT/logs
   ```

2. `config.py` のデフォルト値を `"./"` に設定
   ```python
   LOG_DIR: str = Field(default="./")
   ```

3. `dev-start.sh` で LOG_DIR を設定（修正済み）
   ```bash
   LOG_DIR='$LOG_DIR' uv run uvicorn app.main:app ...
   ```

---

## 静的解析・テスト

### Ruff チェック

```bash
uv run ruff check {project}/app/main.py {project}/core/logger.py
```

### MyPy チェック

```python
# 型ヒントを明示
handlers: list[logging.Handler] = [stream_handler, rotating_handler, error_handler]
```

### ログ出力確認

```bash
# ログファイルが作成されているか確認
ls -lh logs/{プロジェクト名}.log

# 最新ログを確認
tail -50 logs/{プロジェクト名}.log

# リアルタイム監視
tail -f logs/{プロジェクト名}.log
```

---

## 参照

- [Python logging documentation](https://docs.python.org/3/library/logging.html)
- [Uvicorn deployment guide](https://www.uvicorn.org/deployment/)
- [expertAgent ログ修正PR](https://github.com/your-repo/pull/XXX)

---

## 変更履歴

| 日付 | 変更内容 | 担当 |
|-----|---------|------|
| 2025-10-24 | SQLAlchemy ログ抑制・dev-start.sh による環境変数管理を追加 | Claude Code |
| 2025-10-23 | 初版作成：マルチワーカー対応ログ設定を全プロジェクトに統一 | Claude Code |
