# 受入テスト効率化機能

MySwiftAgentの全マイクロサービスを統一的に起動・管理するための機能です。複数のブランチで並行して受入テストを実施でき、開発・テストの効率を大幅に向上させます。

## 目次

- [概要](#概要)
- [機能仕様](#機能仕様)
- [利用方法](#利用方法)
- [アーキテクチャ](#アーキテクチャ)
- [トラブルシューティング](#トラブルシューティング)
- [変更履歴](#変更履歴)

---

## 概要

### 背景

従来、MySwiftAgentの受入テストを行うには、7つのマイクロサービスを個別に起動する必要があり、環境構築に10-15分かかっていました。また、複数のブランチで並行テストを行う場合、ポート競合の手動解決が必要でした。

### ソリューション

統一起動スクリプト `scripts/unified-start.sh` により、以下を実現します:

- **単一コマンドでの一括起動**: 全7サービスを正しい依存順序で起動
- **Worktree並列起動**: 最大4つのブランチで同時にテスト環境を構築
- **自動ポート管理**: ポート競合を自動検出・回避
- **ヘルスチェック**: 各サービスの起動完了と健全性を自動確認
- **エラー自動復旧**: 起動失敗時の自動ロールバック

### 効果

| 指標 | 改善前 | 改善後 | 改善率 |
|------|--------|--------|--------|
| セットアップ時間 | 10-15分 | 3分以内 | **80%削減** |
| 並列テスト数 | 1ブランチ | 4ブランチ | **4倍向上** |
| 起動成功率 | 70% | 95%以上 | **25%向上** |

---

## 機能仕様

### 対象サービス

以下の7つのマイクロサービスを管理します:

| サービス名 | デフォルトポート | 役割 |
|-----------|----------------|------|
| myVault | 8103 | シークレット管理 |
| jobqueue | 8101 | ジョブキュー管理 |
| myscheduler | 8102 | ジョブスケジューリング |
| graphAiServer | 8105 | ワークフロー実行 |
| expertAgent | 8104 | AIエージェント |
| myAgentDesk | 5173 | Web UI |
| commonUI | 8601 | 共通UIコンポーネント |

### 起動順序

依存関係に基づき、以下の3層構造で順次起動します:

```
Layer 1 (インフラ層)
  ├── myVault       (シークレット管理が全サービスの前提)
  └── jobqueue      (キュー管理)

Layer 2 (ミドルウェア層)
  ├── myscheduler   (Layer 1に依存)
  └── graphAiServer (Layer 1に依存)

Layer 3 (アプリケーション層)
  ├── expertAgent   (Layer 1, 2に依存)
  └── myAgentDesk/commonUI (全レイヤーに依存)
```

### Worktree対応

複数のgit worktreeで同時起動する際、以下のルールでポート番号を自動割り当てします:

```
ポート番号 = ベースポート + (worktreeインデックス × 10)
```

**例**:
- `develop` (index 0): expertAgent は 8104
- `worktree-1` (index 1): expertAgent は 8114
- `worktree-2` (index 2): expertAgent は 8124

### ヘルスチェック

各サービスの `/health` エンドポイントを監視し、起動完了を確認します:

- **タイムアウト**: 30秒（デフォルト）
- **リトライ間隔**: 1秒
- **ステータス表示**: ✅ 成功 / ⚠️ 警告 / ❌ 失敗

### エラーハンドリング

起動失敗時、以下の処理を自動実行します:

1. **ポート競合検出**: 使用中のポートとプロセスを特定
2. **自動ロールバック**: 起動済みサービスを逆順で停止
3. **クリーンアップ**: PIDファイル・一時ファイルを削除
4. **エラー提案**: 解決方法を具体的に提示

---

## 利用方法

### 基本コマンド

#### 全サービスの起動

```bash
./scripts/unified-start.sh start
```

**動作**:
1. 環境変数を読み込み（`.env` → `.env.local`の順で優先）
2. Layer 1 → Layer 2 → Layer 3 の順で起動
3. 各サービスのヘルスチェックを実行
4. 起動完了メッセージを表示

#### 全サービスの停止

```bash
./scripts/unified-start.sh stop
```

**動作**:
- Layer 3 → Layer 2 → Layer 1 の逆順で停止
- PIDファイルをクリーンアップ

#### サービスステータス確認

```bash
./scripts/unified-start.sh status
```

**出力例**:
```
✅ jobqueue: Running healthy (PID: 12345, Port: 8101)
✅ myscheduler: Running healthy (PID: 12346, Port: 8102)
⚠️ myVault: Running but health check failed (PID: 12347, Port: 8103)
❌ expertAgent: Not running
```

#### 全サービスの再起動

```bash
./scripts/unified-start.sh restart
```

### 応用コマンド

#### カスタム環境ファイルを使用

```bash
./scripts/unified-start.sh start --env-file .env.production
```

#### ドライラン（設定確認のみ）

```bash
./scripts/unified-start.sh start --dry-run
```

#### 強制起動（既存プロセスを停止）

```bash
./scripts/unified-start.sh start --force
```

**注意**: ポート競合しているプロセスを自動的に停止します。

#### ヘルスチェックタイムアウトのカスタマイズ

```bash
./scripts/unified-start.sh start --timeout 60
```

#### 特定worktreeの操作

```bash
# worktree 2のサービスを起動
./scripts/unified-start.sh start --worktree 2

# worktree 2のステータス確認
./scripts/unified-start.sh status --worktree 2

# worktree 2のサービスを停止
./scripts/unified-start.sh stop --worktree 2
```

### Worktree並列起動の手順

#### 1. Worktreeを作成

```bash
# Issue #123用のworktreeを作成
git worktree add ../MySwiftAgent-worktrees/feature-issue-123 -b feature/issue/123
```

#### 2. 各worktreeでサービスを起動

```bash
# Main repository (develop)
cd /path/to/MySwiftAgent
./scripts/unified-start.sh start

# Worktree 1
cd ../MySwiftAgent-worktrees/feature-issue-123
./scripts/unified-start.sh start
```

**自動的に実行されること**:
- Worktreeインデックスの検出（`git worktree list`で判定）
- ポート番号の自動計算
- `.env.local`の優先読み込み（worktree固有設定）

#### 3. 全worktreeのステータスを一括確認

```bash
# Main repositoryで実行
./scripts/unified-start.sh status --all-worktrees
```

### 環境変数の管理

#### 優先順位

環境変数は以下の優先順で読み込まれます（上が優先）:

1. コマンドライン引数（`--env-file`等）
2. `.env.local`（worktree固有設定）
3. 各プロジェクトの`.env`（プロジェクト設定）
4. スクリプトのデフォルト値

#### `.env.local`の例

Worktree固有のポート設定:

```bash
# .env.local (worktree-1用)
JOBQUEUE_PORT=8111
MYSCHEDULER_PORT=8112
MYVAULT_PORT=8113
EXPERTAGENT_PORT=8114
GRAPHAISERVER_PORT=8115
MYAGENTDESK_PORT=5174
COMMONUI_PORT=8611
```

**注意**: 通常は自動計算されるため、手動設定は不要です。

---

## アーキテクチャ

### システム構成

```
┌─────────────────────────────────────────────────────────────────┐
│                     統一起動スクリプト                           │
│                    (unified-start.sh)                           │
├─────────────────────────────────────────────────────────────────┤
│  コマンド層    │  設定層      │  ライブラリ層   │  監視層     │
├────────────────┼──────────────┼─────────────────┼──────────────┤
│ • start        │ • services   │ • port-manager  │ • health    │
│ • stop         │ • deps       │ • worktree      │ • status    │
│ • restart      │ • env        │ • process       │ • logs      │
│ • status       │              │ • docker        │              │
│ • logs         │              │                 │              │
└────────────────┴──────────────┴─────────────────┴──────────────┘
```

### ディレクトリ構造

```
scripts/
├── unified-start.sh          # メインスクリプト
├── lib/
│   ├── common.sh             # 共通関数（色出力、ログ等）
│   ├── port-manager.sh       # ポート管理
│   ├── process-manager.sh    # プロセス管理
│   ├── health-check.sh       # ヘルスチェック
│   ├── worktree-utils.sh     # worktree検出・管理
│   ├── env-loader.sh         # 環境変数読み込み
│   └── docker-utils.sh       # Docker管理（langfuse用）
└── config/
    ├── services.yaml         # サービス定義
    └── dependencies.yaml     # 依存関係定義
```

### 技術スタック

| 要素 | 技術 | 理由 |
|------|------|------|
| **実装言語** | Bash (POSIX準拠) | 既存資産との整合性、依存最小化 |
| **設定管理** | YAML (yqコマンド) | 可読性、拡張性 |
| **プロセス管理** | nohup + PIDファイル | シンプル、確実 |
| **ヘルスチェック** | curl + エンドポイント監視 | 標準的、信頼性高 |
| **ポート確認** | lsof | macOS/Linux両対応 |

### 主要コンポーネント

#### 1. ポート管理モジュール (`port-manager.sh`)

**機能**:
- Worktreeインデックスの自動検出
- ポート番号計算: `base_port + (index × 10)`
- ポート使用状況確認
- 代替ポートの提案

**主要関数**:
```bash
detect_worktree_index()      # worktreeインデックス検出
calculate_ports()            # ポート番号計算
check_port_available()       # ポート使用確認
resolve_port_conflict()      # ポート競合解決
```

#### 2. プロセス管理モジュール (`process-manager.sh`)

**機能**:
- サービスのライフサイクル管理
- PIDファイルによるプロセス追跡
- 依存関係に基づく起動順序制御
- Graceful shutdown

**主要関数**:
```bash
start_service()              # サービス起動
stop_service()               # サービス停止
restart_service()            # サービス再起動
is_service_running()         # 稼働状況確認
```

#### 3. ヘルスチェックモジュール (`health-check.sh`)

**機能**:
- `/health`エンドポイント監視
- リトライ機構（最大30秒、1秒間隔）
- ステータス可視化

**主要関数**:
```bash
check_service_health()       # 個別サービスヘルスチェック
check_all_health()           # 全サービスヘルスチェック
wait_for_healthy()           # 起動待機
```

---

## トラブルシューティング

### ポート競合エラー

**症状**:
```
❌ Error: Port 8104 is already in use by process 12345
```

**原因**: 既に別のプロセスがポートを使用中

**解決方法**:

1. **強制起動**（既存プロセスを停止）:
   ```bash
   ./scripts/unified-start.sh start --force
   ```

2. **手動でプロセスを確認・停止**:
   ```bash
   # ポート使用中のプロセスを確認
   lsof -i :8104

   # プロセスを停止
   kill <PID>
   ```

3. **別のポートを使用**（`.env.local`で設定）:
   ```bash
   EXPERTAGENT_PORT=8204
   ```

### ヘルスチェック失敗

**症状**:
```
⚠️ myVault: Running but health check failed (PID: 12347, Port: 8103)
```

**原因**:
- サービスは起動しているが、`/health`エンドポイントが応答しない
- 依存サービスが未起動

**解決方法**:

1. **ログを確認**:
   ```bash
   tail -f logs/myVault.log
   ```

2. **手動でヘルスチェック**:
   ```bash
   curl http://localhost:8103/health
   ```

3. **依存サービスを確認**:
   ```bash
   ./scripts/unified-start.sh status
   ```

### Worktreeインデックス検出失敗

**症状**:
```
❌ Error: Could not detect worktree index
```

**原因**: worktreeの構成が想定外

**解決方法**:

1. **Worktreeリストを確認**:
   ```bash
   git worktree list
   ```

2. **手動でインデックスを指定**:
   ```bash
   ./scripts/unified-start.sh start --worktree 2
   ```

### 環境変数が読み込まれない

**症状**: サービスが正しい設定で起動しない

**解決方法**:

1. **ドライランで設定を確認**:
   ```bash
   ./scripts/unified-start.sh start --dry-run
   ```

2. **環境変数の読み込み順を確認**:
   - `.env`ファイルが存在するか
   - `.env.local`が意図した値になっているか

3. **カスタム環境ファイルを明示的に指定**:
   ```bash
   ./scripts/unified-start.sh start --env-file .env.test
   ```

### メモリ不足

**症状**:
```
⚠️ Warning: Available memory (6GB) is below recommended (8GB)
```

**原因**: システムメモリが不足

**解決方法**:

1. **不要なプロセスを停止**

2. **起動するworktree数を減らす**:
   - 推奨: 最大4 worktree
   - 各worktree: 約2GB必要

3. **サービスごとに起動**（一括起動を避ける）:
   ```bash
   # Layer 1のみ起動
   ./scripts/unified-start.sh start --layer 1
   ```

---

## 変更履歴

### 2025-11-11 - Initial Release (Issue #140)

**追加機能**:
- 統一起動スクリプト `scripts/unified-start.sh` の実装
- 全7サービスの一括起動・停止機能
- Worktree並列起動サポート（最大4ブランチ）
- 自動ポート管理とポート競合解決
- ヘルスチェック機能（`/health`エンドポイント監視）
- エラーハンドリングとロールバック機能
- 環境変数の階層的管理（`.env` → `.env.local`）
- YAML設定ファイルによるサービス定義
- Docker Compose統合（langfuse対応）
- ステータスダッシュボード
- メトリクス収集と自動リカバリ

**実装フェーズ**:
- Phase 1: MVP実装（基本起動、ヘルスチェック、エラーハンドリング）
- Phase 2: Worktree対応（自動検出、並列起動、環境変数管理、YAML設定）
- Phase 3: 高度な機能（Docker統合、ダッシュボード、メトリクス）

**性能指標**:
- セットアップ時間: 10-15分 → 3分以内（80%削減）
- 並列テスト数: 1 → 4 worktree（4倍向上）
- 起動成功率: 70% → 95%以上（25%向上）

**関連リソース**:
- GitHub Issue: [#140](https://github.com/kewton/MySwiftAgent/issues/140)
- 設計方針書: `dev-reports/feature/issue/140/design.md`
- 要件定義書: `dev-reports/feature/issue/140/requirements.md`
- 作業計画書: `dev-reports/feature/issue/140/work-plan.md`
- Issue分割計画: `dev-reports/feature/issue/140/issue-breakdown.md`

**子Issue**:
- Issue #140-1: 基本統一起動スクリプトの実装
- Issue #140-2: ヘルスチェック機能の実装
- Issue #140-3: エラーハンドリングとロールバック機能
- Issue #140-4: Worktree自動検出とポート管理
- Issue #140-5: 複数Worktree並列起動サポート
- Issue #140-6: 環境変数の階層的管理機能
- Issue #140-7: YAML設定ファイル導入
- Issue #140-8: Docker Compose統合
- Issue #140-9: ステータスダッシュボード機能
- Issue #140-10: メトリクス収集と自動リカバリ

---

## クロスサービスE2Eテスト

### 概要

複数のマイクロサービスを連携させた実践的なEnd-to-Endテストです。単一サービスのテストではなく、実際のユーザーシナリオに基づいたフルスタックテストを提供します。

### テスト一覧

| テスト | 説明 | 所要時間 |
|--------|------|---------|
| `test_full_workflow_e2e.sh` | Job生成→実行→メール送信の完全E2E | 約3-5分 |

### 前提条件

#### サービス起動

```bash
# Platform層（Docker）+ Agent層（ローカル）で起動
./scripts/dev-hybrid.sh stop --local-only
./scripts/dev-hybrid.sh start --local-only
```

#### 必須サービス

| サービス | URL | 役割 |
|---------|-----|------|
| myAgentDesk | http://localhost:8000 | Web UI |
| expertAgent | http://localhost:8004 | Job Generator API |
| mySwiftAgentCore | http://localhost:8006 | Workflow実行 |
| myVault | http://localhost:8003 | シークレット管理 |

#### 必須環境設定

- myVaultに `default_project` のシークレットが設定済み
  - `ANTHROPIC_API_KEY`: Claude API キー
  - `GOOGLE_CREDENTIALS`: Google API認証情報
  - `GMAIL_CREDENTIALS`: Gmail API認証情報

### テスト実行

#### フルワークフローE2E

```bash
# 基本実行（インタラクティブモード）
./scripts/e2e/cross-service/test_full_workflow_e2e.sh

# パラメータ指定（非インタラクティブ）
./scripts/e2e/cross-service/test_full_workflow_e2e.sh \
  --keyword "大谷翔平の妻" \
  --email "your-email@example.com" \
  --project-id "proj_xxxx" \
  --workbench-id "wb_xxxx"

# ヘルプ表示
./scripts/e2e/cross-service/test_full_workflow_e2e.sh --help
```

#### 全テスト実行

```bash
./scripts/e2e/cross-service/run_all_tests.sh "keyword" "email@example.com"
```

### テストフロー

```
1. サービスヘルスチェック
   ↓
2. myAgentDesk経由でJob Generate実行
   ↓
3. 生成されたJobVersionを確認
   ↓
4. Runを作成・実行（keyword + email パラメータ）
   ↓
5. Run完了を待機（ポーリング）
   ↓
6. 結果検証（status = success）
   ↓
7. レポート出力
```

### テスト結果

テスト結果は以下に出力されます：

```
scripts/e2e/cross-service/results/
├── test_full_workflow_YYYYMMDD_HHMMSS.log
└── test_full_workflow_YYYYMMDD_HHMMSS.json
```

### 関連ドキュメント

- [クロスサービスE2Eテスト README](../../scripts/e2e/cross-service/README.md)
- [mySwiftAgentCore E2Eテスト](../../scripts/e2e/myswiftagentcore/README.md)

---

_最終更新: 2026-01-25_
