# 作業計画書: 受入テストの効率化（Issue #140）

**作成日**: 2025-11-06
**作成者**: Claude (Opus 4.1)
**バージョン**: 1.0.0

---

## 1. 全体スケジュール

### 3週間実装スケジュール概要

```
Week 1 (11/6-11/10): Phase 1 - MVP実装
  └─ Issue #140-1: 基本統一起動スクリプト（3日）
  └─ Issue #140-2: ヘルスチェック機能（2日）
  └─ Issue #140-3: エラーハンドリング（2日）

Week 2 (11/13-11/17): Phase 2 - Worktree対応
  └─ Issue #140-4: Worktree自動検出（3日）
  └─ Issue #140-5: 複数Worktree並列起動（2日）
  └─ Issue #140-6: 環境変数管理（2日）
  └─ Issue #140-7: YAML設定導入（3日）

Week 3 (11/20-11/24): Phase 3 - 高度な機能
  └─ Issue #140-8: Docker Compose統合（2日）
  └─ Issue #140-9: ステータスダッシュボード（3日）
  └─ Issue #140-10: メトリクス収集（2日）
```

### クリティカルパス
1. **Issue #140-1** → **Issue #140-2, #140-3** → **Issue #140-10**
2. **Issue #140-4** → **Issue #140-5**
3. **Issue #140-1** → **Issue #140-7** → **Issue #140-8**

---

## 2. Issue #140-1 詳細作業計画

### 2.1 実装ステップ

#### Day 1: 基盤構築（11/6）

**午前（4h）: ディレクトリ構造とメインスクリプト**
- [ ] **Task 1.1**: ディレクトリ構造の作成（30分）
  ```bash
  scripts/
  ├── unified-start.sh       # 新規作成
  ├── lib/
  │   ├── common.sh          # 新規作成
  │   └── process-manager.sh # 新規作成
  └── config/
      └── services.conf      # 新規作成（ハードコード版）
  ```

- [ ] **Task 1.2**: `unified-start.sh` メインフレーム実装（2h）
  - コマンドライン解析（start/stop/restart/status）
  - 基本的なエラーハンドリング（set -euo pipefail）
  - ヘルプ機能の実装

- [ ] **Task 1.3**: `lib/common.sh` 共通関数実装（1.5h）
  - 既存 `dev-start.sh` から関数を抽出・リファクタリング
  - 色付き出力関数（print_success, print_error, print_warning等）
  - ログ管理関数

