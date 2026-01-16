# 受入テスト計画書

**Issue**: #368
**作成日**: 2026年1月17日
**作成者**: acceptance-plan (slash command)

---

## 1. 概要

### 対象Issue
- **番号**: #368
- **タイトル**: taskflowGeneratorAgent: WorkflowRegistrar 統合とステータス更新の修正
- **プロジェクト**: mySwiftAgentCore
- **種別**: bug fix

### 参照ドキュメント
- Issue: #368
- 設計方針書: `dev-reports/feature/issue/368/design-policy.md`
- アーキテクチャレビュー: `dev-reports/feature/issue/368/architecture-review.md`
- 親Issue: #364

### 問題の概要

1. **WorkflowRegistrar が未使用**: インスタンス化されるが `register()` メソッドが呼ばれていない
2. **ステータス更新のバグ**: 失敗時も `'completed'` を返している

---

## 2. 単体テスト結果レビュー

### 現在のテストカバレッジ（推定）

Issue #368 は未実装のため、TDD結果は存在しません。関連する既存テストをレビューします。

### 既存テスト分析

| テストファイル | テスト数 | カバー範囲 | 問題点 |
|--------------|---------|----------|--------|
| `handlers.test.ts` | 10 | API入力検証、基本レスポンス | WorkflowRegistrar 統合テストなし |
| `BatchProcessor.test.ts` | 9 | 並列実行、部分失敗 | workflowDefinitions 返却テストなし |

### モック使用の妥当性

**handlers.test.ts**:
- ✅ LLMClient をモック（適切）
- ✅ WorkflowRegistry をモック（適切）
- ⚠️ WorkflowRegistrar.register() の呼び出し検証なし（不足）

**BatchProcessor.test.ts**:
- ✅ WorkflowGenerator をモック（適切）
- ⚠️ 返却される workflowDefinitions の検証なし（不足）

### 単体テストでカバーされていない項目

1. **WorkflowRegistrar.register() が実際に呼ばれること**
2. **BatchProcessor が workflowDefinitions を返却すること**
3. **失敗時のステータスが 'failed' になること**
4. **登録失敗時の registered: false 設定**

---

## 3. 受入条件分析

### AC-1: 生成成功したワークフローが WorkflowRegistrar.register() で登録される

- **原文**: 生成成功したワークフローが `WorkflowRegistrar.register()` で登録される
- **分類**: 機能要件
- **テスト方法**: 単体テスト（モック検証）+ E2E API テスト
- **モック使用**: 単体テストでは可、E2Eでは不可
- **検証ポイント**:
  1. WorkflowRegistrar.register() が呼び出されること
  2. 正しい TaskFlowDefinition が渡されること
  3. 登録成功時に registered: true が設定されること
  4. workflow_id が返却されること

### AC-2: 登録失敗時は適切なエラーハンドリングが行われる

- **原文**: 登録失敗時は適切なエラーハンドリングが行われる
- **分類**: 機能要件
- **テスト方法**: 単体テスト（モック検証）
- **モック使用**: 可（登録失敗をモック）
- **検証ポイント**:
  1. 登録失敗時も処理が継続すること
  2. registered: false が設定されること
  3. エラーがログに記録されること
  4. 他のワークフロー登録に影響しないこと

### AC-3: 失敗時のステータスが 'failed' になる

- **原文**: 失敗時のステータスが `'failed'` になる
- **分類**: 機能要件
- **テスト方法**: 単体テスト + E2E API テスト
- **モック使用**: 単体テストでは可
- **検証ポイント**:
  1. batchResult.success が false の場合、status が 'failed'
  2. batchResult.success が true の場合、status が 'completed'
  3. statusStorage に正しいステータスが保存されること

### AC-4: 単体テストで登録フローを検証

- **原文**: 単体テストで登録フローを検証
- **分類**: テスト要件
- **テスト方法**: 単体テスト
- **検証ポイント**:
  1. テストファイルが存在すること
  2. 各受入条件がテストでカバーされていること
  3. テストがすべてパスすること

