# MySwiftAgent Scripts

🚀 **統合開発環境管理スクリプト集**

JobQueue、MyScheduler、CommonUIの3つのサービスを統合的に管理するためのシェルスクリプトです。

## 📁 スクリプト一覧

| スクリプト | 用途 | 概要 |
|-----------|------|------|
| `quick-start.sh` | **🚀 クイック起動** | 一発で全サービス起動 |
| `dev-start.sh` | **🔧 開発環境管理** | 包括的なサービス管理 |
| `health-check.sh` | **🔍 ヘルスチェック** | サービス監視・診断 |
| `start_services.sh` | **⚙️ 基本管理** | シンプルなサービス制御 |
| `restart-myvault.sh` | **🔐 MyVault再起動** | MyVault設定リロード |

## 🚀 クイックスタート

### 即座に起動
```bash
# すべてのサービスを一発起動
./scripts/quick-start.sh
```

> ℹ️ `quick-start.sh` では Docker Compose と並行稼働できるように、デフォルトで `8101-8104` / `8601` の代替ポートを使用します。必要に応じて `JOBQUEUE_PORT=8111 ./scripts/quick-start.sh` のように環境変数で上書きできます。

### 開発用包括管理
```bash
# 全サービス起動（依存関係自動解決）
./scripts/dev-start.sh

# 個別サービス起動
./scripts/dev-start.sh start --jobqueue-only
./scripts/dev-start.sh start --commonui-only

# サービス停止
./scripts/dev-start.sh stop

# ステータス確認
./scripts/dev-start.sh status

# ログ確認
./scripts/dev-start.sh logs
./scripts/dev-start.sh logs jobqueue
```

## 🔍 ヘルスチェック・監視

### 基本ヘルスチェック
```bash
# 全サービスの健康状態確認
./scripts/health-check.sh

# 継続監視（10秒間隔）
./scripts/health-check.sh monitor

# 高頻度監視（3秒間隔）
./scripts/health-check.sh monitor --interval 3
```

### 統合テスト
```bash
# API連携テスト実行
./scripts/health-check.sh test

# システム情報表示
./scripts/health-check.sh info
```

## 📊 サービス構成

### ポート構成
- **🚢 Docker Compose 標準ポート**
    - 🎨 CommonUI (Streamlit): `http://localhost:8501`
    - 📋 JobQueue API: `http://localhost:8101`
    - ⏰ MyScheduler API: `http://localhost:8102`
    - 🤖 ExpertAgent API: `http://localhost:8003`
    - 🔄 GraphAiServer API: `http://localhost:8004`
    - 🔐 MyVault API: `http://localhost:8000`
- **🖥️ `quick-start.sh` / `dev-start.sh` 開発用ポート**
    - 🎨 CommonUI (Streamlit): `http://localhost:8501`
    - 📋 JobQueue API: `http://localhost:8101`
    - ⏰ MyScheduler API: `http://localhost:8102`
    - 🤖 ExpertAgent API: `http://localhost:8103`
    - 🔄 GraphAiServer API: `http://localhost:8104`
    - 🔐 MyVault API: `http://localhost:8000`

### サービス依存関係
```
CommonUI (Frontend)
    ├── JobQueue API (Backend)
    ├── MyScheduler API (Backend)
    ├── ExpertAgent API (AI Agent)
    ├── GraphAiServer API (Workflow Engine)
    └── MyVault API (Secret Management)

JobQueue
    └── ExpertAgent API (Job execution target)

MyVault (Secret Management)
    └── 独立サービス（他サービスから呼び出される）
```

## ⚙️ 高度な機能

### 環境自動設定
```bash
# 開発環境セットアップのみ実行
./scripts/dev-start.sh setup

# 依存関係一括インストール
./scripts/dev-start.sh setup --jobqueue-only
```

### ログ管理
```bash
# 全ログ確認
./scripts/dev-start.sh logs

# サービス別ログ監視
./scripts/dev-start.sh logs myscheduler

# セットアップログ確認
./scripts/dev-start.sh logs setup
```

### 開発用トークン
開発環境では自動生成されるAPIトークンを使用：
```bash
# トークン確認
cat logs/dev_tokens.txt
```

