# MyScheduler

🕐 **MyScheduler** はジョブスケジューリングサービスです。
外部REST APIを柔軟にスケジュール実行します。

| 項目 | 値 |
|------|-----|
| **レイヤー** | Platform層 |
| **役割** | ジョブスケジューリング |
| **技術スタック** | Python + FastAPI + APScheduler |
| **ポート** | 8002 |

## ドキュメント

- **[API Reference](./docs/API_REFERENCE.md)** - 全APIエンドポイント仕様

## ✨ 特徴

- 🚀 **高性能**: FastAPI + APScheduler による高性能スケジューリング
- 📅 **柔軟なスケジューリング**: cron、interval、date（一回限り）対応
- 🔄 **HTTP統合**: 任意のREST APIを実行対象に設定可能
- 💾 **永続化**: SQLiteによるジョブ状態の永続化（再起動後も復元）
- 🔁 **リトライ機能**: 失敗時の自動リトライ（回数・バックオフ設定可）
- 📊 **実行履歴**: 詳細な実行ログとパフォーマンス監視
- 🎯 **即座実行**: スケジュールとは独立したTrigger Now機能
- 🏷️ **ジョブ名管理**: ユーザーフレンドリーなジョブ名設定
- 🛡️ **同時実行制御**: 同一ジョブの同時実行抑制（max_instances=1）
- 🌏 **タイムゾーン**: Asia/Tokyo固定

## 📦 プロジェクト構成

```
myscheduler/
├── app/
│   ├── main.py              # FastAPIアプリケーション
│   ├── api/                 # APIエンドポイント
│   │   └── v1/
│   │       └── jobs.py      # ジョブ管理API
│   ├── core/                # コア機能
│   │   ├── config.py        # 設定管理
│   │   └── logging.py       # ログ設定
│   ├── db/                  # データベース
│   │   └── session.py       # DB接続・スケジューラ管理
│   ├── models/              # データモデル
│   │   ├── job.py           # ジョブモデル（Pydantic）
│   │   └── execution.py     # 実行履歴モデル（SQLAlchemy ORM）
│   ├── repositories/        # データアクセス層
│   │   └── execution_repository.py # 実行履歴リポジトリ
│   ├── schemas/             # APIスキーマ
│   │   └── job.py           # リクエスト・レスポンススキーマ
│   └── services/            # ビジネスロジック
│       ├── job_service.py   # ジョブ管理サービス
│       └── job_executor.py  # ジョブ実行エンジン
├── tests/                   # テストコード
├── pyproject.toml           # プロジェクト設定
├── Dockerfile               # Docker設定
└── README.md                # このファイル
```

## 🚀 セットアップ

### 前提条件