---

## 4. 設計方針検証

### DP-1: InternalBatchResult 型の導入

- **設計方針**: BatchProcessor が内部型 `InternalBatchResult` を返却し、workflowDefinitions を含める
- **検証方法**: コード検証 + 型テスト
- **テスト項目**:
  1. `InternalBatchResult` 型が定義されていること
  2. `workflowDefinitions` フィールドが含まれること
  3. BatchProcessor.processBatch() の返り値に workflowDefinitions が含まれること

### DP-2: Handler での WorkflowRegistrar 使用

- **設計方針**: Handler が WorkflowRegistrar.register() を実際に呼び出す
- **検証方法**: 単体テスト（spy）+ 結合テスト
- **テスト項目**:
  1. `void new WorkflowRegistrar()` ではなく、実際にインスタンスを使用
  2. 各成功ワークフローに対して register() が呼ばれること
  3. project_id が正しく渡されること

### DP-3: エラー時の部分的成功処理

- **設計方針**: 登録エラーは個別に記録し、処理は継続
- **検証方法**: 単体テスト
- **テスト項目**:
  1. 一部の登録が失敗しても全体は継続
  2. 失敗したワークフローのみ registered: false
  3. 成功したワークフローは正しく登録

### DP-4: ステータス更新の修正

- **設計方針**: `status: batchResult.success ? 'completed' : 'failed'`
- **検証方法**: 単体テスト + コードレビュー
- **テスト項目**:
  1. handlers.ts:138 の修正確認
  2. 失敗時のレスポンスに status: 'failed' が含まれること

---

## 5. デッドコード検証計画

### F-1: InternalBatchResult 型

- **ファイル**: `src/taskflowGeneratorAgent/generator/BatchProcessor.ts`
- **種別**: interface
- **検証方法**:
  ```bash
  grep -rn "InternalBatchResult" mySwiftAgentCore/src/ --include="*.ts"
  ```
- **E2E確認**: BatchProcessor の返り値を通じて Handler で使用されること

### F-2: workflowDefinitions フィールド

- **ファイル**: `src/taskflowGeneratorAgent/generator/BatchProcessor.ts`
- **種別**: property
- **検証方法**:
  ```bash
  grep -rn "workflowDefinitions" mySwiftAgentCore/src/ --include="*.ts"
  ```
- **E2E確認**: Handler が workflowDefinitions を WorkflowRegistrar.register() に渡すこと

### F-3: WorkflowRegistrar.register() 呼び出し

- **ファイル**: `src/taskflowGeneratorAgent/api/handlers.ts`
- **種別**: method call
- **検証方法**:
  ```bash
  grep -rn "registrar.register" mySwiftAgentCore/src/ --include="*.ts"
  ```
- **E2E確認**: 実際のワークフロー生成後に登録が完了すること

---

## 6. テスト環境

### 必須サービス

| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| mySwiftAgentCore | http://localhost:8106 | GET /health |
| myVault（Capability取得用） | http://localhost:8103 | GET /health |

### 起動コマンド

```bash
# 推奨: ハイブリッドモード（Platform=Docker, Agent=ローカル）
./scripts/dev-hybrid.sh

# または単体起動
cd mySwiftAgentCore && npm run dev
```

### 環境変数

| 変数名 | 説明 | 必須 |
|--------|------|------|
| OPENAI_API_KEY | OpenAI APIキー | ✅ (LLM呼び出し時) |
| ANTHROPIC_API_KEY | Anthropic APIキー | ✅ (LLM呼び出し時) |
| MYVAULT_URL | myVault URL | 推奨 |

### テストデータ

- 有効な TaskGenerationRequest
- 有効な Capability 定義
- WorkflowRegistry のインスタンス

---

## 7. テスト項目

### TC-001: BatchProcessor が workflowDefinitions を返却する

