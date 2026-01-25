# 作業計画書: Issue #141 - 基本統一起動スクリプトの実装

**Issue番号**: #141
**親Issue**: #140 - 受入テストの効率化
**作成日**: 2025-11-07
**担当**: Claude (Sonnet 4.5)
**Phase**: 1 (MVP実装)

---

## 1. 目的

全マイクロサービス（7サービス）を単一コマンドで起動・停止できる基本的な統一起動スクリプトを実装します。
最初のバージョンでは、ハードコーディングされた依存関係と固定ポートを使用し、単一worktreeでの動作に焦点を当てます。

---

## 2. ユーザーストーリー

**As a** Product Owner (PO)
**I want to** 一つのスクリプトで全てのマイクロサービスを起動できる
**So that** 受入テストの開始時間を短縮し、テスト効率を向上できる

---

## 3. 参照ドキュメント

必須参照ドキュメント：
- [要件定義書](../../140/requirements.md) - 親Issue #140の要件
- [設計方針書](../../140/design.md) - 設計の全体像
- [Issue分割](../../140/issue-breakdown.md) - Issue #141の詳細仕様
- [開発フロー](../../../docs/claude/01-development-workflow.md) - アジャイル開発プロセス
- [品質基準](../../../docs/claude/04-quality-standards.md) - テスト・静的解析基準

---

## 4. スコープ

### 4.1 含まれる機能

#### 基本機能
- `start` コマンド: 全7サービスの起動
- `stop` コマンド: 全サービスの停止
- `restart` コマンド: 全サービスの再起動
- `status` コマンド: サービス状態の確認

#### サービス管理
- 依存関係に基づく起動順序制御
  - Layer 1 (インフラ層): myVault, jobqueue
  - Layer 2 (ミドルウェア層): myscheduler, graphAiServer
  - Layer 3 (アプリケーション層): expertAgent, myAgentDesk, commonUI
- PIDファイル管理 (`/tmp/myswiftagent/*.pid`)
- nohupによるバックグラウンド実行
- 色付きログ出力

#### エラーハンドリング
- サービス起動失敗の検出
- 既存プロセスの検出と警告
- 適切なエラーメッセージ表示

### 4.2 含まれない機能（Phase 2以降）

- worktree自動検出
- ポート番号の動的割り当て
- YAML設定ファイル
- ヘルスチェック機能（Phase 1では既存のhealth-check.shを活用）
- Docker Compose統合
- 環境変数の階層的管理

---

## 5. 技術仕様

### 5.1 ファイル構成

```
scripts/
├── unified-start.sh          # メインエントリーポイント (新規)
└── unified-lib/              # ライブラリディレクトリ (新規)
    ├── common.sh             # 共通関数ライブラリ
    └── process-manager.sh    # プロセス管理機能
```

### 5.2 サービス定義（ハードコーディング）

```bash
# Layer 1: インフラサービス層
MYVAULT_PORT=8003
JOBQUEUE_PORT=8001

# Layer 2: ミドルウェア層
MYSCHEDULER_PORT=8002
GRAPHAISERVER_PORT=8005

# Layer 3: アプリケーション層
EXPERTAGENT_PORT=8004
MYAGENTDESK_PORT=5173
COMMONUI_PORT=8501
```

### 5.3 PIDファイル配置

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

### 5.4 ログファイル配置

既存のログディレクトリ構造を使用：

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

## 6. 実装タスク

### 6.1 ライブラリ実装

#### scripts/lib/common.sh
- [ ] 色定義（RED, GREEN, YELLOW, BLUE, NC等）
- [ ] `print_info()`: 情報メッセージ出力
- [ ] `print_success()`: 成功メッセージ出力
- [ ] `print_warning()`: 警告メッセージ出力
- [ ] `print_error()`: エラーメッセージ出力（stderr出力）
- [ ] `init_directories()`: ディレクトリ初期化
- [ ] `show_banner()`: バナー表示

#### scripts/lib/process-manager.sh
- [ ] `start_service()`: サービス起動関数
  - 引数: service_name, directory, port, start_command
  - PIDファイル確認
  - 既存プロセスチェック
  - nohupでバックグラウンド起動
  - PID保存
- [ ] `stop_service()`: サービス停止関数
  - PIDファイル読み込み
  - SIGTERM送信
  - 10秒待機
  - 必要ならSIGKILL送信
  - PIDファイル削除
- [ ] `restart_service()`: サービス再起動関数
- [ ] `is_service_running()`: プロセス存在確認
- [ ] `check_service_status()`: 稼働状況確認

### 6.2 メインスクリプト実装

#### scripts/unified-start.sh
- [ ] Shebang、エラーハンドリング設定（set -euo pipefail）
- [ ] ライブラリ読み込み
- [ ] サブコマンド解析（start/stop/restart/status）
- [ ] `--help` オプション実装
- [ ] サービス定義のハードコーディング
- [ ] 起動順序制御の実装
- [ ] 各サブコマンドの実装

### 6.3 サブコマンド詳細

#### start コマンド
```bash
./scripts/unified-start.sh start
```
- Layer 1サービス起動（myVault, jobqueue）
- Layer 2サービス起動（myscheduler, graphAiServer）
- Layer 3サービス起動（expertAgent, myAgentDesk, commonUI）
- 起動完了メッセージ表示

#### stop コマンド
```bash
./scripts/unified-start.sh stop
```
- 逆順でサービス停止（Layer 3 → Layer 2 → Layer 1）
- 停止完了メッセージ表示

#### restart コマンド
```bash
./scripts/unified-start.sh restart
```
- stop実行
- 2秒待機
- start実行

