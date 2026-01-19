# 受入テスト計画書

**Issue**: #378
**作成日**: 2026-01-19
**作成者**: acceptance-plan-agent

---

## 1. 概要

### 対象Issue
- **番号**: #378
- **タイトル**: fix(taskflowEngine): ワークフローストレージの責務分離と優先順位の明確化
- **プロジェクト**: mySwiftAgentCore

### 参照ドキュメント
- Issue: #378
- 実装計画書: `/Users/maenokota/.claude/plans/twinkling-mapping-flask.md`

### 実装概要
Issue #378では以下の問題を解決する実装が行われた：
1. `register()`でメモリ登録成功でもstorage失敗なら`success:false`を返す問題
2. 起動時に`config/taskflow/projects/`が読み込まれない問題
3. 部分成功時のAPIレスポンスが矛盾（`success:false`なのに`reloadedCount>0`）する問題

---

## 2. 単体テスト結果レビュー

### カバレッジ
- 現在: 全1373テスト合格
- 目標: 90%
- 判定: ✅ PASS

### テスト品質評価
| 指標 | 値 | 判定 |
|------|-----|------|
| 総テスト数 | 1373 | - |
| Issue #378関連テスト数 | 約20 | ✅ |
| パステスト | 1373 | ✅ |
| 失敗テスト | 0 | ✅ |

### Issue #378用単体テスト
以下のテストファイルにIssue #378専用テストが追加済み：
- `tests/unit/taskflowGeneratorAgent/generator/WorkflowRegistrar.test.ts`
  - `describe('WorkflowRegistrar - registerDetailed (Issue #378)')`
  - `registerDetailed - status: success`
  - `registerDetailed - status: partial_success`
  - `registerDetailed - status: failed`
  - `registerBatchDetailed` テスト
- `tests/unit/taskflowEngine/loader/WorkflowReloader.test.ts`
  - `describe('WorkflowReloader - status field (Issue #378)')`
  - `reloadProject - status` テスト
  - `reloadAll - status` テスト

### 単体テストでカバーされていない項目
1. 実際のファイルシステムを使用したconfig読み込み動作
2. 実際のHTTP APIを通じたreload動作
3. サーバー起動時のconfig優先読み込み動作

---

## 3. 受入条件分析

### AC-1: ストレージの責務を明確化
- **原文**: `generated/workflows/`: 動的生成されたワークフロー（一時保存）、`config/taskflow/projects/`: 手動定義されたワークフロー（永続保存）
- **分類**: 機能要件
- **テスト方法**: ファイルシステム確認 + API確認
- **検証ポイント**:
  1. `config/taskflow/projects/`からワークフローが読み込まれる
  2. `generated/workflows/`からもワークフローが読み込まれる
  3. 同一ワークフローがある場合、`config/`が優先される

### AC-2: 優先順位ルールを定義
- **原文**: 案1: `config/`を常に優先
- **分類**: 機能要件
- **テスト方法**: E2Eテスト
- **検証ポイント**:
  1. `initialize()`で`config/`が先に読み込まれる
  2. `generated/`からの読み込み時に`config/`で読み込み済みのワークフローはスキップされる
  3. `loadedFromConfig` Setで追跡される

### AC-3: reload API実行時に`config/`から上書きする動作を保証
- **原文**: reload API実行時に`config/`から上書きする動作を保証
- **分類**: 機能要件
- **テスト方法**: curl / pytest
- **検証ポイント**:
  1. `POST /api/v1/taskflow/reload` が正常動作する
  2. レスポンスに`status`フィールドが含まれる（`success` | `partial_success` | `failed`）
  3. 部分成功時に`success: true`かつ`status: partial_success`が返る

### AC-4: 部分成功モデルの実装
- **原文**: 部分成功時のAPIレスポンスが矛盾（`success:false`なのに`reloadedCount>0`）を修正
- **分類**: 機能要件
- **テスト方法**: pytest / curl
- **検証ポイント**:
  1. 全成功: `status: 'success'`, `success: true`
  2. 部分成功: `status: 'partial_success'`, `success: true`, `failedCount > 0`
  3. 全失敗: `status: 'failed'`, `success: false`

---

## 4. 設計方針検証

### DP-1: 3-state statusモデル
- **設計方針**: `RegistrationStatus = 'success' | 'partial_success' | 'failed'`
- **検証方法**: 型定義確認 + E2Eテスト
- **テスト項目**:
  1. `determineStatus()`が正しいステータスを返す
  2. APIレスポンスに`status`フィールドが含まれる

