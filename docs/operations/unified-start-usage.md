# Unified Start Script - 使用方法

**バージョン**: 1.0.0
**作成日**: 2025-11-07
**対象**: Issue #141 - 基本統一起動スクリプトの実装

---

## 概要

`unified-start.sh` は、MySwiftAgentの全マイクロサービス（7サービス）を単一コマンドで起動・停止・再起動できる統一起動スクリプトです。

### 主な機能

- 全サービスの一括起動・停止・再起動
- 依存関係に基づく起動順序制御
- サービス状態の確認
- カラフルなログ出力
- PIDファイルによるプロセス管理

---

## 前提条件

### 必須ツール

- **uv**: Python package manager
  - インストール: https://docs.astral.sh/uv/
- **npm**: Node.js package manager (v18以上)
- **curl**: ヘルスチェック用

### 依存関係のインストール

**初回実行前に各サービスの依存関係をインストールしてください：**

#### Python サービス（uv使用）
```bash
# myVault
cd myVault && uv sync --extra dev

# jobqueue
cd jobqueue && uv sync --extra dev

# myscheduler
cd myscheduler && uv sync --extra dev

# expertAgent
cd expertAgent && uv sync --extra dev

# commonUI
cd commonUI && uv sync --extra dev
```

#### Node.js サービス（npm使用）
```bash
# graphAiServer
cd graphAiServer && npm install

# myAgentDesk
cd myAgentDesk && npm install
```

**注意**: 依存関係がインストールされていない場合、サービスの起動に失敗します。

### 対応OS

- macOS (Bash 3.2以上)
- Linux (Bash 3.2以上)

### 権限要件

- ポート8001-8005、5173、8501へのbind権限
- ログディレクトリへの書き込み権限
- `/tmp/myswiftagent/`への書き込み権限

### 環境変数要件

各サービスのプロジェクトディレクトリに`.env`ファイルが必要です：

**myVault** (必須):
```bash
# myVault/.env
MSA_MASTER_KEY=base64:your_generated_key_here
```

マスターキーの生成方法：
```bash
python -c "import secrets, base64; print('base64:' + base64.b64encode(secrets.token_bytes(32)).decode())"
```

**その他のサービス**:
各サービスの`.env.example`を参照して`.env`ファイルを作成してください。

---

## インストール

スクリプトは既にリポジトリに含まれています。実行権限を確認してください：

```bash
chmod +x scripts/unified-start.sh
chmod +x scripts/unified-lib/common.sh
chmod +x scripts/unified-lib/process-manager.sh
```

---

## 基本的な使用方法

### ヘルプの表示

```bash
./scripts/unified-start.sh --help
```

### 全サービスの起動

```bash
./scripts/unified-start.sh start
```

**起動順序**:
1. Layer 1 (Infrastructure): myVault, jobqueue
2. Layer 2 (Middleware): myscheduler, graphAiServer
3. Layer 3 (Application): expertAgent, myAgentDesk, commonUI

各レイヤー間で3秒の待機時間があります。

### サービス状態の確認

```bash
./scripts/unified-start.sh status
```

**出力例**:
```
[STEP] Checking service status...

  myvault: Running (PID: 12345, Port: 8003)
  jobqueue: Running (PID: 12346, Port: 8001)
  myscheduler: Running (PID: 12347, Port: 8002)
  ...

Summary: 7 running, 0 stopped
```

### 全サービスの停止

```bash
./scripts/unified-start.sh stop
```

サービスは逆順（Layer 3 → Layer 2 → Layer 1）で停止されます。

### 全サービスの再起動

```bash
./scripts/unified-start.sh restart
```

内部的に `stop` → `start` を実行します。

---

## サービス一覧

| サービス名 | ポート | 役割 | レイヤー |
|-----------|--------|------|---------|
| myVault | 8003 | シークレット管理 | Infrastructure |
| jobqueue | 8001 | ジョブキュー管理 | Infrastructure |
| myscheduler | 8002 | ジョブスケジューリング | Middleware |
| graphAiServer | 8005 | ワークフロー実行 | Middleware |
| expertAgent | 8004 | AIエージェント | Application |
| myAgentDesk | 5173 | Web UI | Application |
| commonUI | 8501 | 共通UIコンポーネント | Application |

---

## ファイル配置

### PIDファイル

```
/tmp/myswiftagent/
├── myvault.pid
├── jobqueue.pid
├── myscheduler.pid
├── graphaiserver.pid
├── expertagent.pid
├── myagentdesk.pid
└── commonui.pid
```

### ログファイル

```
logs/
├── myvault.log
├── jobqueue.log
├── myscheduler.log
├── graphaiserver.log
├── expertagent.log
├── myagentdesk.log
└── commonui.log
```

---

## トラブルシューティング

### サービスが起動しない

**原因1: 環境変数が未設定**

myVaultが起動しない場合、`MSA_MASTER_KEY`が未設定の可能性があります：

```bash
# ログを確認
tail -50 logs/myvault.log

# エラーメッセージ例
# ValidationError: MSA_MASTER_KEY environment variable is required
```

