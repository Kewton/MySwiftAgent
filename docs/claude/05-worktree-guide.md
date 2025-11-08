# 🔄 並列開発環境（git worktree）

## 概要

**git worktree** を使用することで、複数のブランチを同時に開発できます。これにより：

- ✅ ブランチ切り替え時の `git stash` / `git stash pop` が不要
- ✅ 複数の機能を同時並行で開発可能（例: issue/126 と issue/127 を同時に作業）
- ✅ 各worktreeは独立した作業ディレクトリを持つ
- ✅ ポート番号衝突を自動回避
- ✅ 環境変数は一元管理

## 🏗️ ディレクトリ構造

**重要**: worktreeは**MySwiftAgentと同じ親ディレクトリ**に自動配置されます。

```
~/share/work/github_kewton/              # 親ディレクトリ（例）
├── MySwiftAgent/                        # メインworktree (develop ブランチ)
│   ├── .env                             # 共有環境変数（APIキーなど）
│   ├── .git/                            # Gitリポジトリ本体
│   └── scripts/                         # 共有スクリプト
│       ├── setup-worktree.sh            # worktree自動セットアップ
│       ├── worktree-create-from-issue.sh  # Issue番号からworktree作成
│       └── sync-myvault-db.sh           # myVault DB同期
│
└── MySwiftAgent-worktrees/              # worktree専用ディレクトリ（自動作成）
    ├── feature-issue-126/               # worktree 1 (feature/issue/126)
    │   ├── .env -> ../MySwiftAgent/.env  # シンボリックリンク（共有設定）
    │   ├── .env.local                   # worktree固有設定（ポート番号）
    │   ├── myVault/data/myvault.db      # 独立DB（並行起動対応）
    │   ├── expertAgent/
    │   │   ├── .venv/                   # 独立した仮想環境
    │   │   └── logs/                    # worktree固有ログ
    │   └── myAgentDesk/
    │       └── node_modules/            # 独立した依存関係
    └── feature-issue-127/               # worktree 2 (feature/issue/127)
        ├── .env -> ../MySwiftAgent/.env  # シンボリックリンク（共有設定）
        ├── .env.local                   # worktree固有設定（ポート番号）
        └── ...
```

**パス解決の仕組み**:
- `worktree-create-from-issue.sh` は自動的に親ディレクトリを検出
- `WORKTREES_BASE_DIR="$(dirname "$MAIN_REPO")/MySwiftAgent-worktrees"`
- MySwiftAgentがどこにあっても、同じ親ディレクトリにworktreeが作成される

## 🚀 基本操作

### worktreeの作成

**推奨方法: GitHub Issueから自動作成**

```bash
# メインリポジトリから実行
cd ~/MySwiftAgent  # 実際のパスは任意

# Issue番号を指定してworktree自動作成
./scripts/worktree-create-from-issue.sh 142

# 自動的に以下が実行される:
# 1. GitHub IssueからタイトルとラベルFを取得
# 2. ブランチ種別を自動判定 (feature/fix/refactor等)
# 3. 親ディレクトリ/MySwiftAgent-worktrees/ にworktree作成
# 4. setup-worktree.sh で自動セットアップ
```

**手動作成方法（高度なユーザー向け）**

```bash
# メインリポジトリから実行
cd ~/MySwiftAgent  # 実際のパスは任意

# 親ディレクトリ配下のMySwiftAgent-worktreesに作成
git worktree add ../MySwiftAgent-worktrees/feature-issue-126 -b feature/issue/126

# 作成されたworktreeに移動
cd ../MySwiftAgent-worktrees/feature-issue-126

# 自動セットアップスクリプトを実行
../../MySwiftAgent/scripts/setup-worktree.sh
```

### worktree一覧の確認

```bash
git worktree list

# 出力例:
# /Users/user/MySwiftAgent                          abc1234 [develop]
# /Users/user/MySwiftAgent-worktrees/feature-issue-126  def5678 [feature/issue/126]
# /Users/user/MySwiftAgent-worktrees/feature-issue-127  ghi9012 [feature/issue/127]
```

### worktreeの削除

```bash
# 実行中のプロセスを停止
pkill -f "uvicorn.*8114"  # ポート番号に応じて調整

# worktreeを削除（ディレクトリも削除）
cd ~/MySwiftAgent
git worktree remove ../MySwiftAgent-worktrees/feature-issue-126

# 不要なエントリをクリーンアップ
git worktree prune
```

## 🔌 ポート番号管理

### ポート番号の自動割り当て（空きポート検出方式）

各worktreeで異なるポート番号を使用するため、`scripts/setup-worktree.sh` が自動的に空きポートを検出・割り当てします。

#### ポート番号割り当てテーブル

| Worktree | expertAgent | myVault | myscheduler | jobqueue | graphAiServer | myAgentDesk |
|---------|------------|---------|-------------|----------|---------------|-------------|
| **メイン** (0) | 8104 | 8103 | 8102 | 8101 | 8100 | 5173 |
| **Worktree 1** | 8114 | 8113 | 8112 | 8111 | 8110 | 5174 |
| **Worktree 2** | 8124 | 8123 | 8122 | 8121 | 8120 | 5175 |
| **Worktree 3** | 8134 | 8133 | 8132 | 8131 | 8130 | 5176 |