### DP-2: 後方互換性
- **設計方針**: `success: boolean`フィールドを維持（`status !== 'failed'`）
- **検証方法**: APIレスポンス確認
- **テスト項目**:
  1. レスポンスに`success`フィールドが含まれる
  2. `status: 'partial_success'`の時`success: true`

### DP-3: Config優先読み込み
- **設計方針**: `initialize()`でconfig/を先に読み込み、generated/は上書きしない
- **検証方法**: サーバー起動ログ確認 + E2E
- **テスト項目**:
  1. サーバー起動時に`config/taskflow/projects/`から読み込まれる
  2. 同一ワークフローがgenerated/にあっても上書きされない

---

## 5. デッドコード検証計画

### F-1: RegistrationStatus型
- **ファイル**: `src/taskflowGeneratorAgent/types/registration.ts`
- **種別**: type
- **検証方法**:
  ```bash
  grep -rn "RegistrationStatus" --include="*.ts" | grep -v "registration.ts" | head -20
  ```
- **E2E確認**: WorkflowReloaderとWorkflowRegistrarで使用されていることを確認

### F-2: determineStatus関数
- **ファイル**: `src/taskflowGeneratorAgent/types/registration.ts`
- **種別**: function
- **検証方法**:
  ```bash
  grep -rn "determineStatus" --include="*.ts" | grep -v "registration.ts"
  ```
- **E2E確認**: WorkflowReloaderとWorkflowRegistrarで呼び出されている

### F-3: registerDetailed メソッド
- **ファイル**: `src/taskflowGeneratorAgent/generator/WorkflowRegistrar.ts`
- **種別**: method
- **検証方法**:
  ```bash
  grep -rn "registerDetailed" --include="*.ts" | grep -v "WorkflowRegistrar.ts"
  ```
- **E2E確認**: APIハンドラで使用可能（将来の拡張用）

### F-4: loadFromConfigDirectory メソッド
- **ファイル**: `src/taskflowGeneratorAgent/generator/WorkflowRegistrar.ts`
- **種別**: private method
- **検証方法**: `initialize()`から呼び出されることを確認
- **E2E確認**: サーバー起動時に実行される

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| mySwiftAgentCore | http://localhost:8006 | GET /health |

### 起動コマンド
```bash
# mySwiftAgentCoreディレクトリで
cd mySwiftAgentCore
npm run dev

# または、ハイブリッドモード
./scripts/dev-hybrid.sh start --local-only
```

### テストデータ準備
```bash
# config/taskflow/projects/default_project/workflows/ にテスト用ワークフローを配置
mkdir -p config/taskflow/projects/default_project/workflows
cat > config/taskflow/projects/default_project/workflows/test_workflow.json << 'EOF'
{
  "workflow_name": "test_workflow",
  "steps": [
    {
      "id": "step1",
      "type": "llm",
      "config": {},
      "params": {}
    }
  ],
  "input_schema": {"type": "object", "properties": {}},
  "output_schema": {"type": "object", "properties": {}},
  "output": {}
}
EOF
```

---

## 7. テスト項目

### TC-001: 部分成功モデル - 全成功時のステータス
- **テスト観点**: 全ワークフローが成功した場合に`status: 'success'`が返る
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. mySwiftAgentCoreが起動している
  2. `config/taskflow/projects/default_project/`にワークフローが存在する
- **テスト手順**:
  1. Reload APIを呼び出す
  2. レスポンスを確認する
- **期待結果**:
  - HTTPステータス: 200
  - `status: 'success'`
  - `success: true`
  - `reloadedCount >= 0`
  - `failedCount: 0`
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/taskflow/reload \
    -H "Content-Type: application/json" \
    -d '{"project": "default_project"}' | jq '{status, success, reloadedCount, failedCount}'
  ```
- **pytestメソッド**: `test_tc_001_reload_all_success_status`

### TC-002: 部分成功モデル - APIレスポンス形式
- **テスト観点**: Reload APIレスポンスに必要なフィールドが含まれる
- **関連する受入条件**: AC-3, AC-4
- **関連する設計方針**: DP-1, DP-2
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. mySwiftAgentCoreが起動している
- **テスト手順**:
  1. Reload APIを呼び出す
  2. レスポンスのフィールドを確認する
- **期待結果**:
  - `status`フィールドが存在する
  - `success`フィールドが存在する（後方互換性）
  - `reloadedCount`フィールドが存在する
  - `failedCount`フィールドが存在する
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/taskflow/reload \
    -H "Content-Type: application/json" \
    -d '{"project": "default_project"}' | jq 'keys'
  ```
- **pytestメソッド**: `test_tc_002_reload_response_fields`