- Python 3.12以上
- [uv](https://docs.astral.sh/uv/) パッケージマネージャ

### インストール

```bash
# 1. リポジトリクローン
git clone https://github.com/Kewton/MySwiftAgent.git
cd MySwiftAgent/myscheduler

# 2. 依存関係インストール
uv sync --extra dev

# 3. アプリケーション起動
uv run uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

### 設定

環境変数による設定（オプション）:
```bash
# タイムゾーン設定（デフォルト: Asia/Tokyo）
TZ=Asia/Tokyo

# データベースURL（デフォルト: SQLite）
DATABASE_URL=sqlite:///./data/jobs.db

# ログレベル（デフォルト: INFO）
LOG_LEVEL=INFO
```

## 🏃 起動方法

### 開発環境

```bash
# 開発モード（自動リロード）
uv run uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload

# APIドキュメント: http://localhost:8003/docs
```

### 本番環境

```bash
# 本番モード（単一ワーカー推奨）
uv run uvicorn app.main:app --host 0.0.0.0 --port 8003 --workers 1

# 重要: 複数ワーカーでの運用は二重実行の恐れがあります
```

## 📋 API仕様

### ベースURL
```
http://localhost:8003/api/v1
```

### 1. ジョブ作成 `POST /jobs`

#### リクエスト例（cron：毎日10:30）

```json
{
  "job_id": "daily-report",
  "name": "日次レポート生成",
  "schedule_type": "cron",
  "cron": { "hour": "10", "minute": "30" },
  "target_url": "https://example.com/api/run-report",
  "method": "POST",
  "headers": { "Authorization": "Bearer XXX" },
  "body": { "report": "daily", "projectId": 123 },
  "max_retries": 2,
  "retry_backoff_sec": 2.0
}
```

#### リクエスト例（interval：10分おき）

```json
{
  "name": "ヘルスチェック",
  "schedule_type": "interval",
  "interval": { "minutes": 10 },
  "target_url": "https://example.com/health/check",
  "method": "GET"
}
```

#### リクエスト例（date：一回だけ）

```json
{
  "name": "月末請求処理",
  "schedule_type": "date",
  "run_at": "2025-09-30T15:00:00+09:00",
  "target_url": "https://example.com/billing/run",
  "method": "POST",
  "body": { "month": "2025-09" }
}
```

#### レスポンス

```json
{
  "job_id": "a2f7c0b1-1e77-4b07-8c2b-6e5f9b2b8c3a",
  "status": "scheduled"
}
```

### 2. ジョブ一覧 `GET /jobs`

```json
{
  "jobs": [
    {
      "job_id": "daily-report",
      "id": "daily-report",
      "name": "日次レポート生成",
      "next_run_time": "2025-09-30T10:30:00+09:00",
      "trigger": "cron[hour='10', minute='30']",
      "status": "running",
      "target_url": "https://example.com/api/run-report",
      "method": "POST",
      "execution_count": 15
    }
  ]
}
```

### 3. ジョブ詳細 `GET /jobs/{job_id}`

```json
{
  "job_id": "daily-report",
  "name": "日次レポート生成",
  "func": "execute_http_job",
  "status": "running",
  "trigger": "cron[hour='10', minute='30']",
  "next_run_time": "2025-09-30T10:30:00+09:00",
  "execution_count": 15,
  "trigger_info": {
    "type": "cron",
    "cron": {
      "hour": "10",
      "minute": "30"
    }
  },
  "target_url": "https://example.com/api/run-report",
  "method": "POST",
  "headers": { "Authorization": "Bearer XXX" },
  "body": { "report": "daily", "projectId": 123 },
  "timeout_sec": 30.0,
  "max_retries": 2,
  "retry_backoff_sec": 2.0,
  "executions": [
    {
      "execution_id": "abc123...",
      "job_id": "daily-report",
      "started_at": "2025-09-29T10:30:00",
      "completed_at": "2025-09-29T10:30:02",
      "status": "completed",
      "result": {
        "success": true,
        "status_code": 200,
        "response_size": 1024,
        "attempts": 1
      },
      "execution_time_ms": 2000,
      "http_status_code": 200,
      "response_size": 1024
    }
  ]
}
```

### 4. ジョブ制御操作

#### 一時停止 `POST /jobs/{job_id}/pause`
```json
{ "job_id": "daily-report", "status": "paused" }
```

#### 再開 `POST /jobs/{job_id}/resume`
```json
{ "job_id": "daily-report", "status": "resumed" }
```

#### 即座実行 `POST /jobs/{job_id}/trigger`
```json
{ "job_id": "daily-report", "status": "triggered" }
```

#### 削除 `DELETE /jobs/{job_id}`
```json
{ "job_id": "daily-report", "status": "deleted" }
```

### 5. 実行履歴

#### ジョブ実行履歴 `GET /jobs/{job_id}/executions?limit=50`
```json
{
  "job_id": "daily-report",
  "executions": [...],
  "count": 15
}
```

#### 最近の実行履歴 `GET /jobs/executions/recent?limit=100`
```json
{
  "executions": [...],
  "count": 25
}
```

## 🔧 開発・テスト

### コード品質チェック

```bash
# 静的解析・フォーマット
uv run ruff check .
uv run ruff format .
uv run mypy .
```

### テスト実行

```bash
# 全テスト実行
uv run pytest

# カバレッジ付きテスト
uv run pytest --cov=app --cov-report=term-missing

# 統合テスト
uv run pytest tests/integration/ -v
```

### 起動確認

```bash
# アプリケーション起動テスト
curl http://localhost:8003/health
```

## 🛡️ 実装の特徴

### スケジューラ設定
- **タイムゾーン**: `AsyncIOScheduler(timezone=Asia/Tokyo)` でタイムゾーン固定
- **永続化**: `SQLAlchemyJobStore(url="sqlite:///./data/jobs.db")`
- **同時実行抑制**: `max_instances=1`
- **ミスファイア**: `misfire_grace_time` で許容秒数を設定
- **コアレッシング**: `coalesce=True` で積み残しを1回に圧縮

### HTTP実行エンジン
- **非同期クライアント**: `httpx.AsyncClient` による高性能HTTP通信
- **リトライ戦略**: 5xxエラーのみリトライ、4xxエラーは即終了
- **タイムアウト制御**: リクエスト単位での細かなタイムアウト設定
- **レスポンス追跡**: HTTPステータス、レスポンスサイズ、実行時間の記録

### 実行履歴管理
- **詳細トラッキング**: 開始/終了時刻、ステータス、実行時間を記録
- **エラー情報**: 失敗時のエラーメッセージとHTTPステータス
- **パフォーマンス**: レスポンスサイズ、実行時間、リトライ回数
- **効率的クエリ**: 実行回数の高速カウントとページング対応

## 🐳 Docker

### Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --no-dev

# Copy application code
COPY app/ ./app/

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8003/health || exit 1

EXPOSE 8003

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
```

### ビルド & 実行

```bash
# イメージビルド
docker build -t myscheduler:latest .

# コンテナ起動（データベース永続化）
docker run -d --name myscheduler \
  -p 8003:8003 \
  -v $PWD/data:/app/data \
  -e TZ=Asia/Tokyo \
  myscheduler:latest
```

## ☸️ Kubernetes（本番運用）

### 運用指針
- **単一Pod運用**: HPAで横スケールしない（二重実行防止）
- **永続化**: PersistentVolumeClaimでSQLiteを永続化
- **ネットワーク**: IngressでHTTPS通信、RBACでアクセス制御

### Deployment例

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myscheduler
spec:
  replicas: 1  # 必ず1に固定
  selector:
    matchLabels:
      app: myscheduler
  template:
    metadata:
      labels:
        app: myscheduler
    spec:
      containers:
      - name: myscheduler
        image: myscheduler:latest
        ports:
        - containerPort: 8003
        env:
        - name: TZ
          value: "Asia/Tokyo"
        volumeMounts:
        - name: data
          mountPath: /app/data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: myscheduler-data
```

## 🔗 CommonUI統合

MySchedulerは[CommonUI](../commonUI/README.md)と統合されており、Web UIからの操作が可能です：

### 対応機能
- ✅ ジョブ作成（スケジュール設定、HTTP設定）
- ✅ ジョブ一覧表示（名前、実行回数、ステータス）
- ✅ ジョブ詳細表示（設定、実行履歴）
- ✅ ジョブ制御（停止/再開/削除/即座実行）
- ✅ 実行履歴の詳細表示（エラー情報、パフォーマンス）

### API連携
- `MYSCHEDULER_BASE_URL`: デフォルト `http://localhost:8003`
- `MYSCHEDULER_API_TOKEN`: API認証（将来対応予定）

## 📊 監視・可観測性

### ログ出力
- **構造化ログ**: JSON形式での詳細ログ出力
- **実行追跡**: ジョブ実行の開始/終了/結果をログ記録
- **エラー情報**: 例外スタックトレース、HTTPエラー詳細
- **パフォーマンス**: 実行時間、レスポンスサイズ、リトライ回数

### メトリクス（将来対応）
- Prometheusエクスポート
- OpenTelemetry統合
- カスタムメトリクス（実行回数、レイテンシ、成功率）

## ❗ トラブルシュート

### よくある問題と解決策

#### 二重実行される
- **原因**: 複数ワーカー/複数Podで実行
- **解決**: `--workers 1` で単一ワーカー実行

#### 時刻がずれる
- **原因**: タイムゾーン設定の不整合
- **解決**: コンテナ環境変数 `TZ=Asia/Tokyo` を確認

#### ジョブが復元されない
- **原因**: SQLiteファイル（data/jobs.db）のパス・権限問題
- **解決**: データベースファイルの権限・マウント状況を確認

#### 外部APIが失敗し続ける
- **原因**: タイムアウト、レート制限、認証エラー
- **解決**: `timeout_sec`, `max_retries`, `retry_backoff_sec` の調整

#### 実行履歴が表示されない
- **原因**: 実行履歴テーブルの作成・権限問題
- **解決**: データベース初期化、マイグレーション実行

## 🔮 拡張アイデア

### 次期バージョンで検討中の機能
- 🔐 **認証・認可**: APIキー、JWT、IP制限
- 🔒 **署名付きWebhook**: 外部API側での検証機能
- 📈 **メトリクス統合**: Prometheus、Grafana ダッシュボード
- 🌐 **分散実行**: Celery Beat + Worker + Redis/Valkey への移行
- 📧 **通知機能**: ジョブ失敗時のSlack/Email通知
- 🎯 **条件付き実行**: 前ジョブの成功/失敗による実行制御

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🔗 関連リンク

- [MySwiftAgent メインリポジトリ](https://github.com/Kewton/MySwiftAgent)
- [CommonUI プロジェクト](../commonUI/README.md)
- [JobQueue プロジェクト](../jobqueue/README.md)
- [CLAUDE.md 開発ルール](../CLAUDE.md)

---

## 🚀 クイックスタート

```bash
# 1. 起動
uv run uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload

# 2. APIドキュメント確認
open http://localhost:8003/docs

# 3. ヘルスチェック
curl http://localhost:8003/health

# 4. ジョブ作成テスト
curl -X POST http://localhost:8003/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "テストジョブ",
    "schedule_type": "interval",
    "interval": {"minutes": 1},
    "target_url": "http://localhost:8003/health",
    "method": "GET"
  }'

# 5. ジョブ一覧確認
curl http://localhost:8003/api/v1/jobs
```