- **テスト観点**: BatchProcessor の拡張された返り値の検証
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. モック WorkflowGenerator が準備されている
  2. テストタスクが定義されている
- **テスト手順**:
  1. BatchProcessor.processBatch() を実行
  2. 返り値に workflowDefinitions が含まれることを確認
  3. workflowDefinitions[task_id] が TaskFlowDefinition 形式であることを確認
- **期待結果**:
  - result.workflowDefinitions が Record<string, TaskFlowDefinition>
  - 各タスクIDに対応するワークフロー定義が存在
- **pytestメソッド**: N/A (vitest)
- **vitestメソッド**: `test_batch_processor_returns_workflow_definitions`

### TC-002: Handler が WorkflowRegistrar.register() を呼び出す

- **テスト観点**: WorkflowRegistrar の実使用検証
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-2
- **テスト種別**: 単体テスト
- **テスト方法**: vitest (spy)
- **前提条件**:
  1. モック依存関係が準備されている
  2. 有効なバッチリクエストが定義されている
- **テスト手順**:
  1. WorkflowRegistrar.register() に spy を設定
  2. createBatchGenerationHandler() を実行
  3. spy が呼び出されたことを確認
- **期待結果**:
  - register() が各成功タスクに対して呼ばれる
  - 正しい TaskFlowDefinition と project_id が渡される
- **vitestメソッド**: `test_handler_calls_workflow_registrar_register`

### TC-003: 登録成功時に registered: true が設定される

- **テスト観点**: 登録成功の反映確認
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-2
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. WorkflowRegistrar.register() が成功を返す
- **テスト手順**:
  1. バッチ生成リクエストを実行
  2. レスポンスの workflows[task_id].registered を確認
- **期待結果**:
  - registered: true
  - workflow_id が設定されている
- **vitestメソッド**: `test_successful_registration_sets_registered_true`

### TC-004: 登録失敗時に registered: false が設定される

- **テスト観点**: 登録失敗の適切な処理
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-3
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. WorkflowRegistrar.register() が失敗を返す
- **テスト手順**:
  1. register() が { success: false } を返すようモック
  2. バッチ生成リクエストを実行
  3. レスポンスを確認
- **期待結果**:
  - registered: false
  - 処理は継続（他のタスクは成功）
- **vitestメソッド**: `test_failed_registration_sets_registered_false`

### TC-005: 失敗時のステータスが 'failed' になる

- **テスト観点**: ステータス更新バグの修正確認
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-4
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. BatchProcessor が失敗結果を返す
- **テスト手順**:
  1. batchResult.success = false となるリクエストを実行
  2. statusStorage のステータスを確認
- **期待結果**:
  - status: 'failed' (status: 'completed' ではない)
- **vitestメソッド**: `test_failed_batch_returns_failed_status`

### TC-006: 成功時のステータスが 'completed' になる

- **テスト観点**: 正常系のステータス確認
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-4
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. BatchProcessor が成功結果を返す
- **テスト手順**:
  1. batchResult.success = true となるリクエストを実行
  2. statusStorage のステータスを確認
- **期待結果**:
  - status: 'completed'
- **vitestメソッド**: `test_successful_batch_returns_completed_status`

### TC-007: デッドコード検証 - InternalBatchResult 使用確認

- **テスト観点**: デッドコード検出
- **関連する受入条件**: AC-1, AC-4
- **関連する設計方針**: DP-1
- **テスト種別**: 静的検証
- **テスト方法**: grep
- **前提条件**:
  1. 実装が完了している
- **テスト手順**:
  ```bash
  # InternalBatchResult が定義されていることを確認
  grep -n "interface InternalBatchResult" mySwiftAgentCore/src/**/*.ts

  # workflowDefinitions が使用されていることを確認
  grep -rn "workflowDefinitions" mySwiftAgentCore/src/ --include="*.ts" | grep -v "test"
  ```
- **期待結果**:
  - 定義: 1箇所
  - 使用箇所: 2箇所以上（BatchProcessor + Handler）