### クリーンアップ
```bash
# 一時ファイル・ログ・PIDファイル削除
./scripts/dev-start.sh clean
```

## 🔧 トラブルシューティング

### よくある問題

**1. ポートが既に使用中**
```bash
# ポート使用状況確認（標準・代替ポート両方をチェック）
lsof -i :8501 -i :8601 -i :8001 -i :8002 -i :8003 -i :8004 -i :8101 -i :8102 -i :8103 -i :8104

# 強制終了後に再起動
./scripts/dev-start.sh stop
./scripts/dev-start.sh start
```

**2. 依存関係エラー**
```bash
# 依存関係を再インストール
./scripts/dev-start.sh setup
```

**3. サービス起動失敗**
```bash
# 詳細エラー確認
./scripts/dev-start.sh logs
./scripts/health-check.sh

# 個別起動でデバッグ
./scripts/dev-start.sh start --jobqueue-only
```

### ログファイル場所
```
/tmp/  (quick-start.sh / dev-start.sh)
├── jobqueue.log      # JobQueue API ログ
├── myscheduler.log   # MyScheduler API ログ
├── expertagent.log   # ExpertAgent API ログ
├── graphaiserver.log # GraphAiServer API ログ
├── commonui.log      # CommonUI ログ
└── setup.log         # セットアップログ

docker-compose-data/  (docker-compose)
├── jobqueue/         # JobQueue データ・ログ
├── myscheduler/      # MyScheduler データ・ログ
├── expertagent/logs/ # ExpertAgent ログ
├── graphaiserver/    # GraphAiServer データ・ログ
└── commonUI/         # CommonUI データ
```

### PIDファイル場所
```
.pids/  (quick-start.sh / dev-start.sh)
├── jobqueue.pid      # JobQueue プロセスID
├── myscheduler.pid   # MyScheduler プロセスID
├── expertagent.pid   # ExpertAgent プロセスID
├── graphaiserver.pid # GraphAiServer プロセスID
└── commonui.pid      # CommonUI プロセスID
```

## 🎯 使用例

### 通常の開発フロー
```bash
# 1. プロジェクト起動
./scripts/quick-start.sh

# 2. ブラウザで CommonUI にアクセス
open http://localhost:8501

# 3. 開発作業...

# 4. ヘルスチェック
./scripts/health-check.sh

# 5. ログ確認
./scripts/dev-start.sh logs commonui

# 6. 終了
./scripts/dev-start.sh stop
```

### デバッグフロー
```bash
# 1. 個別サービス起動でデバッグ
./scripts/dev-start.sh start --jobqueue-only

# 2. ログ監視
./scripts/dev-start.sh logs jobqueue

# 3. 問題解決後、全サービス起動
./scripts/dev-start.sh start
```

### 継続監視
```bash
# バックグラウンドでヘルス監視
./scripts/health-check.sh monitor --interval 30 > monitoring.log 2>&1 &
```

### MyVault管理
```bash
# MyVault再起動（設定変更時など）
./scripts/restart-myvault.sh

# MyVault起動
./scripts/restart-myvault.sh start

# MyVault停止
./scripts/restart-myvault.sh stop

# MyVaultステータス確認
./scripts/restart-myvault.sh status

# MyVaultログ確認
./scripts/restart-myvault.sh logs

# MyVaultログ監視
./scripts/restart-myvault.sh logs -f
```

> 💡 `restart-myvault.sh` は、config.yaml や .env の変更後に MyVault サービスを再起動して設定をリロードする際に使用します。

## 🔗 関連リンク

- [JobQueue プロジェクト](../jobqueue/README.md)
- [MyScheduler プロジェクト](../myscheduler/README.md)
- [ExpertAgent プロジェクト](../expertAgent/README.md)
- [GraphAiServer プロジェクト](../graphAiServer/README.md)
- [CommonUI プロジェクト](../commonUI/README.md)
- [MyVault プロジェクト](../myVault/README.md)
- [プロジェクト全体ドキュメント](../README.md)

---

**💡 Tips**:
- `dev-start.sh` は最も包括的な管理スクリプトです
- `quick-start.sh` は初回体験や簡単な起動に最適です
- `health-check.sh` は本番運用でのモニタリングにも使用できます