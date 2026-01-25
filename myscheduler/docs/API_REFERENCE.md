# myscheduler API Reference

myschedulerが提供するジョブスケジューリングAPIの仕様です。

## 概要

myschedulerはAPSchedulerベースのジョブスケジューラです。
定期実行ジョブの登録、管理、実行を担当します。

## ベースURL

```
http://localhost:8002
```

## エンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/health` | ヘルスチェック |
| POST | `/api/v1/schedules` | スケジュール登録 |
| GET | `/api/v1/schedules` | スケジュール一覧 |
| GET | `/api/v1/schedules/{id}` | スケジュール詳細 |
| DELETE | `/api/v1/schedules/{id}` | スケジュール削除 |
| POST | `/api/v1/schedules/{id}/trigger` | 即時実行 |

---

## ヘルスチェック

### GET /health

```json
{
  "status": "healthy",
  "scheduler_running": true
}
```

---

## スケジュール登録

### POST /api/v1/schedules

**リクエスト**:
```json
{
  "name": "daily_report",
  "job_id": "job-uuid",
  "cron": "0 9 * * *",
  "timezone": "Asia/Tokyo"
}
```

**レスポンス**:
```json
{
  "id": "schedule-uuid",
  "name": "daily_report",
  "job_id": "job-uuid",
  "cron": "0 9 * * *",
  "next_run": "2026-01-26T09:00:00+09:00"
}
```

---

## スケジュール一覧

### GET /api/v1/schedules

**レスポンス**:
```json
{
  "schedules": [
    {
      "id": "schedule-uuid",
      "name": "daily_report",
      "cron": "0 9 * * *",
      "next_run": "2026-01-26T09:00:00+09:00",
      "status": "active"
    }
  ]
}
```

---

## Cron式

| フィールド | 値 | 説明 |
|-----------|-----|------|
| 分 | 0-59 | 分 |
| 時 | 0-23 | 時 |
| 日 | 1-31 | 日 |
| 月 | 1-12 | 月 |
| 曜日 | 0-6 | 日曜=0 |

**例**:
- `0 9 * * *` - 毎日9時
- `0 0 * * 1` - 毎週月曜0時
- `*/15 * * * *` - 15分ごと

---

## 関連ドキュメント

- [jobqueue API](../../jobqueue/docs/api/)
- [システム概要](../../docs/architecture/overview.md)