#### status コマンド
```bash
./scripts/unified-start.sh status
```
- 全サービスのPIDファイル確認
- プロセス稼働状況表示
- ポート番号表示

---

## 7. テスト計画

### 7.1 機能テスト

#### TC-141-001: 全サービス起動テスト
- **前提条件**: 全サービスが停止している
- **実行**: `./scripts/unified-start.sh start`
- **期待結果**: 全7サービスが起動順序通りに起動すること

#### TC-141-002: 全サービス停止テスト
- **前提条件**: 全サービスが起動している
- **実行**: `./scripts/unified-start.sh stop`
- **期待結果**: 全サービスが停止すること

#### TC-141-003: ステータス確認テスト
- **前提条件**: 一部サービスが起動している
- **実行**: `./scripts/unified-start.sh status`
- **期待結果**: 各サービスの状態が正しく表示されること

#### TC-141-004: 再起動テスト
- **前提条件**: 全サービスが起動している
- **実行**: `./scripts/unified-start.sh restart`
- **期待結果**: 全サービスが再起動すること

#### TC-141-005: 重複起動防止テスト
- **前提条件**: 全サービスが起動している
- **実行**: `./scripts/unified-start.sh start`
- **期待結果**: 既存プロセス検出の警告が表示され、エラーにならないこと

### 7.2 非機能テスト

#### TC-141-006: PIDファイル管理テスト
- **検証項目**:
  - 起動時にPIDファイルが作成されること
  - 停止時にPIDファイルが削除されること
  - PIDファイルの内容が正しいこと

#### TC-141-007: ログ出力テスト
- **検証項目**:
  - 各サービスのログが正しいパスに出力されること
  - エラー時のログが適切に記録されること

#### TC-141-008: 起動順序テスト
- **検証項目**:
  - Layer 1 → Layer 2 → Layer 3の順序で起動すること
  - 各レイヤー内のサービスが並列起動しないこと（Phase 1）

### 7.3 互換性テスト

#### TC-141-009: 既存スクリプトとの共存テスト
- **検証項目**:
  - `dev-start.sh` と同時に使用しても問題ないこと
  - ログファイルやPIDファイルが競合しないこと

---

## 8. ドキュメントタスク

### 8.1 使用方法ドキュメント

#### docs/unified-start-usage.md
- [ ] 概要
- [ ] インストール方法
- [ ] 基本的な使用方法
  - start コマンド
  - stop コマンド
  - restart コマンド
  - status コマンド
- [ ] コマンドラインオプション
- [ ] トラブルシューティング

### 8.2 コマンドラインヘルプ

#### --help オプション
```bash
./scripts/unified-start.sh --help
```
- 使用方法の表示
- サブコマンド一覧
- オプション説明

### 8.3 README.md更新

- [ ] 新しいunified-start.shスクリプトの説明追加
- [ ] 使用例の記載
- [ ] 既存のdev-start.shとの違いの説明

---

## 9. 受入条件

- [ ] `./scripts/unified-start.sh start` で全7サービスが起動すること
- [ ] `./scripts/unified-start.sh stop` で全サービスが停止すること
- [ ] `./scripts/unified-start.sh status` でサービス状態が確認できること
- [ ] `./scripts/unified-start.sh restart` でサービスが再起動すること
- [ ] `./scripts/unified-start.sh --help` でヘルプが表示されること
- [ ] 起動ログが適切に出力されること
- [ ] エラー時に適切なメッセージが表示されること
- [ ] PIDファイルが正しく作成・削除されること
- [ ] 起動順序が Layer 1 → Layer 2 → Layer 3 であること
- [ ] 全機能テストがパスすること

---

## 10. リスクと対策

| リスク | 影響度 | 発生確率 | 対策 |
|-------|-------|---------|------|
| 既存のdev-start.shとの競合 | 中 | 低 | PIDディレクトリを分離（/tmp/myswiftagent/） |
| サービス起動順序の不具合 | 高 | 中 | 十分なテストと待機時間の調整 |
| PIDファイル管理の失敗 | 中 | 低 | エラーハンドリングの徹底 |
| ポート競合 | 中 | 中 | 既存プロセス検出と警告表示 |

---

## 11. スケジュール

| タスク | 所要時間 | 開始日 | 完了予定日 |
|-------|---------|-------|-----------|
| ドキュメント作成 | 0.5日 | 2025-11-07 | 2025-11-07 |
| scripts/lib/common.sh実装 | 0.5日 | 2025-11-07 | 2025-11-07 |
| scripts/lib/process-manager.sh実装 | 1日 | 2025-11-07 | 2025-11-08 |
| scripts/unified-start.sh実装 | 1日 | 2025-11-08 | 2025-11-08 |
| テスト実施 | 1日 | 2025-11-08 | 2025-11-08 |
| ドキュメント作成 | 0.5日 | 2025-11-08 | 2025-11-08 |
| **合計** | **4.5日** | - | - |

---

## 12. 成功指標

### 定量的指標
- 起動時間: 全サービス起動完了まで5分以内
- コマンド実行成功率: 100%（正常環境下）
- テストケースパス率: 100%

### 定性的指標
- POから「使いやすい」とのフィードバック
- 既存のdev-start.shと同等以上の安定性
- Phase 2への拡張性を確保した設計

---

## 13. 次のステップ（Phase 2以降）

- Issue #140-2: ヘルスチェック機能の実装
- Issue #140-3: エラーハンドリングとロールバック機能
- Issue #140-4: Worktree自動検出とポート管理
- Issue #140-7: YAML設定ファイル導入

---

**承認者**: _______________________
**承認日**: _______________________
