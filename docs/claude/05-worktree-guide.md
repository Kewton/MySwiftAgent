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
| **1. データ共有** | **データディレクトリのみ**シンボリックリンク<br>`myVault/data -> ../MySwiftAgent/myVault/data`<br>アプリコードは実ディレクトリ | ✅ データ共有可能<br>✅ git管理の問題なし<br>✅ アプリコード独立 | - | **開発効率重視（推奨）**<br>複数worktreeで同じDBを参照 |
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
#   1) Share data with develop branch (symlink myVault/data only)
#   2) Independent copy in current worktree (PWD/myVault)
#   3) Custom path (manual input)
# Enter choice [1-3] (default: 1): 1  ← データ共有＋アプリコード独立（推奨）

# 🔍 Langfuse Directory Setup
# Select Langfuse directory placement:
#   1) Share data with develop branch (symlink langfuse/data only)
#   2) Independent copy in current worktree (PWD/langfuse)
#   3) Custom path (manual input)
# Enter choice [1-3] (default: 1): 1  ← データ共有＋設定ファイル独立（推奨）
```

### 各パターンの詳細

**パターン1: データ共有モード（デフォルト推奨）**
```bash
# ディレクトリ構造
feature-issue-126/
├── myVault/                               # 実ディレクトリ
│   ├── app/                               # アプリコード（git管理）
│   ├── tests/                             # テストコード（git管理）
│   ├── pyproject.toml                     # 依存関係（git管理）
│   └── data -> ~/MySwiftAgent/myVault/data  # データのみシンボリックリンク
├── langfuse/                              # 実ディレクトリ
│   ├── docker-compose.yml                 # 設定ファイル（git管理）
│   ├── .env.example                       # 設定例（git管理）
│   └── data -> ~/MySwiftAgent/langfuse/data # データのみシンボリックリンク
└── .env.local                             # worktree固有設定

# メリット
# - developブランチと同じデータ（DB、Docker volumes）を参照
# - アプリケーションコードは独立（git管理の問題なし）
# - ディスク容量節約
# - git statusに「削除」が表示されない
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

## 🔧 worktree管理モジュール（Issue #144）

### モジュール構成

worktree管理機能は、再利用可能なモジュールとして実装されています：

```
scripts/unified-lib/
├── worktree-utils.sh    # worktree検出・管理
└── port-manager.sh      # ポート計算・衝突検出
```

### worktree-utils.sh

**主な機能**:
- worktree自動検出
- メインリポジトリパス取得
- worktreeインデックス管理
- 使用中インデックスの追跡

**主な関数**:
```bash
get_main_repo_path              # メインリポジトリのパスを取得
is_worktree                     # 現在がworktreeかどうか判定
get_worktree_name               # worktree名を取得
list_all_worktrees              # 全worktreeのリスト取得
get_used_worktree_indices       # 使用中のインデックス取得
find_available_worktree_index   # 利用可能なインデックスを検索
get_current_worktree_index      # 現在のworktreeインデックス取得
get_worktree_info               # worktree情報サマリ取得
count_worktrees                 # worktree数をカウント
```

**使用例**:
```bash
source scripts/unified-lib/worktree-utils.sh

# worktreeかどうか確認
if is_worktree; then
    echo "This is a worktree"
    echo "Index: $(get_current_worktree_index)"
    echo "Main repo: $(get_main_repo_path)"
fi

# 利用可能なインデックスを取得
next_index=$(find_available_worktree_index)
echo "Next available index: $next_index"
```

### port-manager.sh

**主な機能**:
- サービスごとのポート番号計算
- ポート使用状況確認
- 空きポート検出
- ポート競合チェック

**ポート計算アルゴリズム**:
```
ポート番号 = ベースポート + (worktreeインデックス × 10)

例: expertagent (index=1)
    8104 + (1 × 10) = 8114
```

**主な関数**:
```bash
calculate_port service_name index    # ポート番号を計算
is_port_in_use port                  # ポートが使用中か確認
find_available_port start_port       # 空きポートを検索
get_all_ports_for_index index        # 全サービスのポート一覧
check_port_conflicts index           # ポート競合チェック
suggest_alternative_port service port # 代替ポート提案
get_port_status_summary              # ポート状態サマリ
```

**デフォルトベースポート**:
```bash
expertagent:  8104
myvault:      8103
myscheduler:  8102
jobqueue:     8101
graphai:      8100
vite:         5173  # +1 ずつ増加（特殊ケース）
```

**使用例**:
```bash
source scripts/unified-lib/port-manager.sh

# ポート番号を計算
port=$(calculate_port expertagent 2)
echo "ExpertAgent port for index 2: $port"  # 8124

# ポート使用確認
if is_port_in_use 8104; then
    echo "Port 8104 is in use"
    alternative=$(find_available_port 8104)
    echo "Use alternative port: $alternative"
fi

# ポート状態サマリを表示
get_port_status_summary
```

### unified-start.sh との統合

`unified-start.sh status` コマンドは、worktree環境で以下の情報を自動表示：

```bash
./scripts/unified-start.sh status

# 出力例:
╔══════════════════════════════════════════════════════════════════════╗
║                    Worktree Information                           ║
╚══════════════════════════════════════════════════════════════════════╝

  Worktree Name:    feature-issue-144
  Worktree Index:   6
  Main Repository:  /Users/user/MySwiftAgent

╔══════════════════════════════════════════════════════════════════════╗
║                    Port Assignments                              ║
╚══════════════════════════════════════════════════════════════════════╝

Port Status for Worktree Index: 6
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  expertagent     : 8164   (Available)
  myvault         : 8163   (Available)
  myscheduler     : 8162   (Available)
  jobqueue        : 8161   (Available)
  graphai         : 8160   (Available)
  vite            : 5179   (Available)
```

### テスト

モジュールの品質は、包括的なテストスイートで保証されています：

```bash
# worktree-utilsのテスト（28テスト、100%パス）
./tests/scripts/test_worktree_utils.sh

# port-managerのテスト（55テスト、100%パス）
./tests/scripts/test_port_manager.sh
```

**テスト項目**:
- 関数の存在確認
- worktree検出の正確性
- インデックス計算の正確性
- ポート計算の正確性（複数インデックス）
- ポート衝突検出
- エラーハンドリング（不正な入力）
- エッジケース（非worktree環境、使用済みポート等）

### 技術仕様

**対応環境**:
- macOS (lsof使用)
- Linux (lsof/netstat使用)
- Bash 3.2+互換

**安全性**:
- 入力値の厳密な検証
- エラーハンドリング
- 後方互換性の保証
- 非worktree環境でも正常動作

---

## 📚 詳細ドキュメント

並列開発の詳細なワークフローについては、[並列開発ワークフロー](../workflows/parallel-development.md) を参照してください。

---

[← 品質基準](./04-quality-standards.md) | [CLAUDE.md](../../CLAUDE.md) | [次: CI/CDエラー防止 →](./06-ci-cd-prevention.md)