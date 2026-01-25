# Valkey Operations Guide

## 概要

本ドキュメントは、MySwiftAgentにおけるValkey（Redis互換）の運用・管理手順を説明します。

## 目次

1. [デプロイメント](#デプロイメント)
2. [バックアップとリストア](#バックアップとリストア)
3. [モニタリング](#モニタリング)
4. [スケーリング](#スケーリング)
5. [トラブルシューティング](#トラブルシューティング)
6. [メンテナンス](#メンテナンス)

## デプロイメント

### 開発環境

```bash
# Docker Composeを使用
docker-compose up -d valkey

# または開発スクリプトを使用
./scripts/dev-start.sh start
```

### Worktree環境

```bash
# Worktree用のValkeyインスタンスをセットアップ
./scripts/setup-valkey-worktree.sh
```

### 本番環境

#### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: valkey
spec:
  replicas: 1
  selector:
    matchLabels:
      app: valkey
  template:
    metadata:
      labels:
        app: valkey
    spec:
      containers:
      - name: valkey
        image: valkey/valkey:latest
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: data
          mountPath: /data
        - name: config
          mountPath: /usr/local/etc/valkey
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "1Gi"
            cpu: "500m"
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: valkey-data
      - name: config
        configMap:
          name: valkey-config
```

## バックアップとリストア

### 手動バックアップ

#### RDB スナップショット

```bash
# バックアップ作成
docker exec myswiftagent-valkey valkey-cli BGSAVE

# バックアップ状態確認
docker exec myswiftagent-valkey valkey-cli LASTSAVE

# バックアップファイルをコピー
docker cp myswiftagent-valkey:/data/valkey.rdb ./backups/valkey-$(date +%Y%m%d-%H%M%S).rdb
```

#### AOF バックアップ

```bash
# AOFファイルをコピー
docker cp myswiftagent-valkey:/data/appendonly.aof ./backups/appendonly-$(date +%Y%m%d-%H%M%S).aof
```

### 自動バックアップ

#### Cronジョブ設定

```bash
# /etc/cron.d/valkey-backup
0 2 * * * root /opt/scripts/backup-valkey.sh
```

#### backup-valkey.sh

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/valkey"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
CONTAINER_NAME="myswiftagent-valkey"

# Create backup directory
mkdir -p $BACKUP_DIR

# Trigger BGSAVE
docker exec $CONTAINER_NAME valkey-cli BGSAVE

# Wait for completion
sleep 10

# Copy RDB file
docker cp $CONTAINER_NAME:/data/valkey.rdb $BACKUP_DIR/valkey-$TIMESTAMP.rdb

# Keep only last 7 days of backups
find $BACKUP_DIR -name "valkey-*.rdb" -mtime +7 -delete

echo "Backup completed: valkey-$TIMESTAMP.rdb"
```

### リストア手順

```bash
# 1. Valkeyを停止
docker-compose stop valkey

# 2. 既存データをバックアップ
mv valkey/data/valkey.rdb valkey/data/valkey.rdb.old

# 3. バックアップファイルをリストア
cp backups/valkey-20241114-020000.rdb valkey/data/valkey.rdb

# 4. Valkeyを起動
docker-compose up -d valkey

# 5. データ確認
docker exec myswiftagent-valkey valkey-cli DBSIZE
```

## モニタリング

### 基本メトリクス

```bash
# メモリ使用量
docker exec myswiftagent-valkey valkey-cli INFO memory | grep used_memory_human

# 接続数
docker exec myswiftagent-valkey valkey-cli INFO clients | grep connected_clients

# コマンド処理数
docker exec myswiftagent-valkey valkey-cli INFO stats | grep total_commands_processed

# キー数
docker exec myswiftagent-valkey valkey-cli DBSIZE
```

### Prometheusメトリクス

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'valkey'
    static_configs:
      - targets: ['valkey-exporter:9121']
```

### アラート設定

```yaml
# alert-rules.yml
groups:
  - name: valkey
    rules:
      - alert: ValkeyDown
        expr: up{job="valkey"} == 0
        for: 5m
        annotations:
          summary: "Valkey is down"

      - alert: ValkeyHighMemory
        expr: valkey_memory_used_bytes / valkey_memory_max_bytes > 0.9
        for: 5m
        annotations:
          summary: "Valkey memory usage above 90%"

      - alert: ValkeySlowQueries
        expr: rate(valkey_slowlog_length[5m]) > 10
        for: 5m
        annotations:
          summary: "High number of slow queries"
```

## スケーリング

### 垂直スケーリング

#### メモリ増設

```bash
# docker-compose.yml
services:
  valkey:
    deploy:
      resources:
        limits:
          memory: 2g  # 2GBに増設
```

#### 設定最適化

```bash
# valkey.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
```

### 水平スケーリング

#### レプリケーション設定

```yaml
# docker-compose.yml
services:
  valkey-master:
    image: valkey/valkey:latest
    ports:
      - "6379:6379"

  valkey-replica:
    image: valkey/valkey:latest
    command: valkey-server --slaveof valkey-master 6379
    ports:
      - "6380:6379"
    depends_on:
      - valkey-master
```

### パフォーマンスチューニング

```bash
# valkey.conf
# 接続数上限
maxclients 10000

# TCP設定
tcp-backlog 511
tcp-keepalive 300

# スローログ設定
slowlog-log-slower-than 10000
slowlog-max-len 128

# メモリ最適化
lazyfree-lazy-eviction yes
lazyfree-lazy-expire yes
```

## トラブルシューティング

### 問題: メモリ不足

**症状:**
```
OOM command not allowed when used memory > 'maxmemory'
```

**対処:**
```bash
# 1. 現在のメモリ使用量確認
docker exec myswiftagent-valkey valkey-cli INFO memory

# 2. 不要なキーを削除
docker exec myswiftagent-valkey valkey-cli FLUSHDB

# 3. メモリ上限を増やす
docker exec myswiftagent-valkey valkey-cli CONFIG SET maxmemory 2gb
```

### 問題: 接続エラー

**症状:**
```
Could not connect to Redis at localhost:6379: Connection refused
```

**対処:**
```bash
# 1. コンテナ状態確認
docker ps | grep valkey

# 2. ログ確認
docker logs myswiftagent-valkey

# 3. ポート確認
lsof -i :6379

# 4. コンテナ再起動
docker-compose restart valkey
```

### 問題: パフォーマンス低下

**症状:**
- レスポンスタイムが遅い
- CPU使用率が高い

**対処:**
```bash
# 1. スローログ確認
docker exec myswiftagent-valkey valkey-cli SLOWLOG GET 10

# 2. メモリ断片化確認
docker exec myswiftagent-valkey valkey-cli INFO memory | grep mem_fragmentation_ratio

# 3. 必要に応じてメモリデフラグ
docker exec myswiftagent-valkey valkey-cli MEMORY PURGE
```

## メンテナンス

### 定期メンテナンスタスク

#### 日次

1. **ヘルスチェック**
   ```bash
   docker exec myswiftagent-valkey valkey-cli PING
   ```

2. **メモリ使用量確認**
   ```bash
   docker exec myswiftagent-valkey valkey-cli INFO memory | grep used_memory_human
   ```

#### 週次

1. **バックアップ確認**
   ```bash
   ls -lh /var/backups/valkey/
   ```

2. **スローログ分析**
   ```bash
   docker exec myswiftagent-valkey valkey-cli SLOWLOG GET 50
   ```

#### 月次

1. **メモリ最適化**
   ```bash
   docker exec myswiftagent-valkey valkey-cli MEMORY DOCTOR
   ```

2. **設定レビュー**
   ```bash
   docker exec myswiftagent-valkey valkey-cli CONFIG GET "*"
   ```

### アップグレード手順

```bash
# 1. 現在のバージョン確認
docker exec myswiftagent-valkey valkey-cli INFO server | grep valkey_version

# 2. バックアップ作成
./scripts/backup-valkey.sh

# 3. 新しいイメージをプル
docker pull valkey/valkey:7.2

# 4. docker-compose.yml更新
# image: valkey/valkey:7.2

# 5. コンテナ再作成
docker-compose up -d valkey

# 6. 動作確認
docker exec myswiftagent-valkey valkey-cli PING
```

## セキュリティ

### パスワード設定

```bash
# valkey.conf
requirepass your-strong-password

# 環境変数
VALKEY_PASSWORD=your-strong-password
```

### ネットワークアクセス制限

```bash
# valkey.conf
bind 127.0.0.1 ::1
protected-mode yes
```

### TLS/SSL設定

```bash
# valkey.conf
tls-port 6380
port 0
tls-cert-file /path/to/cert.pem
tls-key-file /path/to/key.pem
tls-ca-cert-file /path/to/ca.pem
```

## 災害復旧計画

### RPO/RTO目標

- **RPO (Recovery Point Objective)**: 1時間
- **RTO (Recovery Time Objective)**: 30分

### 復旧手順

1. **バックアップからの復旧**
   - 最新のRDBファイルを特定
   - リストア手順を実行
   - データ整合性を確認

2. **レプリカからの昇格**
   ```bash
   # レプリカをマスターに昇格
   docker exec valkey-replica valkey-cli SLAVEOF NO ONE
   ```

3. **アプリケーション接続先変更**
   - 環境変数を更新
   - アプリケーションを再起動

## 参考資料

- [Valkey公式ドキュメント](https://valkey.io/)
- [Docker Compose仕様](https://docs.docker.com/compose/)
- [Kubernetes運用ガイド](https://kubernetes.io/docs/)
- [expertAgent Valkey統合ガイド](../../expertAgent/docs/valkey-integration.md)