- **pytestメソッド**: N/A (手動検証)

### TC-008: E2E API テスト - ワークフロー登録確認

- **テスト観点**: 実際のAPI呼び出しでの動作確認
- **関連する受入条件**: AC-1, AC-3
- **関連する設計方針**: DP-2, DP-4
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. mySwiftAgentCore サービスが起動している
  2. APIキーが設定されている
- **テスト手順**:
  1. POST /api/v1/generator/workflow/batch を実行
  2. レスポンスを確認
- **期待結果**:
  - HTTPステータス: 200 または 207
  - workflows[task_id].registered が true または false
  - success フィールドが結果を反映
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8106/api/v1/generator/workflow/batch \
    -H "Content-Type: application/json" \
    -d '{
      "tasks": [
        {
          "task_id": "test_task_1",
          "name": "Test Task",
          "description": "Integration test task",
          "interface": {
            "input": {"data": "string"},
            "output": {"result": "string"}
          }
        }
      ],
      "capabilities": [
        {"id": "cap_1", "name": "Test Cap", "category": "api", "status": "available"}
      ],
      "project_id": "test_project",
      "options": {
        "validate_before_register": true
      }
    }'
  ```
- **pytestメソッド**: `test_issue_368_workflow_registration_e2e`

---

## 8. テスト実行計画

### 実行順序

1. **サービス起動確認**（ヘルスチェック）
   ```bash
   curl -s http://localhost:8106/health | jq .
   ```

2. **単体テスト実行**
   ```bash
   cd mySwiftAgentCore
   npm test -- --grep "Issue #368"
   # または
   npm test -- tests/unit/taskflowGeneratorAgent/api/handlers.test.ts
   npm test -- tests/unit/taskflowGeneratorAgent/generator/BatchProcessor.test.ts
   ```

3. **デッドコード検証**（TC-007）
   ```bash
   # grep コマンドで静的検証
   grep -rn "InternalBatchResult\|workflowDefinitions\|registrar.register" \
     mySwiftAgentCore/src/taskflowGeneratorAgent/ --include="*.ts"
   ```

4. **E2E API テスト実行**（TC-008）
   ```bash
   # curlでAPIテスト
   ```

### 成功基準

- [ ] TC-001: BatchProcessor が workflowDefinitions を返却する ✅
- [ ] TC-002: Handler が WorkflowRegistrar.register() を呼び出す ✅
- [ ] TC-003: 登録成功時に registered: true が設定される ✅
- [ ] TC-004: 登録失敗時に registered: false が設定される ✅
- [ ] TC-005: 失敗時のステータスが 'failed' になる ✅
- [ ] TC-006: 成功時のステータスが 'completed' になる ✅
- [ ] TC-007: デッドコード検証 - 使用箇所が存在する ✅
- [ ] TC-008: E2E API テストがパス ✅

### 失敗時の対応

| 失敗パターン | 対応 |
|-------------|------|
| 単体テスト失敗 | 実装を修正し、再テスト |
| デッドコード検出 | 統合コードを追加し、再検証 |
| E2E失敗（サービス起動不可） | 環境構築を確認 |
| E2E失敗（機能不具合） | ログを確認し、実装を修正 |

---

## 9. 補足事項

### 注意事項

1. **後方互換性**: BatchGenerationResponse の公開型は変更しない。InternalBatchResult は内部型として扱う。
2. **トレーシング**: Langfuse統合への影響なし（trace_url は引き続き返却）
3. **並行処理**: 登録処理は順次実行（同時実行による競合を避けるため）

### 関連する過去のIssue

- Issue #364: 親Issue（handlers.ts の基本実装）
- Issue #367: RETRY_WITH_FEEDBACK 実装（同じファイルを編集）

### メモリ参照

- `project_overview`: mySwiftAgentCore のアーキテクチャ
- `coding_style_conventions`: TypeScript コーディング規約
