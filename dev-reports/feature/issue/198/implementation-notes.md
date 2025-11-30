# Implementation Notes: docker-compose.platform.yml

**Issue番号**: #198
**親Issue**: #197
**作成日**: 2025-11-30
**ステータス**: 完了

---

## 1. 実装概要

### 1.1 目的

MySwiftAgentの運用基盤レイヤ（Platform Layer）を独立したdocker-compose定義ファイルとして分離し、レイヤ別起動の基盤を構築した。

### 1.2 成果物

| 成果物 | パス | 説明 |
|--------|------|------|
| Platform Layer定義 | `docker-compose.platform.yml` | 運用基盤サービスのDocker Compose定義 |
| 実装メモ | `dev-reports/feature/issue/198/implementation-notes.md` | 本ドキュメント |

---

## 2. 設計判断事項

### 2.1 ネットワーク構成

**判断**: 外部ネットワーク（external: true）を採用

**理由**:
- レイヤ間の通信を可能にするため
- 各レイヤのcomposeファイルが独立して起動・停止できるようにするため
- ネットワークのライフサイクルをサービスから分離するため

**設定**:
```yaml
networks:
  myswiftagent:
    external: true
    name: myswiftagent-network
```

**使用前の準備**:
```bash
docker network create myswiftagent-network
```

### 2.2 サービスグルーピング

Platform Layerに含めるサービスを以下の基準で選定した:

| グループ | サービス | 選定理由 |
|---------|---------|---------|
| Core Platform | valkey, jobqueue, myscheduler, myvault | アプリケーション共通のインフラ基盤 |
| Observability | langfuse-* (6サービス) | LLMトレーシング・監視基盤 |

**除外されたサービス**:
- `expertagent`: Agent Layerに分類
- `graphaiserver`: Agent Layerに分類
- `myagentdesk`: Frontend Layerに分類
- `commonui`: Frontend Layerに分類

### 2.3 ポート割り当て

ポート競合を避けるため、以下のポートマッピングを採用した:

| サービス | ホストポート | コンテナポート | 備考 |
|---------|------------|--------------|------|
| valkey | 6381 | 6379 | langfuse-redis(6380)との競合回避 |
| jobqueue | 8001 | 8000 | FastAPIデフォルト |
| myscheduler | 8002 | 8000 | FastAPIデフォルト |
| myvault | 8003 | 8000 | FastAPIデフォルト |
| langfuse-db | 5433 | 5432 | expertAgent PostgreSQL(5432)との競合回避 |
| langfuse-clickhouse | 8123, 9000 | 8123, 9000 | localhost bindのみ |
| langfuse-redis | 6380 | 6379 | localhost bindのみ |
| langfuse-minio | 9002, 9001 | 9000, 9001 | API(9002): ClickHouse(9000)との競合回避 |
| langfuse-worker | 3030 | 3030 | localhost bindのみ |
| langfuse-server | 3001 | 3000 | Web UI |

### 2.4 依存関係管理

**判断**: `depends_on` with `condition: service_healthy` を使用

**理由**:
- 起動順序の保証
- サービス間の依存関係を明示
- healthcheckによる準備完了の確認

**実装例**:
```yaml
myscheduler:
  depends_on:
    jobqueue:
      condition: service_healthy

langfuse-worker:
  depends_on:
    langfuse-db:
      condition: service_healthy
    langfuse-clickhouse:
      condition: service_healthy
    langfuse-redis:
      condition: service_healthy
    langfuse-minio:
      condition: service_healthy
```

### 2.5 YAML Anchor使用

**判断**: Langfuse環境変数でYAML Anchorを使用

**理由**:
- langfuse-worker と langfuse-server で共通の環境変数セットを共有
- DRY原則の適用
- 設定変更時の一貫性確保

**実装**:
```yaml
langfuse-worker:
  environment: &langfuse-env
    DATABASE_URL: postgresql://...
    # ... 共通設定

langfuse-server:
  environment:
    <<: *langfuse-env
    # 追加設定（Headless Initialization）
    LANGFUSE_INIT_ORG_NAME: ...
```

---

## 3. サービス詳細

### 3.1 Core Platform Services

#### valkey
- **役割**: インメモリデータストア（Redis互換）
- **用途**: 会話履歴の永続化、キャッシュ
- **healthcheck**: `valkey-cli PING`

#### jobqueue
- **役割**: ジョブキュー管理API
- **用途**: 非同期タスクのキュー管理
- **healthcheck**: `curl -f http://localhost:8000/health`
- **データ永続化**: `./docker-compose-data/jobqueue/`

#### myscheduler
- **役割**: ジョブスケジューリングサービス
- **用途**: 定期実行タスクの管理
- **依存**: jobqueue
- **healthcheck**: `curl -f http://localhost:8000/health`

#### myvault
- **役割**: シークレット管理サービス
- **用途**: APIキー、認証トークンの安全な保管
- **healthcheck**: `curl -f http://localhost:8000/health`
- **設定ファイル**: `./myVault/config.yaml` (read-only mount)

### 3.2 Langfuse Observability Stack

