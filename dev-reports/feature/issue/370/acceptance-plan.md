# 受入テスト計画書

**Issue**: #370
**作成日**: 2026-01-17
**作成者**: acceptance-plan (slash command)

---

## 1. 概要

### 対象Issue
- **番号**: #370
- **タイトル**: fix(mySwiftAgentCore): WorkflowRegistrar のワークフロー永続化とログ出力強化
- **プロジェクト**: mySwiftAgentCore
- **重要度**: 🔴 High（データ消失リスク）

### 参照ドキュメント
- Issue: #370
- 設計方針書: `dev-reports/feature/issue/370/design-policy.md`
- E2Eテストスクリプト: `mySwiftAgentCore/dev-reports/feature/issue/364/e2e-test-script.sh`

### 問題の要約
Batch Generation API でワークフローを生成した際、API は `registered: true` を返すが、実際にはワークフローJSONファイルが作成されていない。サーバー再起動時にすべてのワークフローが失われる。

---

## 2. 単体テスト結果レビュー

### カバレッジ（TDD実装前のため推定）
- 現在: N/A（未実装）
- 目標: 90%
- 判定: ⏳ 待機中

### 期待される単体テスト項目
| コンポーネント | テスト項目 | 優先度 |
|---------------|-----------|--------|
| PathValidator | パストラバーサル攻撃パターン | 🔴 必須 |
| PathValidator | プロトタイプ汚染攻撃パターン | 🔴 必須 |
| PathValidator | 空文字・長すぎる入力 | 🔴 必須 |
| WorkflowStorage | save/load/delete操作 | 🔴 必須 |
| WorkflowStorage | アトミック書き込み | 🔴 必須 |
| StorageMonitor | 容量計測・閾値判定 | 🔴 必須 |
| StorageCleanupService | LRU+Age削除戦略 | 🔴 必須 |
| Logger | 各ログレベル・フォーマット | 🟡 推奨 |
| WorkflowRegistrar | 永続化連携 | 🔴 必須 |

---

## 3. 受入条件分析

### AC-1: ワークフローの永続化
- **原文**: 生成されたワークフローが `generated/workflows/{project_id}/` に JSON ファイルとして保存される
- **分類**: 機能要件
- **テスト方法**: E2Eスクリプト + ファイル存在確認
- **モック使用**: 不可（実ファイル操作を検証）
- **検証ポイント**:
  1. ファイルが指定パスに作成される
  2. ファイル名が `{workflow_name}.json` 形式
  3. JSONの内容が妥当

### AC-2: WorkflowStorage 連携
- **原文**: `WorkflowRegistrar` が `taskflowEngine/storage/WorkflowStorage` を使用する
- **分類**: 技術要件
- **テスト方法**: コード構造確認 + E2Eテスト
- **モック使用**: 不可
- **検証ポイント**:
  1. WorkflowStorage が正しく注入されている
  2. save メソッドが呼び出される
  3. プロジェクト単位のディレクトリ構造

### AC-3: 正確なレスポンス
- **原文**: `registered` フラグは実際の永続化結果を反映する
- **分類**: 機能要件
- **テスト方法**: APIレスポンス検証
- **モック使用**: 不可
- **検証ポイント**:
  1. 永続化成功時: `registered: true` + `file_path`
  2. 永続化失敗時: `registered: false` + エラー詳細

### AC-4: ログ出力強化
- **原文**: ワークフロー生成・登録の過程がログで追跡可能
- **分類**: 非機能要件
- **テスト方法**: ログ出力確認
- **モック使用**: 不可
- **検証ポイント**:
  1. 生成開始/完了のログ
  2. 永続化処理のログ（ファイルパス含む）
  3. 構造化ログ（JSON形式）

### AC-5: サーバー再起動後の復元【追加要件】
- **原文**: ユーザー要求に基づく追加テスト項目
- **分類**: 機能要件
- **テスト方法**: サーバー再起動 + E2Eスクリプト
- **モック使用**: 不可
- **検証ポイント**:
  1. サーバー停止前にワークフロー生成
  2. サーバー再起動後もワークフロー利用可能

---

## 4. 設計方針検証

