# ローカル開発環境の起動方法

MySwiftAgentプロジェクトには3つの起動方法があります。この ドキュメントでは、それぞれの使い分けと詳細を説明します。

## 📋 目次

- [3つの起動方法の比較](#3つの起動方法の比較)
- [dev-start.sh（推奨）](#dev-startsh推奨)
- [quick-start.sh](#quick-startsh)
- [docker-compose](#docker-compose)
- [ポート番号一覧](#ポート番号一覧)
- [ベストプラクティス](#ベストプラクティス)
- [トラブルシューティング](#トラブルシューティング)

---

## 3つの起動方法の比較

| 項目 | dev-start.sh | quick-start.sh | docker-compose |
|------|-------------|----------------|----------------|
| **対象** | ローカルプロセス | ローカルプロセス | Dockerコンテナ |
| **ポート** | 8001-8005, 8501 | 8101-8105, 8601 | 8001-8005, 8501 |
| **使用頻度** | ⭐⭐⭐⭐⭐ 日常開発 | ⭐⭐ 特殊ケース | ⭐⭐⭐ 本番検証 |
| **起動速度** | 🚀 高速 | 🚀 高速 | 🐢 遅い（イメージビルド） |
| **リソース消費** | 💚 低 | 💚 低 | 💛 高（コンテナ） |
| **コード変更反映** | ✅ 即座 | ✅ 即座 | ❌ 再ビルド必要 |
| **本番環境近似度** | ❌ 低 | ❌ 低 | ✅ 高 |
| **複数環境同時起動** | ❌ 不可 | ✅ 可能 | ❌ 不可 |

---

## dev-start.sh（推奨）

**最も一般的な開発環境起動方法**です。ローカルマシン上で直接サービスを起動します。

### 基本的な使い方

```bash
# 全サービス起動
./scripts/dev-start.sh start

# 状態確認
./scripts/dev-start.sh status

# ログ確認
./scripts/dev-start.sh logs              # 全サービスのログ
./scripts/dev-start.sh logs myvault      # 特定サービスのログ

# サービス再起動
./scripts/dev-start.sh restart           # 全サービス
./scripts/dev-start.sh restart commonui  # 特定サービス

# 全サービス停止
./scripts/dev-start.sh stop
```

### 利用可能なコマンド

```bash
start       # 全サービス起動（デフォルト）
stop        # 全サービス停止
restart     # 全サービス再起動
status      # 全サービスの状態確認
logs        # ログ表示
test        # 基本APIテスト実行
setup       # 開発環境セットアップのみ
clean       # ログ・PIDファイルクリーンアップ
help        # ヘルプ表示
```

### サービス個別操作

```bash
# 特定サービスのみ操作
./scripts/dev-start.sh start --jobqueue-only
./scripts/dev-start.sh start --myscheduler-only
./scripts/dev-start.sh start --commonui-only

# Docker Composeサービスをスキップ
./scripts/dev-start.sh start --skip-docker
```

### アクセスURL

| サービス | URL | 用途 |
|---------|-----|------|
| JobQueue API | http://localhost:8001 | ジョブキュー管理 |
| MyScheduler API | http://localhost:8002 | ジョブスケジューリング |
| MyVault API | http://localhost:8003 | シークレット管理 |
| ExpertAgent API | http://localhost:8004 | AIエージェント |
| GraphAiServer API | http://localhost:8005 | ワークフロー実行 |
| CommonUI | http://localhost:8501 | Web UI (Streamlit) |
| MyAgentDesk | http://localhost:8000 | Web UI (SvelteKit) |

### 推奨する使用場面

✅ **日常的な開発作業**
```bash
# 朝の起動
./scripts/dev-start.sh start

# コード変更 → 即座に反映
# テスト → デバッグ → 修正のサイクル

# 帰宅時
./scripts/dev-start.sh stop
```

✅ **特定サービスの開発**
```bash
# MyVaultのみ再起動
./scripts/dev-start.sh restart myvault

# ログを監視しながら開発
./scripts/dev-start.sh logs myvault -f
```

✅ **worktree環境での開発**
```bash
cd worktree/feature-issue-123
./scripts/dev-start.sh start

# 別のブランチに切り替え
./scripts/dev-start.sh stop
cd ../feature-issue-124
./scripts/dev-start.sh start
```

---

## quick-start.sh

**docker-composeと並行実行するため**のポート番号を使用するラッパースクリプトです。

### 本質

```bash
# quick-start.sh の実体
export JOBQUEUE_PORT=8101
export MYSCHEDULER_PORT=8102
export MYVAULT_PORT=8103
export EXPERTAGENT_PORT=8104
export GRAPHAISERVER_PORT=8105
export COMMONUI_PORT=8601

./scripts/dev-start.sh start  # 内部で dev-start.sh を呼び出す
```

つまり、`quick-start.sh = 環境変数プリセット + dev-start.sh start`

### 基本的な使い方

```bash
# ワンコマンド起動（全サービス）
./scripts/quick-start.sh
```

### アクセスURL（ポート番号が異なる）

| サービス | URL | dev-start.shとの違い |
|---------|-----|-------------------|
| JobQueue API | http://localhost:8101 | +100 |
| MyScheduler API | http://localhost:8102 | +100 |
| MyVault API | http://localhost:8103 | +100 |
| ExpertAgent API | http://localhost:8104 | +100 |
| GraphAiServer API | http://localhost:8105 | +100 |
| CommonUI | http://localhost:8601 | +100 |

### 推奨する使用場面

✅ **docker-composeと並行実行**
```bash
# Terminal 1: Docker環境
docker-compose up -d
# → ポート 8001-8005, 8501 で起動

# Terminal 2: ローカル開発環境
./scripts/quick-start.sh
# → ポート 8101-8105, 8601 で起動

# 両方にアクセスして動作比較
open http://localhost:8501  # Docker版
open http://localhost:8601  # ローカル版
```

✅ **複数worktreeで同時起動（レアケース）**
```bash
# worktree A
cd worktree/main
./scripts/dev-start.sh start
# → ポート 8001-8005, 8501（修正前）

# worktree B
cd ../worktree/feature-bugfix-123
./scripts/quick-start.sh
# → ポート 8101-8105, 8601（修正後）

# ブラウザで2つのバージョンを比較
```

⚠️ **注意事項**
- quick-start.shで起動したら、停止も同じ環境で行う
- dev-start.shと混在させない（ポート番号が異なるため）
- リソース消費が2倍になるので、必要な時だけ使用

---

## docker-compose

**本番環境に近い構成**でコンテナとして起動します。

### 基本的な使い方

```bash
# 全サービス起動（デタッチモード）
docker-compose up -d

# ログ確認
docker-compose logs -f              # 全サービス
docker-compose logs -f commonui     # 特定サービス

# 状態確認
docker-compose ps

# サービス再起動
docker-compose restart commonui     # 特定サービス

# 全サービス停止・削除
docker-compose down

# イメージ再ビルド
docker-compose build commonui
docker-compose up -d commonui
```

### アクセスURL

| サービス | URL | コンテナ内ポート |
|---------|-----|----------------|
| Valkey | localhost:6380 | 6379 |
| JobQueue API | http://localhost:8001 | 8000 |
| MyScheduler API | http://localhost:8002 | 8000 |
| MyVault API | http://localhost:8003 | 8000 |
| ExpertAgent API | http://localhost:8004 | 8000 |
| GraphAiServer API | http://localhost:8005 | 8000 |
| CommonUI | http://localhost:8501 | 8501 |

### 推奨する使用場面

✅ **本番環境の動作確認**
```bash
# デプロイ前の最終確認
docker-compose up -d
# → コンテナ化された環境でテスト
```

✅ **環境変数・設定ファイルの検証**
```bash
# .env.docker の設定をテスト
docker-compose up -d

# 設定が正しく反映されているか確認
docker-compose exec expertagent env | grep MYVAULT
```

✅ **依存関係の確認**
```bash
# サービス間の通信をテスト
docker-compose up -d
docker-compose logs -f
# → コンテナネットワーク内の通信を確認
```

⚠️ **注意事項**
- コード変更後は `docker-compose build` が必要
- 起動に時間がかかる（イメージビルド）
- dev-start.shと同じポート番号を使用（同時起動不可）
- `commonUI/.streamlit/secrets.toml` はコンテナ内にコピーされる

---

## ポート番号一覧

### ポート番号設計の意図

```
┌─────────────────────────────────────────────────────────────┐
│ ポート番号範囲の使い分け                                           │
├─────────────────────────────────────────────────────────────┤
│ 8001-8005, 8501  → 標準ポート（dev-start.sh, docker-compose） │
│ 8101-8105, 8601  → 回避ポート（quick-start.sh）                 │
└─────────────────────────────────────────────────────────────┘
```

### 完全なポート番号マッピング

| サービス | dev-start.sh | quick-start.sh | docker-compose | 説明 |
|---------|--------------|----------------|----------------|------|
| Valkey | 6379 | - | 6380→6379 | Redisプロトコル |
| JobQueue | 8001 | 8101 | 8001→8000 | ジョブキューAPI |
| MyScheduler | 8002 | 8102 | 8002→8000 | スケジューラーAPI |
| MyVault | 8003 | 8103 | 8003→8000 | シークレット管理API |
| ExpertAgent | 8004 | 8104 | 8004→8000 | AIエージェントAPI |
| GraphAiServer | 8005 | 8105 | 8005→8000 | ワークフローAPI |
| CommonUI | 8501 | 8601 | 8501→8501 | Streamlit UI |
| MyAgentDesk | 8000 | - | - | SvelteKit UI |

---

## ベストプラクティス

### 1. 日常的な開発

**推奨**: dev-start.sh のみ使用

```bash
# 起動
./scripts/dev-start.sh start

# 開発サイクル
while true; do
  # コード編集
  vim app/main.py

  # サービス自動再起動（uvicorn --reload）
  # または手動再起動
  ./scripts/dev-start.sh restart expertagent

  # 動作確認
  open http://localhost:8501
done

# 終了
./scripts/dev-start.sh stop
```

### 2. worktree環境での開発

**推奨**: 1つのworktreeでのみサービス起動

```bash
# worktree A で開発
cd worktree/feature-issue-123
./scripts/dev-start.sh start
# ... 開発作業 ...

# worktree B に切り替え
./scripts/dev-start.sh stop
cd ../feature-issue-124
./scripts/dev-start.sh start
```

### 3. docker-composeとローカル環境の比較

**推奨**: quick-start.sh を使用

```bash
# Docker環境
docker-compose up -d
# → http://localhost:8501

# ローカル環境
./scripts/quick-start.sh
# → http://localhost:8601

# 比較検証
# ブラウザで2つのURLを開いて動作確認
```

### 4. 本番デプロイ前の検証

**推奨**: docker-compose のみ使用

```bash
# 本番環境に近い構成でテスト
docker-compose down
docker-compose build
docker-compose up -d

# ヘルスチェック
docker-compose ps
docker-compose logs -f

# テスト実行
curl http://localhost:8003/health
```

---

## トラブルシューティング

### ❌ エラー: ポート番号が既に使用されている

```
Error: Port 8003 is already in use
```

**原因**: 別のスクリプトまたはdocker-composeが同じポートを使用中

**解決策1**: 既存のサービスを停止

```bash
./scripts/dev-start.sh stop
docker-compose down
```

**解決策2**: quick-start.sh を使用

```bash
./scripts/quick-start.sh  # ポート 8101-8105 を使用
```

### ❌ エラー: MyVault接続失敗

```
Service 'MyVault' is unavailable
```

**原因**: CommonUIが間違ったポート番号を参照

**診断**:
```bash
# どのポートでMyVaultが動作しているか確認
lsof -i :8003  # dev-start.sh
lsof -i :8103  # quick-start.sh

# CommonUIがどのポートを使用しているか確認
ps aux | grep streamlit
# → ポート8501ならdev-start.sh、8601ならquick-start.sh
```

**解決策**: スクリプトを統一

```bash
# 全サービス停止
./scripts/dev-start.sh stop
pkill -f streamlit

# 統一されたスクリプトで再起動
./scripts/dev-start.sh start
```

### ❌ エラー: docker-composeとdev-start.shの混在

**原因**: 異なる起動方法のサービスが同時に動作

**解決策**:
```bash
# 全て停止
./scripts/dev-start.sh stop
docker-compose down

# どちらか一方で起動
./scripts/dev-start.sh start
# または
docker-compose up -d
```

### ⚠️ 警告: secrets.tomlの設定

**問題**: `commonUI/.streamlit/secrets.toml` にDocker専用の設定が書かれている

```toml
# ❌ 間違い: Docker専用のURL
MYVAULT_BASE_URL = "http://myvault:8000"
```

**解決策**: secrets.tomlは環境変数に委譲

```toml
# ✅ 正解: コメントアウトして環境変数に任せる
# MyVault configuration is set via environment variables:
# - Docker environment: MYVAULT_BASE_URL=http://myvault:8000 (in docker-compose.yml)
# - Local environment: MYVAULT_BASE_URL=http://localhost:8003 (in dev-start.sh)
```

---

## 環境変数の優先順位

各起動方法での環境変数の読み込み順序：

### dev-start.sh

```
1. プロジェクト.env ファイル (jobqueue/.env, myVault/.env等)
2. dev-start.sh のデフォルト値
3. 起動スクリプト内で export された値
4. CommonUI: Streamlit secrets.toml → 環境変数の順
```

### quick-start.sh

```
1. プロジェクト.env ファイル
2. quick-start.sh で export された値（優先）
3. dev-start.sh のデフォルト値（上書きされる）
4. CommonUI: Streamlit secrets.toml → 環境変数の順
```

### docker-compose

```
1. .env.docker ファイル
2. docker-compose.yml の environment セクション
3. コンテナ内の secrets.toml（ビルド時にコピー）
```

---

## まとめ

| 状況 | 推奨スクリプト | 理由 |
|------|--------------|------|
| 日常的な開発 | `dev-start.sh` | シンプル、高速、標準ポート |
| worktree環境 | `dev-start.sh` | 1つずつ起動・停止で十分 |
| docker-compose並行実行 | `quick-start.sh` | ポート番号が被らない |
| 本番環境検証 | `docker-compose` | コンテナ化された環境 |
| 動作比較検証 | `quick-start.sh` + `docker-compose` | 両方同時実行可能 |

---

**最終更新**: 2025-12-09
**作成者**: /doc-register コマンド
**関連ドキュメント**:
- [deployment-guide.md](./deployment-guide.md) - デプロイメント手順
- [dev-start-troubleshooting.md](./dev-start-troubleshooting.md) - トラブルシューティング
- [CLAUDE.md](../../CLAUDE.md) - プロジェクト全体ガイド
