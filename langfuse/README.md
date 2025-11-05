# Langfuse Self-hosted v3

expertAgent統合用のLangfuse Self-hosted v3環境です。

## 📋 セットアップ手順

### 1. 環境変数の設定

`.env.example` を `.env` にコピーして、必要に応じて編集：

```bash
cd langfuse
cp .env.example .env
# 必要に応じて .env を編集（本番環境ではパスワード変更推奨）
```

### 2. Docker Compose起動

```bash
docker compose -f docker-compose.langfuse.yml --env-file .env up -d
```

### 3. 初回セットアップの確認

Langfuseは自動初期化機能（Headless Initialization）により、初回起動時に以下を自動作成します：

- 組織: `expertAgent`
- プロジェクト: `expertAgent-traces`
- 管理者ユーザー: `admin@example.com`
- APIキー: `.env.example` に記載

### 4. アクセス確認

- **Langfuse Web UI**: http://localhost:3001
- **MinIO Console**: http://localhost:9001

## 🔧 設定のカスタマイズ

### ポート番号の変更（worktree環境）

worktree環境では、`.env.local` でポート番号をオーバーライドできます：

```bash
# .env.local
LANGFUSE_PORT=3011
LANGFUSE_DB_PORT=5443
CLICKHOUSE_HTTP_PORT=8133
REDIS_PORT=6389
MINIO_PORT=9012
```

### APIキーの取得

1. Web UI (http://localhost:3001) にログイン
2. プロジェクト設定から Public Key / Secret Key を確認
3. expertAgent の環境変数に設定：

```bash
# .env または myVault
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3001
```

## 🗂️ ディレクトリ構造

```
langfuse/
├── .env.example                    # 環境変数テンプレート
├── .env                            # 環境変数（ユーザー作成、git管理外）
├── docker-compose.langfuse.yml     # Docker Compose設定
├── README.md                       # このファイル
├── docker-compose-data/            # Dockerボリュームデータ（git管理外）
└── data/                           # 追加データ（git管理外）
```

## 🔄 worktree環境での共有

worktree環境では、`scripts/setup-worktree.sh` で以下のいずれかを選択できます：

1. **共有モード**: developブランチのlangfuseディレクトリへのシンボリックリンク
   - メリット: リソース効率的、データ共有可能
   - デメリット: developブランチ依存

2. **独立モード**: 各worktreeで独立したlangfuseインスタンス
   - メリット: 完全に独立した環境
   - デメリット: リソース消費増

3. **カスタムモード**: 任意のパスを手動指定
   - メリット: 柔軟性が高い
   - デメリット: 手動管理が必要

## 🛠️ トラブルシューティング

### コンテナが起動しない

```bash
# ログ確認
docker compose -f docker-compose.langfuse.yml logs

# 再起動
docker compose -f docker-compose.langfuse.yml down
docker compose -f docker-compose.langfuse.yml up -d
```

### ポート競合

別のworktreeやサービスでポートが使用されている場合、`.env` でポート番号を変更してください。

### データベースのリセット

```bash
docker compose -f docker-compose.langfuse.yml down -v
docker compose -f docker-compose.langfuse.yml up -d
```

## 📚 参考資料

- [Langfuse公式ドキュメント](https://langfuse.com/docs)
- [Self-hosting Guide](https://langfuse.com/docs/deployment/self-host)
- [expertAgent統合ガイド](../expertAgent/docs/langfuse-integration.md)