#### langfuse-db (PostgreSQL)
- **役割**: Langfuseメタデータ保存
- **イメージ**: `postgres:15-alpine`
- **healthcheck**: `pg_isready`

#### langfuse-clickhouse
- **役割**: 分析データ保存（高速クエリ）
- **イメージ**: `clickhouse/clickhouse-server:latest`
- **healthcheck**: `wget /ping`

#### langfuse-redis
- **役割**: Langfuse用キャッシュ
- **イメージ**: `redis:7-alpine`
- **healthcheck**: `redis-cli ping`

#### langfuse-minio
- **役割**: S3互換オブジェクトストレージ
- **用途**: イベントデータ、メディアファイル保存
- **healthcheck**: `curl /minio/health/live`

#### langfuse-worker
- **役割**: バックグラウンド処理ワーカー
- **イメージ**: `langfuse/langfuse-worker:3`
- **依存**: langfuse-db, langfuse-clickhouse, langfuse-redis, langfuse-minio
- **healthcheck**: `wget /api/health`

#### langfuse-server
- **役割**: Web UI・API サーバー
- **イメージ**: `langfuse/langfuse:3`
- **アクセス**: http://localhost:3001
- **healthcheck**: `wget /api/public/health`

---

## 4. healthcheck設定

全サービスにhealthcheckを設定し、起動状態の監視と依存関係制御を実現した。

| サービス | テストコマンド | interval | timeout | retries | start_period |
|---------|--------------|----------|---------|---------|--------------|
| valkey | `valkey-cli PING` | 30s | 10s | 3 | 5s |
| jobqueue | `curl -f /health` | 30s | 10s | 3 | 5s |
| myscheduler | `curl -f /health` | 30s | 10s | 3 | 10s |
| myvault | `curl -f /health` | 30s | 10s | 3 | 5s |
| langfuse-db | `pg_isready` | 10s | 5s | 10 | - |
| langfuse-clickhouse | `wget /ping` | 5s | 5s | 10 | 10s |
| langfuse-redis | `redis-cli ping` | 3s | 10s | 10 | - |
| langfuse-minio | `curl /minio/health/live` | 10s | 5s | 5 | 10s |
| langfuse-worker | `wget /api/health` | 30s | 10s | 3 | 30s |
| langfuse-server | `wget /api/public/health` | 30s | 10s | 3 | 60s |

---

## 5. 使用方法

### 5.1 初回セットアップ

```bash
# 1. 共有ネットワークを作成
docker network create myswiftagent-network

# 2. 環境変数ファイルを確認・編集
cp .env.docker.example .env.docker  # 必要に応じて
```

### 5.2 起動

```bash
# Platform Layer起動
docker compose -f docker-compose.platform.yml up -d

# 起動状態確認
docker compose -f docker-compose.platform.yml ps

# ログ確認
docker compose -f docker-compose.platform.yml logs -f
```

### 5.3 停止

```bash
# サービス停止（データは保持）
docker compose -f docker-compose.platform.yml down

# サービス停止 + ボリューム削除（データ消去）
docker compose -f docker-compose.platform.yml down -v
```

### 5.4 ヘルスチェック確認

```bash
# 各サービスのヘルスチェック
curl -sf http://localhost:8001/health && echo "jobqueue: OK"
curl -sf http://localhost:8002/health && echo "myscheduler: OK"
curl -sf http://localhost:8003/health && echo "myvault: OK"
curl -sf http://localhost:3001/api/public/health && echo "langfuse: OK"
```

---

## 6. テスト結果

### 6.1 YAML検証

```bash
docker compose -f docker-compose.platform.yml config
```
結果: パス（エラーなし）

### 6.2 単体起動テスト

| テスト項目 | 結果 | 備考 |
|-----------|------|------|
| 全サービス起動 | Pass | 10サービス全て起動 |
| healthcheck | Pass | 全サービスhealthy |
| ログエラー確認 | Pass | クリティカルエラーなし |

### 6.3 確認済み事項

- [x] 全10サービスが正常に起動する
- [x] 全サービスにhealthcheckが定義されている
- [x] 外部ネットワーク（myswiftagent-network）を使用している
- [x] サービス間の依存関係が正しく設定されている
- [x] ポート競合がない

---

## 7. 関連リンク

| ドキュメント | 説明 |
|-------------|------|
| [設計方針書](../197/design-policy.md) | docker-compose分離の全体設計 |
| [Issue分割計画書](../197/issue-split.md) | 関連Issue一覧 |
| [work-plan.md](./work-plan.md) | 本Issueの作業計画 |

---

## 8. 今後の拡張

### 8.1 関連Issue

- **#199**: docker-compose.agent.yml（Agent Layer）
- **#200**: docker-compose.frontend.yml（Frontend Layer）
- **#201**: Makefileでのレイヤ別起動コマンド

### 8.2 改善候補

1. **リソース制限の追加**: CPU/メモリ制限の設定
2. **ログローテーション**: 長期運用時のログ管理
3. **バックアップ設定**: データボリュームの定期バックアップ

---

**作成者**: Claude Code (Refactoring Agent)
**最終更新**: 2025-11-30
