# 概要
外部の REST API を柔軟にスケジュール実行します。
自動タグ生成機能のテストを実行中です。
FastAPI でジョブ管理用のRESTエンドポイントを公開し、APScheduler で cron / interval / date の各トリガを扱い、SQLite にジョブを永続化します。タイムゾーンは Asia/Tokyo を使用します。

---

主な機能

- ジョブの 作成 / 一覧 / 一時停止 / 再開 / 削除
- スケジュール種別：cron、interval、date（一回限り）
- 実行内容：任意の HTTP メソッド（GET/POST/PUT/PATCH/DELETE） で外部 REST API を叩く
- SQLite 永続化（再起動してもジョブが復元）
- 失敗時リトライ（回数・バックオフ設定可）
- 同時実行抑制（同一ジョブ max_instances=1）

---

ディレクトリ構成（最小）

```
.
├─ app.py          # 本体
├─ jobs.db         # SQLite（初回起動時に自動作成）
└─ requirements.txt（任意）
```

jobs.db は APScheduler のジョブストアです。バックアップ対象に含めてください。

---

前提

- Python 3.12+
- タイムゾーン：Asia/Tokyo（zoneinfo を使用）
- 単一プロセス運用（APScheduler は 1 プロセス 1 スケジューラが基本）

---

セットアップ

```bash
# 1) 依存関係のインストール
pip install fastapi uvicorn[standard] apscheduler sqlalchemy httpx

# 2) 起動（開発）
uvicorn app:app --reload

# 3) 本番の例（単一ワーカー推奨）
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1
```

重要：複数ワーカー/複数Podで同一DBを共有すると 二重実行 の恐れがあります。
本プロジェクトは 単一ワーカー/単一Pod を前提としてください（水平スケールが必要な場合は後述の「拡張アーキテクチャ」を検討）。

---

API

1) ジョブ作成 POST /jobs

- スケジュール種別は schedule_type: "cron" | "interval" | "date" から選択
- 外部API呼び出し先は target_url、メソッドは method
- 任意で headers、body、timeout_sec、max_retries、retry_backoff_sec
- cron 用のフィールド、interval 用のフィールド、date 用の run_at を使い分け

リクエスト例（cron：毎日10:30）

```json
{
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

リクエスト例（interval：10分おき）

```json
{
  "schedule_type": "interval",
  "interval": { "minutes": 10 },
  "target_url": "https://example.com/health/check",
  "method": "GET"
}
```

リクエスト例（date：一回だけ）

```json
{
  "schedule_type": "date",
  "run_at": "2025-09-20T15:00:00+09:00",
  "target_url": "https://example.com/billing/run",
  "method": "POST",
  "body": { "month": "2025-09" }
}
```

レスポンス例

```json
{ "job_id": "a2f7c0b1-1e77-4b07-8c2b-6e5f9b2b8c3a", "status": "scheduled" }
```

job_id を自分で指定したい場合はリクエストに job_id を含めてください（既存IDと衝突する場合は replace_existing の挙動に依存）。

---

2) ジョブ一覧 GET /jobs

```json
{
  "jobs": [
    {
      "job_id": "a2f7c0b1-1e77-4b07-8c2b-6e5f9b2b8c3a",
      "next_run_time": "2025-09-20T15:00:00+09:00",
      "trigger": "date[2025-09-20 15:00:00 JST]"
    }
  ]
}
```


---

3) ジョブ削除 DELETE /jobs/{job_id}

```json
{ "job_id": "a2f7c0b1-1e77-4b07-8c2b-6e5f9b2b8c3a", "status": "deleted" }
```


---

4) 一時停止 / 再開

- 一時停止：POST /jobs/{job_id}/pause

```json
{ "job_id": "xxx", "status": "paused" }
```

- 再開：POST /jobs/{job_id}/resume

```json
{ "job_id": "xxx", "status": "resumed" }
```

---

cURL サンプル

```bash
# 作成（cron）
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "schedule_type": "cron",
    "cron": {"hour": "10", "minute": "30"},
    "target_url": "https://example.com/api/run-report",
    "method": "POST",
    "headers": {"Authorization": "Bearer XXX"},
    "body": {"report":"daily","projectId":123}
  }'

# 一覧
curl http://localhost:8000/jobs

# 停止
curl -X POST http://localhost:8000/jobs/<job_id>/pause

# 再開
curl -X POST http://localhost:8000/jobs/<job_id>/resume

# 削除
curl -X DELETE http://localhost:8000/jobs/<job_id>
```


---

実装のポイント

- Asia/Tokyo：AsyncIOScheduler(timezone=TZ) でタイムゾーン固定
- 永続化：SQLAlchemyJobStore(url="sqlite:///jobs.db")
- 同時実行抑制：max_instances=1
- ミスファイア：misfire_grace_time で許容秒数を設定
- コアレッシング：coalesce=True で積み残しを1回に圧縮
- HTTP実行：httpx.AsyncClient、5xxはリトライ、4xxは即終了（サンプル実装）
- ログ/結果：標準出力に要約出力。要件に応じて DB や外部ロガーに記録してください

---

運用・本番ガイド

- 単一ワーカーで起動：

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1
```

- プロセス管理：systemd や Supervisor、Docker でコンテナ化
- バックアップ：jobs.db（スキーマは APScheduler 管理）
- 機密情報：APIトークン等は環境変数 or シークレットマネージャを使用
- 可観測性：構造化ログ、失敗回数・レイテンシ等のメトリクスを導入（例：Prometheus）

---

Docker（任意）

Dockerfile（例）

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY app.py /app/
RUN pip install --no-cache-dir fastapi uvicorn[standard] apscheduler sqlalchemy httpx
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

ビルド & 実行

```bash
docker build -t scheduler-api .
docker run -d --name scheduler -p 8000:8000 -v $PWD/data:/app -e TZ=Asia/Tokyo scheduler-api
```

永続化を確実にするには jobs.db を ボリューム に置く（例：-v $PWD/data:/app にし、/app/jobs.db をマウント先に生成）。

---

Kubernetes（任意）

- 単一Pod 運用を推奨（HPAで横に伸ばさない）
- 永続化用に PersistentVolumeClaim を割り当て、jobs.db をマウント
- Ingress 経由で API を公開し、RBAC/ネットワークポリシでアクセス制御

---

トラブルシュート

- 二重実行される：複数ワーカー/複数Podで動かしていないか確認
- 時刻がずれる：コンテナ/OS の TZ 設定、Asia/Tokyo 指定を確認
- ジョブが復元されない：jobs.db の権限・マウント・パスを確認
- 外部APIが失敗し続ける：max_retries と retry_backoff_sec、タイムアウト値の見直し、接続先のレート制限確認

---

拡張アイデア

- 実行履歴テーブル（開始/終了時刻、HTTPステータス、レスポンス抜粋、再実行API）
- ジョブ所有者/認可（APIキーやJWT、IP制限）
- 署名付きWebhook（外部API側検証）
- メトリクス（Prometheus エクスポート／OpenTelemetry）
- 分散要件が強い場合：Celery Beat + Worker + Redis/Valkey へ移行

---

ライセンス

MIT など任意。プロジェクト方針に合わせて設定してください。

---

クイックリンク

- 起動（開発）: uvicorn app:app --reload
- APIドキュメント: http://localhost:8000/docs（Swagger UI）
- 動作確認: curl http://localhost:8000/jobs

---

必要に応じて、README をあなたの運用環境（k3s / Ingress / Auth / 監査要件）向けにカスタマイズした版も用意できます。