### TC-003: Config優先読み込み - サーバー起動時
- **テスト観点**: サーバー起動時に`config/taskflow/projects/`からワークフローが読み込まれる
- **関連する受入条件**: AC-1, AC-2
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: ログ確認 + API
- **前提条件**:
  1. `config/taskflow/projects/default_project/workflows/`にテストワークフローが配置されている
- **テスト手順**:
  1. mySwiftAgentCoreを起動する
  2. 起動ログを確認する
  3. 登録されたワークフローをAPIで確認する
- **期待結果**:
  - ログに "Loading workflows from config directory" が出力される
  - ログに "Loaded workflows from config" が出力される
- **確認コマンド**:
  ```bash
  npm run dev 2>&1 | grep -E "config directory|Loaded.*config"
  ```
- **pytestメソッド**: `test_tc_003_config_priority_loading`

### TC-004: determineStatus関数 - 空の場合
- **テスト観点**: total=0の場合に`'success'`が返る
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-1
- **テスト種別**: 単体（E2E確認用）
- **テスト方法**: pytest
- **前提条件**: なし
- **テスト手順**:
  1. ワークフローが存在しないプロジェクトでreloadを実行
- **期待結果**:
  - `status: 'success'`
  - `reloadedCount: 0`
  - `failedCount: 0`
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/taskflow/reload \
    -H "Content-Type: application/json" \
    -d '{"project": "nonexistent_project"}' | jq '{status, reloadedCount, failedCount}'
  ```
- **pytestメソッド**: `test_tc_004_empty_project_status`

### TC-005: デッドコード検証 - RegistrationStatus使用確認
- **テスト観点**: RegistrationStatus型が実際に使用されている
- **関連する受入条件**: -
- **関連する設計方針**: DP-1
- **テスト種別**: コード検証
- **テスト方法**: grep
- **前提条件**: なし
- **テスト手順**:
  1. RegistrationStatusの参照箇所を検索
- **期待結果**:
  - `WorkflowReloader.ts`で使用されている
  - `WorkflowRegistrar.ts`で使用されている
- **確認コマンド**:
  ```bash
  grep -rn "RegistrationStatus" mySwiftAgentCore/src --include="*.ts" | grep -v "registration.ts"
  ```
- **pytestメソッド**: `test_tc_005_registration_status_not_dead_code`

### TC-006: デッドコード検証 - determineStatus使用確認
- **テスト観点**: determineStatus関数が実際に使用されている
- **関連する受入条件**: -
- **関連する設計方針**: DP-1
- **テスト種別**: コード検証
- **テスト方法**: grep
- **前提条件**: なし
- **テスト手順**:
  1. determineStatusの参照箇所を検索
- **期待結果**:
  - `WorkflowReloader.ts`で呼び出されている
  - `WorkflowRegistrar.ts`で呼び出されている
- **確認コマンド**:
  ```bash
  grep -rn "determineStatus" mySwiftAgentCore/src --include="*.ts" | grep -v "registration.ts"
  ```
- **pytestメソッド**: `test_tc_006_determine_status_not_dead_code`

---

## 8. テスト実行計画

### 実行順序
1. サービス起動確認（ヘルスチェック）
2. デッドコード検証（grep）
3. curl APIテスト実行
4. pytest受入テスト実行

### 成功基準
- [ ] すべてのpytestテストがパス
- [ ] すべての受入条件が検証済み
- [ ] デッドコードが検出されないこと
- [ ] APIレスポンスに`status`フィールドが含まれること
- [ ] 部分成功時に`success: true`かつ`status: partial_success`が返ること

### 受入テストファイル
```
mySwiftAgentCore/tests/acceptance/test_issue_378_acceptance.py
```

---

## 9. 補足事項

### 実装済みファイル一覧
| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `src/taskflowGeneratorAgent/types/registration.ts` | 新規 | 部分成功モデルの型定義 |
| `src/taskflowGeneratorAgent/types/index.ts` | 修正 | 新型定義のエクスポート追加 |
| `src/taskflowGeneratorAgent/generator/WorkflowRegistrar.ts` | 修正 | registerDetailed()追加、initialize()修正 |
| `src/taskflowEngine/loader/WorkflowReloader.ts` | 修正 | status フィールド追加 |
| `src/api/routes/taskflow-reload.ts` | 修正 | APIレスポンス整合性 |

### 後方互換性
- `RegistrationResult.success`は維持（`status !== 'failed'`で計算）
- `ProjectReloadResult.success`は維持（`status !== 'failed'`で計算）
- 既存APIを呼び出すコードは変更不要
