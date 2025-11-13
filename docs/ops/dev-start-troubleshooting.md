# dev-start.sh トラブルシューティング

worktree環境での開発サービス起動時の問題と解決策を記録します。

## Issue #166: SQLAlchemy非同期ドライバーエラー

**ステータス**: ✅ 解決済み (2025-11-13)
**影響範囲**: jobqueue、myscheduler、CommonUI、myAgentDesk
**重要度**: 🔴 High（開発環境起動不可）

### 問題の概要

worktree環境で `./scripts/dev-start.sh` を実行すると、以下のエラーが発生してjobqueueサービスが起動しない：

```
sqlalchemy.exc.InvalidRequestError: The asyncio extension requires an async driver to be used. The loaded 'pysqlite' is not async.
```

また、以下の付随的な問題も発見：
1. CommonUIの起動状態チェックが誤って"Not running"を報告
2. myAgentDeskが起動対象に含まれていない

### 根本原因

#### 1. DATABASE_URL環境変数の読み込み失敗

**技術的詳細**:
- pydantic-settings v2の `env_file` パラメータは相対パスをCWD（Current Working Directory）基準で解決
- dev-start.shはリポジトリルートから実行されるため、各サービスの `.env` ファイルが正しく読み込まれない
- 結果として、jobqueueがmyschedulerの `DATABASE_URL=sqlite:///./data/jobs.db` を読み込んでしまう
- `sqlite:///` は同期ドライバ（pysqlite）のため、非同期SQLAlchemy（aiosqlite）と互換性がない

**問題のコード** (`jobqueue/app/core/config.py`):
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",  # ❌ 相対パス - CWD依存
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )

    database_url: str = Field(default="sqlite+aiosqlite:///./data/jobqueue.db")
```

dev-start.shからuvicornを起動すると：
- CWD = `/path/to/MySwiftAgent` (リポジトリルート)
- `.env` を `リポジトリルート/.env` から探す → 見つからない or 別サービスの .env
- デフォルト値もロードされず、間違った値が適用される

#### 2. load_dotenv() との競合

初期調査で `load_dotenv()` と pydantic-settings が競合していることを発見：
- 両方が環境変数をロードしようとする
- `@lru_cache` デコレータによるシングルトンパターンがモジュール間で汚染される

#### 3. CommonUI ステータスチェック失敗

**技術的詳細**:
- `check_service_status()` 関数が `/health` エンドポイントの存在を前提としている
- FastAPIサービス（jobqueue、myscheduler等）は `/health` を提供
- StreamlitアプリケーションであるCommonUIは `/health` エンドポイントを持たない
- 結果として、CommonUIが正常動作していても "Not running" と誤判定される

**問題のコード** (scripts/dev-start.sh 旧版):
```bash
check_service_status() {
    # ...
    if curl -sf "$health_url/health" >/dev/null 2>&1; then
        print_success "$name: Running healthy"
    else
        print_error "$name: Not running"  # ❌ Streamlitは常にここ
    fi
}
```

### 解決策

#### Fix 1: DATABASE_URL環境変数の明示的設定

**変更**: `scripts/dev-start.sh:805`

dev-start.sh内で、jobqueue起動時に `DATABASE_URL` を明示的に環境変数として渡す：

```bash
# Before:
start_service "JobQueue" "$JOBQUEUE_DIR" $JOBQUEUE_PORT "$JOBQUEUE_PID" "$JOBQUEUE_LOG" \
    "LOG_DIR='$LOG_DIR' LOG_LEVEL='$jobqueue_log_level' uv run uvicorn app.main:app --host 0.0.0.0 --port $JOBQUEUE_PORT" || exit 1

# After:
start_service "JobQueue" "$JOBQUEUE_DIR" $JOBQUEUE_PORT "$JOBQUEUE_PID" "$JOBQUEUE_LOG" \
    "DATABASE_URL='sqlite+aiosqlite:///./data/jobqueue.db' LOG_DIR='$LOG_DIR' LOG_LEVEL='$jobqueue_log_level' uv run uvicorn app.main:app --host 0.0.0.0 --port $JOBQUEUE_PORT" || exit 1
```

**効果**:
- 環境変数が確実に正しい値（`sqlite+aiosqlite:///./data/jobqueue.db`）で設定される
- pydantic-settingsの環境変数優先順位により、.envファイルより優先される
- CWD依存の問題を回避

#### Fix 2: config.py のクリーンアップ

**変更**: `jobqueue/app/core/config.py`

1. `load_dotenv()` 呼び出しを削除（pydantic-settingsと競合）
2. `@lru_cache` デコレータを削除し、カスタムシングルトンパターンに変更
3. `env_file` を絶対パスに変更

```python
"""Application configuration."""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Calculate absolute path to jobqueue/.env
PROJECT_ROOT = Path(__file__).parent.parent.parent
env_path = PROJECT_ROOT / ".env"

class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=str(env_path) if env_path.exists() else None,  # ✅ 絶対パス
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )

    database_url: str = Field(default="sqlite+aiosqlite:///./data/jobqueue.db")
    # ... other fields ...

# Singleton instance - created once on first import
_settings_instance: Settings | None = None

def get_settings() -> Settings:
    """Get settings instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
```