### DP-1: セキュリティ（パストラバーサル対策）
- **設計方針**: PathValidator による入力検証
- **検証方法**: 単体テスト + 異常系E2Eテスト
- **テスト項目**:
  1. `../etc/passwd` を含むprojectIdを拒否
  2. `__proto__` を含むworkflowIdを拒否
  3. 特殊文字（`/`, `\`, `~`）を拒否

### DP-2: ディスク容量管理
- **設計方針**: StorageMonitor + StorageCleanupService
- **検証方法**: 単体テスト（容量監視・クリーンアップ戦略）
- **テスト項目**:
  1. 容量メトリクスが取得できる
  2. 閾値超過を検出できる
  3. クリーンアップが動作する

### DP-3: アトミック書き込み
- **設計方針**: .tmp → rename によるアトミック更新
- **検証方法**: 単体テスト + 異常系テスト
- **テスト項目**:
  1. 書き込み中に中断してもファイルが破損しない
  2. 一時ファイルが残らない

### DP-4: 構造化ログ
- **設計方針**: JSON形式のログ出力
- **検証方法**: ログ出力確認
- **テスト項目**:
  1. ログがJSON形式で出力される
  2. timestamp, level, message, context を含む

---

## 5. デッドコード検証計画

### F-1: WorkflowStorage.save
- **ファイル**: `src/taskflowEngine/storage/WorkflowStorage.ts`
- **種別**: method
- **期待される呼び出し元**: WorkflowRegistrar.register
- **検証方法**:
  ```bash
  grep -rn "storage.save\|this.storage.save" --include="*.ts" mySwiftAgentCore/src/
  ```
- **E2E確認**: Batch Generation API呼び出し → ファイル作成確認

### F-2: PathValidator.validate
- **ファイル**: `src/utils/validation/PathValidator.ts`
- **種別**: function
- **期待される呼び出し元**: WorkflowStorage.save
- **検証方法**:
  ```bash
  grep -rn "PathValidator.validate" --include="*.ts" mySwiftAgentCore/src/
  ```
- **E2E確認**: 不正なprojectIdでAPIを呼び出し → エラーレスポンス確認

### F-3: Logger.info/error
- **ファイル**: `src/utils/logger/Logger.ts`
- **種別**: class method
- **期待される呼び出し元**: 各コンポーネント
- **検証方法**:
  ```bash
  grep -rn "logger.info\|logger.error\|logger.warn" --include="*.ts" mySwiftAgentCore/src/
  ```
- **E2E確認**: API呼び出し → コンソールログ確認

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| mySwiftAgentCore | http://localhost:8006 | GET /health |

### 起動コマンド
```bash
# ハイブリッドモード（推奨）
./scripts/dev-hybrid.sh start --local-only