**午後（4h）: プロセス管理基盤**
- [ ] **Task 1.4**: `lib/process-manager.sh` 基本機能実装（3h）
  - PIDファイル管理（/tmp/myswiftagent/*.pid）
  - nohup起動機能
  - プロセス停止機能（graceful shutdown対応）
  - ポート使用確認機能（lsof使用）

- [ ] **Task 1.5**: サービス定義の実装（1h）
  - 7サービスの定義（ポート、起動コマンド、依存関係）
  - 起動順序の定義（3層アーキテクチャ）

#### Day 2: コア機能実装（11/7）

**午前（4h）: サービス起動機能**
- [ ] **Task 2.1**: 個別サービス起動関数の実装（2h）
  - start_service() 関数の実装
  - 各サービス固有の起動パラメータ対応
  - 環境変数の自動設定（JOBQUEUE_API_URL等）

- [ ] **Task 2.2**: 依存関係に基づく順次起動の実装（2h）
  - Layer 1: myVault, jobqueue
  - Layer 2: myscheduler, graphAiServer
  - Layer 3: expertAgent, myAgentDesk, commonUI

**午後（4h）: 停止・再起動機能**
- [ ] **Task 2.3**: サービス停止機能の実装（2h）
  - stop_service() 関数の実装
  - 逆順での停止処理
  - 孤立プロセスのクリーンアップ

- [ ] **Task 2.4**: ステータス確認機能の実装（1.5h）
  - check_service_status() 関数
  - プロセス存在確認
  - ポート監視状態確認

- [ ] **Task 2.5**: 再起動機能の実装（30分）
  - restart コマンドの実装（stop → sleep → start）

#### Day 3: テストとドキュメント（11/8）

**午前（4h）: テスト実装**
- [ ] **Task 3.1**: 単体テストの実装（2h）
  - 各関数の個別テスト
  - エラーケースのテスト
  - PIDファイル管理のテスト

- [ ] **Task 3.2**: 統合テストの実装（2h）
  - 全サービス起動・停止テスト
  - 起動順序の確認テスト
  - ポート競合時の動作テスト

**午後（4h）: ドキュメント作成とバグ修正**
- [ ] **Task 3.3**: ユーザードキュメントの作成（2h）
  - README.md の更新
  - docs/unified-start-usage.md の作成
  - コマンドラインヘルプの充実

- [ ] **Task 3.4**: バグ修正とリファクタリング（2h）
  - テストで発見された問題の修正
  - コードレビューと改善
  - 既存スクリプトとの互換性確認

### 2.2 実装する関数・ファイル

#### scripts/unified-start.sh
```bash
# メイン制御関数
main()                    # エントリーポイント、コマンド解析とディスパッチ
parse_args()             # コマンドライン引数の解析
show_help()              # ヘルプメッセージ表示
show_banner()            # 起動バナー表示

# サービス管理関数
start_all_services()     # 全サービスの起動制御
stop_all_services()      # 全サービスの停止制御
restart_all_services()   # 全サービスの再起動
status_all_services()    # 全サービスのステータス確認

# 環境設定関数
setup_environment()      # 環境変数の設定
validate_environment()   # 環境の事前チェック
```

#### scripts/lib/common.sh
```bash
# 出力関数（dev-start.shから移植）
print_step()             # ステップ表示 "[HH:MM:SS] 📋 message"
print_info()             # 情報表示 "[HH:MM:SS] ℹ️ message"
print_success()          # 成功表示 "[HH:MM:SS] ✅ message"
print_warning()          # 警告表示 "[HH:MM:SS] ⚠️ message"
print_error()            # エラー表示 "[HH:MM:SS] ❌ message"
print_service()          # サービス固有メッセージ

# ディレクトリ管理
init_directories()       # ログ・PIDディレクトリ作成
cleanup_directories()    # 一時ファイルクリーンアップ

# ログ管理
setup_logging()          # ログファイル初期化
rotate_logs()           # ログローテーション（将来実装）
```

#### scripts/lib/process-manager.sh
```bash
# プロセス管理
start_service()          # サービス起動（nohup使用）
stop_service()           # サービス停止（graceful shutdown）
restart_service()        # サービス再起動
is_service_running()     # プロセス稼働確認
get_service_pid()        # PIDファイルからPID取得

# PIDファイル管理
create_pid_file()        # PIDファイル作成
remove_pid_file()        # PIDファイル削除
validate_pid_file()      # PIDファイルの整合性チェック

# ポート管理
check_port()             # ポート使用確認（lsof使用）
kill_port()              # ポート占有プロセスの停止
wait_for_port()          # ポート開放待機

# 依存関係管理
get_service_dependencies() # サービスの依存関係取得
check_dependencies()      # 依存サービスの稼働確認
```

#### scripts/config/services.conf
```bash
# Phase 1ではBash配列でハードコード
declare -A SERVICE_PORTS=(
    [jobqueue]=8101
    [myscheduler]=8102
    [myVault]=8103
    [expertAgent]=8104
    [graphAiServer]=8105
    [myAgentDesk]=5173
    [commonUI]=8601
)

declare -A SERVICE_DIRS=(
    [jobqueue]="$PROJECT_ROOT/jobqueue"
    [myscheduler]="$PROJECT_ROOT/myscheduler"
    # ...
)

# 起動順序の定義
LAYER1_SERVICES=("myVault" "jobqueue")
LAYER2_SERVICES=("myscheduler" "graphAiServer")
LAYER3_SERVICES=("expertAgent" "myAgentDesk" "commonUI")
```

### 2.3 技術的注意点

#### エラーハンドリング
```bash
# 厳密モードの使用
set -euo pipefail
trap cleanup EXIT ERR

# エラートラップの実装
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        print_error "Script failed with exit code: $exit_code"
        # ロールバック処理
    fi
}
```

#### 並行処理の考慮
```bash
# 同一層内のサービスは並列起動可能
start_layer_parallel() {
    local layer_services=("$@")
    local pids=()

    for service in "${layer_services[@]}"; do
        start_service "$service" &
        pids+=($!)
    done

    # 全バックグラウンドジョブの完了待機
    for pid in "${pids[@]}"; do
        wait $pid || return 1
    done
}
```

#### ポータビリティ
- POSIX準拠のシェルスクリプト記法を使用
- macOS/Linux両対応（lsof/netstatの違いを吸収）
- bashのバージョン依存を最小化（bash 3.2以上）

### 2.4 テストシナリオ

#### 正常系テスト
1. **全サービス起動テスト**
   - 前提: 全ポートが空いている状態
   - 実行: `./scripts/unified-start.sh start`
   - 期待: 全7サービスが正しい順序で起動、ステータス確認可能

2. **個別サービス停止・起動テスト**
   - 前提: 全サービスが起動済み
   - 実行: 特定サービスの停止→起動
   - 期待: 依存関係が保たれたまま正常動作

3. **再起動テスト**
   - 前提: 全サービスが起動済み
   - 実行: `./scripts/unified-start.sh restart`
   - 期待: 全サービスが一度停止し、再度起動

#### 異常系テスト
1. **ポート競合テスト**
   - 前提: 8101ポートを別プロセスが使用中
   - 実行: `./scripts/unified-start.sh start`
   - 期待: エラーメッセージ表示、ポート解放の提案

2. **依存サービス未起動テスト**
   - 前提: myVaultが起動していない
   - 実行: expertAgent起動試行
   - 期待: 依存関係エラーの表示

3. **権限不足テスト**
   - 前提: ログディレクトリへの書き込み権限なし
   - 実行: `./scripts/unified-start.sh start`
   - 期待: 適切なエラーメッセージ表示

#### 境界値テスト
1. **同時起動テスト**
   - 複数ターミナルから同時に起動スクリプト実行
   - PIDファイルのロック機構確認

2. **長時間稼働テスト**
   - 24時間連続稼働後の安定性確認
   - メモリリーク、ファイルディスクリプタリークの確認

### 2.5 予想される課題と対策

| 課題 | リスク | 対策 | 実装優先度 |
|-----|-------|------|----------|
| **Python仮想環境の活性化** | uvコマンドが見つからない | 自動的に.venvを検出・活性化 | 高 |
| **macOS/Linux差異** | lsof/netstatコマンドの違い | OSを検出して適切なコマンドを使用 | 高 |
| **サービス起動タイムアウト** | 遅いマシンで起動失敗 | タイムアウト値を環境変数で調整可能に | 中 |
| **ログファイルの肥大化** | ディスク容量圧迫 | Phase 3でログローテーション実装 | 低 |
| **並列起動の競合状態** | データベースロック | 起動順序の厳密な制御 | 高 |
| **環境変数の衝突** | 既存設定との競合 | .env.localの優先読み込み | 中 |

---

## 3. その他Issue（#140-2 ~ #140-10）概要計画

### Issue #140-2: ヘルスチェック機能（2日）

**実装方針:**
- `scripts/lib/health-check.sh` を新規作成
- 各サービスの `/health` エンドポイントをcurlで確認
- リトライ機構（最大30秒、1秒間隔）
- ステータスの可視化（✅/⚠️/❌）

**主要マイルストーン:**
- Day 1: ヘルスチェック基本機能実装
- Day 2: リトライ機構とタイムアウト処理

**Issue #140-1との連携:**
- start_service() 関数内でヘルスチェックを呼び出し
- status コマンドでヘルスチェック結果を表示

### Issue #140-3: エラーハンドリングとロールバック（2日）

**実装方針:**
- trapコマンドによるエラーキャッチ
- 起動済みサービスのトラッキング（配列管理）
- エラー時の自動ロールバック

**主要マイルストーン:**
- Day 1: エラートラップとロールバック機構
- Day 2: エラーメッセージカタログ化

**予想される課題:**
- 部分的な起動失敗時の状態管理
- 並列起動時のエラーハンドリング

### Issue #140-4: Worktree自動検出とポート管理（3日）

**実装方針:**
- `setup-worktree.sh` のロジックを統合
- 空きインデックス検出アルゴリズムの実装
- ポート計算式: base_port + (index × 10)

**主要マイルストーン:**
- Day 1: worktree検出機能
- Day 2: ポート管理モジュール
- Day 3: 競合解決機能

**技術的注意点:**
- git worktree listコマンドの解析
- .env.localファイルの読み込み優先順位

### Issue #140-5: 複数Worktree並列起動サポート（2日）

**実装方針:**
- worktreeごとのPIDファイル分離
- 最大4 worktree同時起動のサポート
- メモリ使用量の事前チェック

**主要マイルストーン:**
- Day 1: PID/ログファイル分離
- Day 2: リソース管理と制限

**Issue #140-4との連携:**
- worktree検出機能を前提
- ポート番号の自動割り当てを活用

### Issue #140-6: 環境変数の階層的管理（2日）

**実装方針:**
- .env → .env.local の優先順位実装
- サービスURL自動構成（JOBQUEUE_API_URL等）
- 必須環境変数のバリデーション

**主要マイルストーン:**
- Day 1: 環境変数ローダー実装
- Day 2: バリデーションとエラー処理

### Issue #140-7: YAML設定ファイル導入（3日）

**実装方針:**
- services.yaml, dependencies.yamlの設計
- yqコマンドによるパース（オプション）
- フォールバック機構（yq不在時）

**主要マイルストーン:**
- Day 1: YAML設計とスキーマ定義
- Day 2: パーサー実装
- Day 3: 既存ハードコードからの移行

**技術的課題:**
- yqコマンドの依存性管理
- Bashでの簡易YAML解析実装

### Issue #140-8: Docker Compose統合（2日）

**実装方針:**
- langfuse用docker-compose.yml作成
- Docker Desktop起動確認
- --skip-dockerオプション

**主要マイルストーン:**
- Day 1: Docker管理モジュール
- Day 2: 統合テスト

### Issue #140-9: ステータスダッシュボード（3日）

**実装方針:**
- 拡張statusコマンド
- テーブル形式での表示
- --watchオプションでリアルタイム更新

**主要マイルストーン:**
- Day 1: 基本的な表示機能
- Day 2: リソース使用状況の収集
- Day 3: リアルタイム更新機能

### Issue #140-10: メトリクス収集と自動リカバリ（2日）

**実装方針:**
- サービス異常の自動検知
- 設定可能な再起動ポリシー
- 再起動履歴の記録

**主要マイルストーン:**
- Day 1: メトリクス収集基盤
- Day 2: 自動リカバリ実装

---

## 4. 品質保証計画

### 4.1 テスト戦略

#### 単体テスト
- 各関数の個別テスト（scripts/test/unit/）
- モック使用によるエラーケーステスト
- カバレッジ目標: 90%

#### 統合テスト
- エンドツーエンドシナリオテスト
- 複数worktreeでの並列実行テスト
- カバレッジ目標: 50%

#### 受入テスト
- POによる実環境でのテスト
- 3つの異なるブランチでの同時起動
- パフォーマンス測定（起動時間3分以内）

### 4.2 レビュープロセス

1. **セルフレビュー**
   - 実装後に自己チェックリスト確認
   - 静的解析ツール実行（shellcheck）

2. **ピアレビュー**
   - 各Issueごとにプルリクエスト作成
   - 最低1名のレビュアーによる確認

3. **受入レビュー**
   - POによる機能確認
   - ユーザビリティの評価

### 4.3 CI/CD統合

#### GitHub Actions設定
```yaml
name: Unified Start Script Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run shellcheck
        run: shellcheck scripts/unified-start.sh scripts/lib/*.sh
      - name: Run unit tests
        run: ./scripts/test/run-unit-tests.sh
      - name: Run integration tests
        run: ./scripts/test/run-integration-tests.sh
```

#### 自動テスト項目
- Syntax check（bashスクリプト構文）
- Shellcheck（ベストプラクティス）
- 起動・停止の基本動作
- エラーハンドリング

---

## 5. リスク管理

### 技術リスク

| リスク | 影響度 | 発生確率 | 対策 | モニタリング方法 |
|-------|-------|---------|------|----------------|
| **Bashスクリプトの保守性低下** | 高 | 中 | モジュール分割、詳細なコメント | コードレビュー、複雑度測定 |
| **worktree検出の失敗** | 中 | 低 | フォールバック機構、手動指定オプション | テストケースでカバー |
| **ポート競合** | 高 | 中 | 自動ポート検出、代替ポート機能 | 起動時のポート確認 |
| **依存関係の循環** | 高 | 低 | 依存グラフの事前検証 | 設計レビュー |
| **パフォーマンス劣化** | 中 | 中 | 並列起動、キャッシュ活用 | 起動時間の測定 |

### 運用リスク

| リスク | 影響度 | 発生確率 | 対策 | モニタリング方法 |
|-------|-------|---------|------|----------------|
| **設定ミス** | 高 | 中 | バリデーション、エラーメッセージ改善 | ユーザーフィードバック |
| **ドキュメント不足** | 中 | 中 | 詳細なREADME、--helpオプション | 質問・問い合わせ数 |
| **互換性の破壊** | 高 | 低 | 後方互換性維持、移行ガイド | 既存ユーザーテスト |

### 緩和策
1. **段階的リリース**: Phase 1完了時点でベータ版リリース
2. **フィードバックループ**: 各Phaseごとにユーザーフィードバック収集
3. **ロールバック計画**: 既存スクリプトの並行維持（3ヶ月）

---

## 6. 成功基準

### Phase 1（MVP）完了基準
- [ ] 単一コマンドで全7サービスが起動する
- [ ] 起動順序が正しく制御される
- [ ] PIDファイルによるプロセス管理が機能する
- [ ] 基本的なエラーハンドリングが実装されている
- [ ] ドキュメントが作成されている

### Phase 2（Worktree対応）完了基準
- [ ] worktreeが自動検出される
- [ ] 最大4 worktreeで並列起動可能
- [ ] ポート競合が自動解決される
- [ ] 環境変数が階層的に管理される
- [ ] YAML設定ファイルが導入されている

### Phase 3（高度な機能）完了基準
- [ ] Docker Compose統合が機能する
- [ ] ステータスダッシュボードが表示される
- [ ] メトリクス収集が動作する
- [ ] 自動リカバリが実装されている

### 最終成功指標
- **起動時間**: 10-15分 → **3分以内**（80%削減）✅
- **並列実行**: 1 → **4 worktree**（4倍向上）✅
- **起動成功率**: 70% → **95%以上**✅
- **ユーザー満足度**: **4.5/5.0以上**✅

---

## 7. 次のアクション（Issue #140-1）

### 即時実行タスク（本日11/6）

1. **ディレクトリ構造の作成**
```bash
cd ~/MySwiftAgent
mkdir -p scripts/{lib,config,test/{unit,integration}}
touch scripts/unified-start.sh
chmod +x scripts/unified-start.sh
```

2. **基本スクリプトの作成**
```bash
# メインスクリプト
touch scripts/unified-start.sh

# ライブラリファイル
touch scripts/lib/{common.sh,process-manager.sh}

# 設定ファイル
touch scripts/config/services.conf
```

3. **既存コードの分析と抽出**
- `dev-start.sh` から再利用可能な関数を特定
- 色付き出力関数のコピー
- サービス起動ロジックの理解

### Day 1 タスクリスト（11/6）

**Morning Session (9:00-13:00)**
- [ ] 09:00-09:30: ディレクトリ構造作成、ファイル初期化
- [ ] 09:30-11:30: unified-start.sh メインフレーム実装
- [ ] 11:30-13:00: lib/common.sh 共通関数実装

**Afternoon Session (14:00-18:00)**
- [ ] 14:00-17:00: lib/process-manager.sh 実装
- [ ] 17:00-18:00: サービス定義（services.conf）作成

**Evening Review (18:00-19:00)**
- [ ] コードレビューとテスト
- [ ] Day 2の準備
- [ ] 進捗報告書作成

---

## 8. 補足情報

### 参考資料
- 既存スクリプト: `/scripts/dev-start.sh`（930行）
- Worktree設定: `/scripts/setup-worktree.sh`（368行）
- ログポリシー: `/docs/design/logging-policy.md`
- 環境変数設計: `/docs/design/environment-variables.md`

### 依存ツール
- **必須**: bash, curl, lsof, pkill
- **推奨**: jq（JSON解析）
- **オプション**: yq（YAML解析、Phase 2）, docker（Phase 3）

### 連絡先
- PO: [Product Owner]
- 技術リード: [Tech Lead]
- QAリード: [QA Lead]

---

**承認欄**

承認者: _______________________
承認日: _______________________
コメント: _______________________

---

**改訂履歴**

| バージョン | 日付 | 変更内容 | 作成者 |
|-----------|------|---------|--------|
| 1.0.0 | 2025-11-06 | 初版作成 | Claude (Opus 4.1) |