#### 仕組み

1. **自動インデックス検出**: `setup-worktree.sh` が既存worktreeの `.env.local` をスキャン
2. **空きポート計算**: 使用中のインデックスを除外し、最小の空きインデックスを割り当て
3. **ポート番号計算**: `ベースポート + (インデックス × 10)`
4. **永続化**: `.env.local` にインデックスを記録（worktree削除後も他のworktreeに影響なし）

**重要**: worktreeを削除しても、既存worktreeのポート番号は変わりません。削除されたインデックスは次回の新規作成時に再利用されます。

## 🔐 環境変数・設定の共有

### 共有設定と固有設定の分離

| 設定種別 | 配置場所 | 共有方法 | 用途 |
|---------|---------|---------|------|
| **共有設定** | `~/MySwiftAgent/.env` | シンボリックリンク | APIキー、データベース接続情報など |
| **固有設定** | `各worktree/.env.local` | 各worktree独自 | ポート番号、ログディレクトリなど |

### 環境変数の読み込み順序

Pythonプロジェクト（FastAPI等）は以下の順序で環境変数を読み込みます：

1. `.env` (共有設定)
2. `.env.local` (固有設定) ← **優先**

```python
# app/core/config.py の実装例
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    class Config:
        env_file = [".env", ".env.local"]  # .env.local が優先
        env_file_encoding = "utf-8"
```

## myVault / langfuse の柔軟な配置戦略

**テスト環境構築効率化のため、myVaultとlangfuseを複数worktreeから共有可能にしつつ、別端末での環境構築も確実に動作させます。**

### 配置パターン（3種類）

`scripts/setup-worktree.sh` 実行時に、myVaultとlangfuseの両方について以下3パターンから選択できます：

| パターン | 配置方法 | メリット | デメリット | 推奨ユースケース |
|---------|---------|---------|----------|-----------------|
| **1. 共有 (develop)** | `../../MySwiftAgent/{myVault,langfuse}` へのシンボリックリンク | ✅ リソース効率的<br>✅ データ共有可能<br>✅ ポート競合なし | ⚠️ developブランチ依存 | **開発効率重視**<br>複数worktreeで同じデータを参照 |
| **2. 独立 (PWD)** | カレントworktree内に実ディレクトリ配置 | ✅ 完全に独立した環境<br>✅ 安全性が高い<br>✅ 別端末でも動作 | ⚠️ リソース消費増<br>⚠️ ポート管理必要 | **複数worktreeで並行テスト**<br>**CI/CD環境**<br>**別端末での初回セットアップ** |
| **3. カスタム** | 任意のパスへのシンボリックリンク | ✅ 柔軟性が高い<br>✅ 複数worktreeで共有可能 | ⚠️ 手動管理が必要 | **特定worktree間のみ共有** |

### セットアップフロー

```bash
# 1. worktree作成
git worktree add ../MySwiftAgent-worktrees/feature-issue-126 -b feature/issue/126
cd ../MySwiftAgent-worktrees/feature-issue-126

# 2. セットアップスクリプト実行（対話的に選択）
~/MySwiftAgent/scripts/setup-worktree.sh

# 🔐 myVault Directory Setup
# Select myVault directory placement:
#   1) Share with develop branch (symlink to ~/MySwiftAgent/myVault)
#   2) Independent copy in current worktree (PWD/myVault)
#   3) Custom path (manual input)
# Enter choice [1-3] (default: 1): 1  ← 開発効率重視の場合

# 🔍 Langfuse Directory Setup
# Select Langfuse directory placement:
#   1) Share with develop branch (symlink to ~/MySwiftAgent/langfuse)
#   2) Independent copy in current worktree (PWD/langfuse)
#   3) Custom path (manual input)
# Enter choice [1-3] (default: 1): 1  ← リソース効率重視の場合
```

### 各パターンの詳細

**パターン1: 共有モード（デフォルト推奨）**
```bash
# ディレクトリ構造
feature-issue-126/
├── myVault -> ~/MySwiftAgent/myVault      # シンボリックリンク
├── langfuse -> ~/MySwiftAgent/langfuse    # シンボリックリンク
└── .env.local                             # ポート番号は共有元に従う

# メリット
# - developブランチと同じmyVault DBを参照
# - Langfuse Docker環境を共有（1インスタンスのみ起動）
# - ディスク容量節約
```