# 停止コマンド
./scripts/dev-hybrid.sh stop --local-only
```

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| ANTHROPIC_API_KEY | Anthropic APIキー（MyVault経由） | ✅（実LLM呼び出し時） |

### テストデータ
- E2Eテストスクリプト: `mySwiftAgentCore/dev-reports/feature/issue/364/e2e-test-script.sh`
- テスト用タスク: Google検索 → サマリ → メール送信

---

## 7. テスト項目

### TC-001: ワークフロー永続化の基本動作
- **テスト観点**: ワークフロー生成後にJSONファイルが作成される
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: shell script + ファイル確認
- **前提条件**:
  1. mySwiftAgentCore が起動している
  2. APIキーが設定されている
- **テスト手順**:
  1. Batch Generation API を呼び出す
  2. レスポンスで `registered: true` を確認
  3. 指定パスにJSONファイルが存在することを確認
- **期待結果**:
  - HTTPステータス: 200
  - `workflows.task_001.registered`: true
  - ファイル存在: `generated/workflows/default_project/*.json`
- **curlコマンド**:
  ```bash
  # API呼び出し
  ./mySwiftAgentCore/dev-reports/feature/issue/364/e2e-test-script.sh

  # ファイル存在確認
  find mySwiftAgentCore/generated/workflows/ -name "*.json" -newermt "$(date +%Y-%m-%d) 00:00:00"
  ```
- **pytestメソッド**: `test_tc_001_workflow_persistence`

### TC-002: サーバー再起動後のワークフロー復元
- **テスト観点**: サーバー再起動後もワークフローが利用可能
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: サーバー再起動 + E2Eスクリプト
- **前提条件**:
  1. TC-001 が成功している
  2. ワークフローファイルが存在する
- **テスト手順**:
  1. 現在のワークフローファイルを記録
  2. サーバーを停止（`./scripts/dev-hybrid.sh stop --local-only`）
  3. サーバーを起動（`./scripts/dev-hybrid.sh start --local-only`）
  4. ワークフローが復元されていることを確認
- **期待結果**:
  - サーバー起動後、既存ワークフローファイルが保持されている
  - 起動ログに「Workflows restored from storage」が出力される
- **shellコマンド**:
  ```bash
  # 1. E2Eテストでワークフロー生成
  ./mySwiftAgentCore/dev-reports/feature/issue/364/e2e-test-script.sh

  # 2. ファイル存在確認（再起動前）
  ls -la mySwiftAgentCore/generated/workflows/default_project/

  # 3. サーバー再起動
  ./scripts/dev-hybrid.sh stop --local-only
  ./scripts/dev-hybrid.sh start --local-only

  # 4. ファイル存在確認（再起動後）
  ls -la mySwiftAgentCore/generated/workflows/default_project/

  # 5. E2Eテスト再実行
  ./mySwiftAgentCore/dev-reports/feature/issue/364/e2e-test-script.sh
  ```
- **pytestメソッド**: `test_tc_002_workflow_restoration_after_restart`

### TC-003: パストラバーサル攻撃の防御
- **テスト観点**: 不正なprojectIdを拒否する
- **関連する受入条件**: （暗黙のセキュリティ要件）
- **関連する設計方針**: DP-1
- **テスト種別**: セキュリティテスト
- **テスト方法**: curl + エラーレスポンス確認
- **前提条件**:
  1. mySwiftAgentCore が起動している
- **テスト手順**:
  1. `project_id: "../etc/passwd"` で API を呼び出す
  2. エラーレスポンスを確認
- **期待結果**:
  - HTTPステータス: 400
  - エラーメッセージ: "contains invalid characters" または "INVALID_PATH"
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/generator/workflow/batch \
    -H "Content-Type: application/json" \
    -d '{
      "tasks": [{"task_id": "test", "name": "Test", "description": "Test"}],
      "capabilities": [],
      "project_id": "../etc/passwd"
    }'
  ```
- **pytestメソッド**: `test_tc_003_path_traversal_protection`

### TC-004: 構造化ログ出力の確認
- **テスト観点**: ログがJSON形式で出力される
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-4
- **テスト種別**: E2E
- **テスト方法**: APIコール + ログ確認
- **前提条件**:
  1. mySwiftAgentCore が起動している
  2. ログレベルがDEBUG以上
- **テスト手順**:
  1. Batch Generation API を呼び出す
  2. コンソールログを確認
- **期待結果**:
  - ログにJSON形式の出力が含まれる
  - `timestamp`, `level`, `message`, `context` フィールドが存在
- **確認コマンド**:
  ```bash
  # サーバーログを確認（ターミナルに出力される）
  # または
  grep -E '^\{.*"level".*"message"' /path/to/server.log
  ```
- **pytestメソッド**: `test_tc_004_structured_logging`

### TC-005: レスポンスに file_path が含まれる
- **テスト観点**: 永続化成功時にファイルパスが返される
- **関連する受入条件**: AC-3
- **関連する設計方針**: -
- **テスト種別**: E2E
- **テスト方法**: APIレスポンス確認
- **前提条件**:
  1. mySwiftAgentCore が起動している
- **テスト手順**:
  1. Batch Generation API を呼び出す
  2. レスポンスに `file_path` が含まれることを確認
- **期待結果**:
  - `workflows.task_001.file_path` が存在
  - パスが `generated/workflows/{project_id}/` で始まる
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/generator/workflow/batch \
    -H "Content-Type: application/json" \
    -d '{"tasks": [...], "project_id": "default_project"}' | jq '.workflows[].file_path'
  ```
- **pytestメソッド**: `test_tc_005_response_includes_file_path`

### TC-006: E2Eテストスクリプトの完全実行
- **テスト観点**: 既存E2Eスクリプトが期待通り動作する
- **関連する受入条件**: AC-1, AC-2, AC-3
- **関連する設計方針**: -
- **テスト種別**: E2E
- **テスト方法**: shell script
- **前提条件**:
  1. サーバーが起動している
  2. APIキーが設定されている
- **テスト手順**:
  1. サーバー再起動
  2. E2Eスクリプト実行
  3. ファイル作成確認
- **期待結果**:
  - Test 1 (Health Check): ✅ PASS
  - Test 2 (Generator Health): ✅ PASS
  - Test 3 (Batch Generation): ✅ PASS
  - JSONファイルが作成されている
- **shellコマンド**:
  ```bash
  # 1. サーバー再起動
  ./scripts/dev-hybrid.sh stop --local-only
  ./scripts/dev-hybrid.sh start --local-only

  # 2. E2Eテスト実行
  ./mySwiftAgentCore/dev-reports/feature/issue/364/e2e-test-script.sh

  # 3. ファイル確認
  find mySwiftAgentCore/generated/workflows/ -name "*.json" -ls
  ```
- **pytestメソッド**: `test_tc_006_e2e_script_full_execution`

---

## 8. テスト実行計画

### 実行順序
1. **環境準備**
   ```bash
   ./scripts/dev-hybrid.sh stop --local-only
   ./scripts/dev-hybrid.sh start --local-only
   ```

2. **サービス起動確認**
   ```bash
   curl -s http://localhost:8006/health
   ```

3. **TC-006: E2Eテストスクリプト実行**
   ```bash
   ./mySwiftAgentCore/dev-reports/feature/issue/364/e2e-test-script.sh
   ```

4. **TC-001: ファイル永続化確認**
   ```bash
   find mySwiftAgentCore/generated/workflows/ -name "*.json" -newermt "$(date +%Y-%m-%d) 00:00:00" -ls
   ```

5. **TC-002: サーバー再起動テスト**
   ```bash
   ./scripts/dev-hybrid.sh stop --local-only
   ./scripts/dev-hybrid.sh start --local-only
   ls -la mySwiftAgentCore/generated/workflows/default_project/
   ```

6. **TC-003: セキュリティテスト**（異常系）
   ```bash
   curl -s -X POST http://localhost:8006/api/v1/generator/workflow/batch \
     -H "Content-Type: application/json" \
     -d '{"tasks": [{"task_id": "test", "name": "Test", "description": "Test"}], "capabilities": [], "project_id": "../etc/passwd"}'
   ```

### 成功基準
- [x] TC-001: ワークフローファイルが作成される
- [x] TC-002: サーバー再起動後もファイルが保持される
- [x] TC-003: パストラバーサル攻撃が拒否される
- [x] TC-004: ログがJSON形式で出力される
- [x] TC-005: レスポンスにfile_pathが含まれる
- [x] TC-006: E2Eスクリプトが全て成功する

---

## 9. 補足事項

### ユーザー指定の追加テスト手順

ユーザーから指定された具体的なテスト手順：

```bash
# 1. サーバー停止
./scripts/dev-hybrid.sh stop --local-only

# 2. サーバー起動
./scripts/dev-hybrid.sh start --local-only

# 3. E2Eテスト実行
./mySwiftAgentCore/dev-reports/feature/issue/364/e2e-test-script.sh

# 4. ワークフローファイル確認
find mySwiftAgentCore/generated/workflows/ -name "*.json" -ls
```

### テスト結果の判定基準

| 項目 | 成功条件 |
|------|---------|
| E2Eスクリプト | Test 1-3 すべて PASS |
| ファイル作成 | `generated/workflows/` に `.json` ファイルが存在 |
| サーバー再起動後 | ファイルが保持され、APIが正常動作 |

### 注意事項

1. **APIキー**: 実LLM呼び出しには MyVault に `ANTHROPIC_API_KEY` が必要
2. **ディレクトリ作成**: `generated/workflows/` ディレクトリは自動作成される設計
3. **ログ確認**: 構造化ログはターミナルに直接出力される

---

## 10. 受入テスト実行チェックリスト

```bash
# ===== 受入テスト実行チェックリスト =====

# 準備
[ ] APIキーがMyVaultに設定されている
[ ] 他のプロセスがポート8006を使用していない

# 環境準備
[ ] ./scripts/dev-hybrid.sh stop --local-only
[ ] ./scripts/dev-hybrid.sh start --local-only
[ ] curl -s http://localhost:8006/health → {"status":"healthy"}

# TC-006: E2Eスクリプト実行
[ ] ./mySwiftAgentCore/dev-reports/feature/issue/364/e2e-test-script.sh
[ ] Test 1 (Health Check): ✅ PASS
[ ] Test 2 (Generator Health): ✅ PASS
[ ] Test 3 (Batch Generation): ✅ PASS

# TC-001: ファイル永続化確認
[ ] find mySwiftAgentCore/generated/workflows/ -name "*.json" → ファイルあり

# TC-002: 再起動テスト
[ ] ./scripts/dev-hybrid.sh stop --local-only
[ ] ./scripts/dev-hybrid.sh start --local-only
[ ] ls -la mySwiftAgentCore/generated/workflows/default_project/ → ファイル保持

# TC-003: セキュリティテスト
[ ] 不正なproject_idでAPI呼び出し → エラーレスポンス

# 最終確認
[ ] すべてのテスト項目が成功
```