#### Fix 3: database.py の遅延初期化

**変更**: `jobqueue/app/core/database.py`

データベースエンジンの初期化を遅延させ、設定ロード後に実行するように変更：

```python
# Lazy initialization to ensure .env is loaded before creating engine
_engine = None
_session_maker = None

def _init_engine() -> None:
    """Initialize database engine and session maker (lazy initialization)."""
    global _engine, _session_maker

    if _engine is not None:
        return

    settings = get_settings()

    # Debug logging
    logger.info(f"[DATABASE] DATABASE_URL from settings: {settings.database_url}")

    # Create database directory if it doesn't exist
    if settings.database_url.startswith("sqlite"):
        db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    _engine = create_async_engine(
        settings.database_url,
        echo=False,
        future=True,
    )

    # Enable WAL mode for SQLite
    if settings.database_url.startswith("sqlite"):
        def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        event.listen(_engine.sync_engine, "connect", set_sqlite_pragma)

    _session_maker = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    logger.info(f"Database engine initialized with URL: {settings.database_url}")

def get_engine():
    """Get database engine (creates it if not initialized)."""
    _init_engine()
    return _engine

def get_session_maker():
    """Get session maker (creates it if not initialized)."""
    _init_engine()
    return _session_maker
```

**主要な変更点**:
- グローバルな `AsyncSessionLocal` を削除
- `get_session_maker()` 関数を追加し、遅延初期化を保証
- デバッグログを追加して DATABASE_URL の値を追跡

#### Fix 4: CommonUI ステータスチェック修正

**変更**: `scripts/dev-start.sh:479-504`

`check_service_status()` 関数を改修し、`/health` エンドポイントがない場合はHTTPステータスコードで判定：

```bash
check_service_status() {
    local name=$1
    local pid_file=$2
    local port=$3
    local health_url="http://localhost:$port"

    if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        local pid=$(cat "$pid_file")
        if check_port $port; then
            # Try health endpoint first (for FastAPI services)
            if curl -sf "$health_url/health" >/dev/null 2>&1; then
                print_success "$name: Running healthy (PID: $pid, Port: $port)"
            # If no health endpoint, just check if port responds (for Streamlit, SvelteKit, etc.)
            elif curl -sf -o /dev/null -w "%{http_code}" "$health_url" 2>/dev/null | grep -qE "^(200|301|302|404)"; then
                print_success "$name: Running (PID: $pid, Port: $port)"
            else
                print_warning "$name: Running but health check failed (PID: $pid, Port: $port)"
            fi
        else
            print_warning "$name: Process exists but port $port not listening (PID: $pid)"
        fi
    else
        print_error "$name: Not running"
        rm -f "$pid_file" 2>/dev/null || true
    fi
}
```

**効果**:
- FastAPIサービス: `/health` エンドポイントでヘルスチェック
- Streamlit/SvelteKitサービス: HTTPステータスコード（200, 301, 302, 404）で判定
- CommonUIが正しく "Running" と表示される

#### Fix 5: myAgentDesk サービス統合

**変更**: `scripts/dev-start.sh` の複数箇所

myAgentDeskを起動対象に追加：

1. **ポート設定** (line 39):
```bash
MYAGENTDESK_PORT="${MYAGENTDESK_PORT:-8000}"
```

2. **ディレクトリ設定** (line 58):
```bash
MYAGENTDESK_DIR="$PROJECT_ROOT/myAgentDesk"
```

3. **ログファイル設定** (line 71):
```bash
MYAGENTDESK_LOG="$LOG_DIR/myagentdesk.log"
```

4. **PIDファイル設定** (line 81):
```bash
MYAGENTDESK_PID="$PID_DIR/myagentdesk.pid"
```

5. **バナー更新** (line 102): MyAgentDeskを表示に追加

6. **サービスURL表示** (line 540): URL情報を追加

7. **起動コマンド** (lines 909-926):
```bash
# Start myAgentDesk (Streamlit)
if check_project_dir "$MYAGENTDESK_DIR"; then
    print_header "Starting myAgentDesk (Streamlit)"

    if ! install_service_deps "$MYAGENTDESK_DIR"; then
        print_error "Failed to install dependencies for myAgentDesk"
        exit 1
    fi

    start_service "MyAgentDesk" "$MYAGENTDESK_DIR" $MYAGENTDESK_PORT "$MYAGENTDESK_PID" "$MYAGENTDESK_LOG" \
        "LOG_DIR='$LOG_DIR' LOG_LEVEL='INFO' uv run streamlit run Home.py --server.port $MYAGENTDESK_PORT --server.address 0.0.0.0" || exit 1
else
    print_warning "myAgentDesk directory not found, skipping"
fi
```

8. **停止コマンド** (lines 939-941): 停止処理に追加

9. **ステータスコマンド** (lines 991-993): ステータス確認に追加

