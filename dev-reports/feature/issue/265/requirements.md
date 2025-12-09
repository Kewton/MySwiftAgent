# 要件定義書: Issue #265

## Langfuse MinIOバケット自動作成によるトレース永続化の修正

---

## 1. ユーザーストーリー

```
As a 開発者・運用担当者
I want to Langfuse起動時にMinIOバケットが自動作成される
So that 手動設定なしでLLMトレースが永続化され、Langfuse UIで確認できる
```

---

## 2. 受入条件（Acceptance Criteria）

### AC1: バケット自動作成

- **Given**: Docker Composeで初めてLangfuse環境を起動する
- **When**: `docker compose -f docker-compose.platform.yml up -d` を実行
- **Then**: MinIOに`langfuse`バケットが自動作成される

### AC2: S3エラー解消

- **Given**: Langfuseサービスが起動している
- **When**: expertAgentからトレースが送信される
- **Then**: `NoSuchBucket`エラーが発生せず、正常にS3アップロードされる

### AC3: トレース表示

- **Given**: expertAgentでLLM呼び出しを実行済み
- **When**: Langfuse UI (http://localhost:3001) にアクセス
- **Then**: トレースデータが正常に表示される

### AC4: 冪等性

- **Given**: すでに`langfuse`バケットが存在する状態
- **When**: `docker compose down && docker compose up -d` でサービスを再起動
- **Then**: エラーなく起動し、既存バケットが維持される

---

## 3. 機能要件

### 3.1 必須機能（Must Have）

| 機能ID | 機能名           | 説明                                             |
| ------ | ---------------- | ------------------------------------------------ |
| F1     | バケット自動作成 | MinIO起動後に`langfuse`バケットを自動作成        |
| F2     | 依存関係制御     | langfuse-serverがバケット作成完了を待ってから起動 |
| F3     | 冪等性確保       | 既存バケットがある場合はスキップ（エラーにしない） |

### 3.2 あると良い機能（Nice to Have）

| 機能ID | 機能名           | 説明                                               |
| ------ | ---------------- | -------------------------------------------------- |
| N1     | 初期化ログ出力   | バケット作成成功/スキップをログ出力                |
| N2     | 複数バケット対応 | 将来的に複数バケットが必要になった場合の拡張性     |

### 3.3 将来的な拡張（Future Enhancement）

| 機能ID | 機能名             | 説明                                   |
| ------ | ------------------ | -------------------------------------- |
| E1     | バケットポリシー設定 | セキュリティポリシーの自動設定         |
| E2     | ライフサイクル設定   | 古いトレースデータの自動削除ルール     |

---

## 4. 非機能要件

### 4.1 パフォーマンス要件

| 要件       | 基準                                                   |
| ---------- | ------------------------------------------------------ |
| 初期化時間 | MinIO healthcheck通過後、30秒以内にバケット作成完了    |
| 起動順序   | langfuse-server起動前にバケット作成が完了すること      |

### 4.2 信頼性要件

| 要件     | 基準                                   |
| -------- | -------------------------------------- |
| 冪等性   | 複数回実行してもエラーにならない       |
| リトライ | MinIO接続失敗時に適切なリトライを行う  |

### 4.3 運用性要件

| 要件     | 基準                                 |
| -------- | ------------------------------------ |
| ログ出力 | 初期化処理の成功/失敗をログで確認可能 |
| 設定変更 | バケット名を環境変数で変更可能        |

---

## 5. 技術的制約

### 5.1 使用する技術スタック

| 技術                 | バージョン                     | 用途                       |
| -------------------- | ------------------------------ | -------------------------- |
| MinIO                | RELEASE.2025-09-07T16-13-09Z   | オブジェクトストレージ     |
| MinIO Client (mc)    | latest                         | バケット作成CLI            |
| Docker Compose       | v2.x                           | コンテナオーケストレーション |

### 5.2 既存システムとの連携

```
docker-compose.platform.yml
├── langfuse-minio (既存)
├── langfuse-minio-init (新規追加)  ← バケット初期化コンテナ
├── langfuse-worker
│   └── depends_on: langfuse-minio-init
└── langfuse-server
    └── depends_on: langfuse-minio-init
```

### 5.3 環境変数

| 変数名                           | デフォルト値 | 説明                   |
| -------------------------------- | ------------ | ---------------------- |
| `MINIO_ROOT_USER`                | minioadmin   | MinIO管理者ユーザー    |
| `MINIO_ROOT_PASSWORD`            | minioadmin   | MinIO管理者パスワード  |
| `LANGFUSE_S3_EVENT_UPLOAD_BUCKET` | langfuse     | バケット名             |

---

## 6. 実装方針

### 6.1 推奨アプローチ: initコンテナ方式（案1）

```yaml
langfuse-minio-init:
  image: minio/mc
  container_name: myswiftagent-langfuse-minio-init
  depends_on:
    langfuse-minio:
      condition: service_healthy
  entrypoint: >
    /bin/sh -c "
    mc alias set myminio http://langfuse-minio:9000
      $${MINIO_ROOT_USER:-minioadmin} $${MINIO_ROOT_PASSWORD:-minioadmin};
    mc mb --ignore-existing myminio/$${LANGFUSE_S3_BUCKET:-langfuse};
    echo 'Bucket langfuse created or already exists';
    "
  networks:
    - myswiftagent
```

### 6.2 依存関係の更新

```yaml
langfuse-worker:
  depends_on:
    langfuse-minio-init:
      condition: service_completed_successfully  # 追加

langfuse-server:
  depends_on:
    langfuse-minio-init:
      condition: service_completed_successfully  # 追加
```

---

## 7. リスクと対策

| リスク                           | 影響度 | 対策                                               |
| -------------------------------- | ------ | -------------------------------------------------- |
| MinIO接続タイムアウト            | 中     | healthcheckで起動待ちを確保、リトライ処理を追加    |
| initコンテナ失敗時のサービス起動阻害 | 高     | エラーハンドリングとログ出力で原因特定を容易に     |
| 既存環境との互換性               | 低     | `--ignore-existing`フラグで冪等性を確保            |

---

## 8. テスト計画

### 8.1 単体テスト

| テストケース             | 期待結果                       |
| ------------------------ | ------------------------------ |
| 新規環境での起動         | `langfuse`バケットが作成される |
| 既存バケットありでの起動 | エラーなくスキップされる       |

### 8.2 結合テスト

| テストケース                     | 期待結果                     |
| -------------------------------- | ---------------------------- |
| expertAgent → Langfuseトレース送信 | S3エラーなしで永続化         |
| Langfuse UI表示                  | トレースが正常に表示される   |

### 8.3 受入テスト

```bash
# 1. 環境をクリーンアップ
docker compose -f docker-compose.platform.yml down -v

# 2. 環境を起動
docker compose -f docker-compose.platform.yml up -d

# 3. バケット確認
docker exec myswiftagent-langfuse-minio mc ls local/ | grep langfuse

# 4. トレース送信テスト
curl -X POST http://localhost:8004/aiagent-api/v1/test-trace

# 5. Langfuse UI確認
open http://localhost:3001
```

---

## 9. 関連情報

| 項目         | 内容                                       |
| ------------ | ------------------------------------------ |
| 関連Issue    | #135 (MERGED): Langfuse Self-hosted構築    |
| 関連Issue    | #263 (CLOSED): Langfuse CallbackHandlerのmyVault連携 |
| 対象ファイル | `docker-compose.platform.yml`              |
| ラベル       | `bug`                                      |

---

## 10. 見積もり

| 工程         | 内容                               |
| ------------ | ---------------------------------- |
| 実装         | docker-compose.platform.yml修正    |
| テスト       | 単体・結合・受入テスト             |
| ドキュメント | 設計方針書・実装レポート           |