**パターン2: 独立モード（並行テスト推奨）**
```bash
# ディレクトリ構造
feature-issue-126/
├── myVault/                               # 実ディレクトリ
│   └── data/myvault.db                   # 独立DB（WALモード有効）
├── langfuse/                              # 実ディレクトリ
│   ├── .env.example                      # 設定ファイル
│   └── docker-compose.langfuse.yml       # Docker Compose設定
└── .env.local                             # worktree固有ポート番号

# メリット
# - 完全に独立した環境（他worktreeに影響なし）
# - 別端末でクローンしても即座に利用可能
# - 並行テストに最適

# セットアップ（独立モード選択時）
cd myVault
cp .env.example .env  # 初回のみ
uv run uvicorn app.main:app --reload --port 8113  # worktree固有ポート

cd langfuse
cp .env.example .env  # 初回のみ
docker compose -f docker-compose.langfuse.yml --env-file .env up -d
```

**パターン3: カスタムモード（柔軟性重視）**
```bash
# 例: 複数worktreeで共有するが、developブランチとは分離
mkdir -p ~/MySwiftAgent-shared/myVault
mkdir -p ~/MySwiftAgent-shared/langfuse

# setup-worktree.sh でカスタムパスを指定
# Enter custom myVault path: ~/MySwiftAgent-shared/myVault
# Enter custom langfuse path: ~/MySwiftAgent-shared/langfuse
```

### DB同期（独立モード時）

独立モード選択時、myVault DBは自動的にdevelopブランチからコピーされます。重要なシークレット追加後に同期が必要な場合：

```bash
# 全worktreeのmyVault DBを最新版に同期
~/MySwiftAgent/scripts/sync-myvault-db.sh
```

### 別端末での環境構築

**重要**: langfuse設定ファイルがgit管理されているため、別端末でも即座に利用可能です。

```bash
# 別端末でクローン
git clone https://github.com/your-org/MySwiftAgent.git
cd MySwiftAgent

# langfuse/.env.example から .env を作成
cd langfuse
cp .env.example .env

# Docker起動
docker compose -f docker-compose.langfuse.yml --env-file .env up -d
```

## 📋 worktree作業時のチェックリスト

### worktree作成時

- [ ] `git worktree add` でworktreeを作成
- [ ] `scripts/setup-worktree.sh` を実行（myVault/langfuseの配置パターンを選択）
- [ ] 各プロジェクトで `uv sync` / `npm install` を実行
- [ ] `.env.local` でポート番号が正しく設定されているか確認
- [ ] 独立モードの場合、`langfuse/.env` を作成してDocker起動
- [ ] 開発サーバーを起動して、ポート衝突がないか確認

### worktree削除時

- [ ] 実行中のプロセスをすべて停止（`pkill -f uvicorn`, `pkill -f vite` など）
- [ ] `git worktree remove` でworktreeを削除
- [ ] `git worktree prune` で不要なエントリをクリーンアップ

### 開発時の注意事項

- ✅ 各worktreeは**独立したブランチ**を持つため、同じブランチを複数worktreeで開くことはできません
- ✅ `.git` ディレクトリはメインworktreeのみに存在し、他のworktreeは参照のみ
- ✅ `git fetch`, `git pull` はどのworktreeからでも実行可能
- ✅ `git push` は各worktreeで独立して実行
- ✅ myVault/langfuseは配置戦略に応じて**共有モード/独立モード**を選択可能
  - 共有モード: リソース効率的、developブランチと同じDBを参照
  - 独立モード: 完全に独立した環境、WALモード有効化済み
- ❌ 大容量ファイル（node_modules, .venv, ログファイル等）はworktree毎に生成されるため、ディスク容量に注意
- ❌ 推奨最大worktree数: 3-4個（ディスク容量とパフォーマンスのバランス）
  - 独立モード選択時は特にディスク容量に注意（Langfuse Dockerボリュームが大きい）

## 🛠️ 便利コマンド

### 全worktreeのブランチ状況を確認

```bash
git worktree list
```

### myVault DBを全worktreeに同期

```bash
# メインworktreeのmyVault DBを全worktreeにコピー
~/MySwiftAgent/scripts/sync-myvault-db.sh
```

### 特定のworktreeでコマンドを実行

```bash
# worktree 1でテスト実行
cd ~/MySwiftAgent-worktrees/feature-issue-126/expertAgent
uv run pytest

# worktree 2で開発サーバー起動
cd ~/MySwiftAgent-worktrees/feature-issue-127/expertAgent
uv run uvicorn app.main:app --reload
```

### 全worktreeで並列作業

```bash
# 実際のパスは環境により異なります
# 例: ~/share/work/github_kewton/ 配下の場合

# ターミナル1: メインworktree (develop)
cd ~/share/work/github_kewton/MySwiftAgent

# ターミナル2: worktree 1 (feature/issue/126)
cd ~/share/work/github_kewton/MySwiftAgent-worktrees/feature-issue-126

# ターミナル3: worktree 2 (feature/issue/127)
cd ~/share/work/github_kewton/MySwiftAgent-worktrees/feature-issue-127
```

## 📚 詳細ドキュメント

並列開発の詳細なワークフローについては、[並列開発ワークフロー](../workflows/parallel-development.md) を参照してください。

---

[← 品質基準](./04-quality-standards.md) | [CLAUDE.md](../../CLAUDE.md) | [次: CI/CDエラー防止 →](./06-ci-cd-prevention.md)