### 検証方法

#### 1. サービス起動確認

```bash
cd /Users/maenokota/share/work/github_kewton/MySwiftAgent-worktrees/fix-issue-166
./scripts/dev-start.sh
```

期待される出力:
```
✅ JobQueue: Running healthy (PID: 12345, Port: 8001)
✅ MyScheduler: Running healthy (PID: 12346, Port: 8002)
✅ MyVault: Running healthy (PID: 12347, Port: 8003)
✅ ExpertAgent: Running healthy (PID: 12348, Port: 8004)
✅ GraphAiServer: Running healthy (PID: 12349, Port: 8005)
✅ CommonUI: Running (PID: 12350, Port: 8501)
✅ MyAgentDesk: Running (PID: 12351, Port: 8000)
```

#### 2. DATABASE_URL確認

jobqueueログで正しいDATABASE_URLがロードされているか確認：

```bash
grep "DATABASE_URL from settings" logs/jobqueue.log | tail -1
```

期待される出力:
```
[DATABASE] DATABASE_URL from settings: sqlite+aiosqlite:///./data/jobqueue.db
```

#### 3. CommonUIアクセス確認

ブラウザで http://localhost:8501 にアクセスし、StreamlitアプリケーションのUIが表示されることを確認。

#### 4. myAgentDeskアクセス確認

ブラウザで http://localhost:8000 にアクセスし、myAgentDeskのUIが表示されることを確認。

### 影響を受けるファイル

| ファイルパス | 変更種別 | 変更内容 |
|------------|---------|---------|
| `scripts/dev-start.sh` | 修正 | DATABASE_URL環境変数追加、CommonUIステータスチェック修正、myAgentDesk統合 |
| `jobqueue/app/core/config.py` | 修正 | load_dotenv削除、カスタムシングルトン実装、絶対パス使用 |
| `jobqueue/app/core/database.py` | 修正 | 遅延初期化パターン実装、デバッグログ追加 |
| `jobqueue/app/core/worker.py` | 修正 | get_session_maker()使用に変更 |
| `jobqueue/scripts/seed_phase1_test_data.py` | 修正 | get_session_maker()使用に変更 |
| `jobqueue/scripts/seed_missing_interfaces.py` | 修正 | get_session_maker()使用に変更 |

### コミット情報

- **コミットハッシュ**: 0852724
- **コミットメッセージ**: "fix(global): resolve Issue #166 SQLAlchemy async driver errors in worktree environment"
- **変更統計**: +199行追加、-55行削除
- **コミット日時**: 2025-11-13

### 学んだこと

#### 技術的な学び

1. **pydantic-settings v2の挙動**:
   - `env_file` パラメータの相対パスはCWD基準で解決される
   - 絶対パスを使用することで予測可能な動作を保証できる
   - 環境変数 > .envファイル の優先順位を活用

2. **SQLAlchemy非同期ドライバー**:
   - `sqlite:///` = 同期ドライバ (pysqlite)
   - `sqlite+aiosqlite:///` = 非同期ドライバ (aiosqlite)
   - AsyncSessionとの組み合わせには非同期ドライバが必須

3. **Pythonモジュールキャッシング**:
   - `@lru_cache` はモジュール間で状態を共有する可能性がある
   - カスタムシングルトンパターンで明示的な制御が可能

4. **サービスヘルスチェック**:
   - FastAPI: `/health` エンドポイント標準
   - Streamlit: HTTPステータスコードで判定
   - 汎用的なチェック関数は複数のパターンに対応すべき

#### プロセス改善

1. **デバッグログの重要性**:
   - 設定値を明示的にログ出力することで問題の特定が容易になる
   - DATABASE_URLのような重要な設定は起動時に必ずログに記録

2. **worktree環境での検証**:
   - メインリポジトリで動作してもworktreeで動作しない可能性がある
   - CWD依存のコードは特に注意が必要

3. **段階的な問題解決**:
   - 複数の問題（SQLAlchemy、CommonUI、myAgentDesk）を一度に解決
   - 各問題の根本原因を理解してから修正することが重要

### 関連Issue/PR

- **Issue**: #166
- **PR**: (作成予定)
- **関連ドキュメント**:
  - [開発フロー](../claude/01-development-workflow.md)
  - [品質基準](../claude/04-quality-standards.md)
  - [worktreeガイド](../claude/05-worktree-guide.md)

### 補足事項

#### myAgentDesk ビルドエラー

myAgentDeskの起動時に以下のエラーが発生する場合があります：

```
[09:21:44] ❌ MyAgentDesk: Failed to build TypeScript project
```

**原因**: vitestの依存関係が不足

**対処法**:
```bash
cd myAgentDesk
npm install --save-dev vitest
npm run build
```

このエラーはIssue #166の主要な問題（SQLAlchemyエラー）とは独立しており、別途対処が必要です。

---

**最終更新**: 2025-11-13
**作成者**: Claude Code
**カテゴリ**: トラブルシューティング
**対象環境**: worktree、開発環境全般