**解決方法**:
```bash
# myVault/.envを作成
cd myVault
cp .env.example .env

# マスターキーを生成して設定
python -c "import secrets, base64; print('base64:' + base64.b64encode(secrets.token_bytes(32)).decode())"
# 生成されたキーをmyVault/.envのMSA_MASTER_KEYに設定
```

**原因2: 依存関係が未インストール**

graphAiServerやmyAgentDeskが起動しない場合、npm依存関係が未インストールの可能性があります：

```bash
# ログを確認
tail -30 logs/graphaiserver.log

# エラーメッセージ例
# sh: ts-node: command not found
# sh: vite: command not found
```

**解決方法**:
```bash
# 各Node.jsサービスで依存関係をインストール
cd graphAiServer && npm install
cd ../myAgentDesk && npm install
```

Pythonサービスの場合：
```bash
# 各Pythonサービスで依存関係をインストール
cd myVault && uv sync --extra dev
cd ../jobqueue && uv sync --extra dev
# 他のサービスも同様に
```

**原因3: 依存ツールが不足**

```bash
# uvがインストールされているか確認
uv --version

# npmがインストールされているか確認
npm --version
```

**原因4: ポートが既に使用されている**

```bash
# ポート使用状況を確認
lsof -i :8001  # jobqueueのポート例
```

スクリプトは自動的にポートを解放しようとしますが、手動で停止する必要がある場合もあります。

**原因3: サービスディレクトリが存在しない**

```bash
# プロジェクトルートで実行していることを確認
ls -la myVault jobqueue myscheduler
```

### ログの確認

サービス起動に失敗した場合、各サービスのログファイルを確認してください：

```bash
# 最新のログを表示
tail -n 50 logs/myvault.log
tail -n 50 logs/jobqueue.log
```

### PIDファイルが残っている

サービスが異常終了した場合、古いPIDファイルが残ることがあります：

```bash
# PIDファイルを手動削除
rm /tmp/myswiftagent/*.pid

# その後、再度起動
./scripts/unified-start.sh start
```

### 既存のdev-start.shとの競合

`dev-start.sh` と `unified-start.sh` は異なるPIDディレクトリを使用しているため、基本的には競合しません：

- `dev-start.sh`: `PROJECT_ROOT/.pids/`
- `unified-start.sh`: `/tmp/myswiftagent/`

ただし、ポート番号は同じため、同時に使用することはできません。

---

## 既存スクリプトとの違い

| 項目 | dev-start.sh | unified-start.sh |
|------|--------------|------------------|
| サービス定義 | スクリプト内に散在 | 構造化された配列定義 |
| ライブラリ構造 | なし | モジュール化（lib/） |
| PIDファイル | `.pids/` | `/tmp/myswiftagent/` |
| 起動順序制御 | 手動 | レイヤー別自動制御 |
| Bash互換性 | Bash 4.0+ | Bash 3.2+ |

---

## よくある質問 (FAQ)

### Q1: 特定のサービスだけ起動できますか？

**A1**: Phase 1では全サービスの一括操作のみをサポートしています。Phase 2以降で個別サービス制御を実装予定です。

現時点では、既存の`dev-start.sh`を使用するか、手動でサービスを起動してください。

### Q2: ポート番号を変更できますか？

**A2**: Phase 1では固定ポートのみをサポートしています。ポート番号を変更する場合は、`scripts/unified-start.sh` の以下の箇所を編集してください：

```bash
# Layer 1: Infrastructure services
LAYER1_SERVICES=(
    "myvault:8003:${PROJECT_ROOT}/myVault:uv run uvicorn app.main:app --host 0.0.0.0 --port 8003"
    ...
)
```

### Q3: worktreeで複数ブランチを同時に起動できますか？

**A3**: Phase 1では単一worktreeのみをサポートしています。Phase 2 (Issue #140-4, #140-5) でworktree並列起動をサポート予定です。

### Q4: エラーが発生しても他のサービスは起動し続けますか？

**A4**: はい、1つのサービスが起動に失敗しても、他のサービスの起動は続行されます。ただし、依存関係のあるサービス（例: myVaultに依存するサービス）は正しく動作しない可能性があります。

---

## 次のステップ

### Phase 2の機能（予定）

- ヘルスチェック機能 (Issue #140-2)
- エラーハンドリングとロールバック (Issue #140-3)
- Worktree自動検出とポート管理 (Issue #140-4)
- YAML設定ファイル導入 (Issue #140-7)

### フィードバック

問題や改善提案がある場合は、GitHubのIssueで報告してください：
- 親Issue: #140
- 本Issue: #141

---

## 参考資料

- [要件定義書](../dev-reports/feature/issue/140/requirements.md)
- [設計方針書](../dev-reports/feature/issue/140/design.md)
- [作業計画書](../dev-reports/feature/issue/141/work-plan.md)
- [開発フロー](./claude/01-development-workflow.md)

---

**更新履歴**:
- 2025-11-07: v1.0.0 初版作成 (Issue #141)
