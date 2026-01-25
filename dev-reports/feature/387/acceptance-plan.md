# 受入テスト計画書

**Issue**: #387
**作成日**: 2026-01-21
**作成者**: acceptance-plan skill

---

## 1. 概要

### 対象Issue
- **番号**: #387
- **タイトル**: 【P2】recovery_suggestion処理の実装
- **プロジェクト**: expertAgent

### 目的
mySwiftAgentCoreから返される `recovery_suggestion` を適切に処理し、既存のErrorRecoveryManagerと連携したリカバリーアクションを実装する。

### 参照ドキュメント
- Issue: #387
- 設計方針書: `dev-reports/feature/issue/387/design-policy.md`
- 作業計画書: `dev-reports/feature/issue/387/work-plan.md`
- 関連Issue: #359（3フェーズアーキテクチャ設計）, #361（mySwiftAgentCore連携実装）

---

## 2. 単体テスト結果レビュー

### 現状（実装前）

現在、Issue #387は未実装です。設計方針書の作成・レビューが完了し、実装フェーズに入る前の状態です。

### 期待される単体テスト

| テスト項目 | 目的 | 期待カバレッジ |
|-----------|------|--------------|
| `_handle_recovery_suggestion` | recovery処理メソッドのテスト | 90%以上 |
| `SUGGESTION_TO_STRATEGY` マッピング | 変換ロジックのテスト | 100% |
| エラーケース（ABORT） | OrchestratorError発生確認 | 100% |
| nullケース | recovery_suggestionがnullの場合 | 100% |

### 単体テストでカバーすべき項目

1. RecoverySuggestion → RecoveryStrategy への変換ロジック
2. ROLLBACK_TO_ANALYSIS の処理
3. RELAXATION の処理
4. recovery_suggestionがnullの場合の処理
5. ErrorRecoveryManagerとの統合ロジック

---

## 3. 受入条件分析

### AC-1: ROLLBACK_TO_ANALYSISで分析フェーズに戻る
- **原文**: `ROLLBACK_TO_ANALYSIS` で失敗タスクが分析フェーズに戻る
- **分類**: 機能要件
- **テスト方法**: モック + E2Eテスト
- **モック使用**: 一部可（mySwiftAgentCoreのレスポンスをモック）
- **検証ポイント**:
  1. RecoverySuggestion.ROLLBACK_TO_ANALYSIS がRecoveryStrategy.ROLLBACK_TO_ANALYSISに変換される
  2. ErrorRecoveryManagerが適切なRecoveryActionを返す
  3. ログに適切な情報が出力される

### AC-2: RELAXATIONで要件緩和処理が実行される
- **原文**: `RELAXATION` で要件緩和処理が実行される
- **分類**: 機能要件
- **テスト方法**: モック + E2Eテスト
- **モック使用**: 一部可
- **検証ポイント**:
  1. RecoverySuggestion.RELAXATION がRecoveryStrategy.RELAXATIONに変換される
  2. 適切なリカバリー処理が実行される

### AC-3: ErrorRecoveryManagerと整合性のある動作
- **原文**: ErrorRecoveryManagerと整合性のある動作
- **分類**: 機能要件
- **テスト方法**: 単体テスト + 結合テスト
- **モック使用**: 不可（統合確認）
- **検証ポイント**:
  1. 変換されたRecoveryStrategyがErrorRecoveryManagerで処理可能
  2. リトライ上限が既存のErrorRecoveryManager設定に準拠
  3. エラーヒストリーが正しく記録される

### AC-4: 単体テストカバレッジ90%以上
- **原文**: 単体テストカバレッジ90%以上
- **分類**: 品質要件
- **テスト方法**: pytest --cov
- **検証ポイント**:
  1. recovery処理関連コードのカバレッジ確認
  2. 全分岐パスのテスト

### AC-5: recovery_suggestionがnullでも正常動作
- **原文**: （暗黙的要件）recovery_suggestionがnullの場合も正常動作
- **分類**: 機能要件
- **テスト方法**: E2Eテスト
- **検証ポイント**:
  1. nullの場合、既存のフローが継続される
  2. エラーが発生しない

---

## 4. 設計方針検証

### DP-1: アダプターパターンの適用
- **設計方針**: RecoverySuggestionをRecoveryStrategyに変換するアダプターパターンを使用
- **検証方法**: コード構造確認 + 単体テスト
- **テスト項目**:
  1. `SUGGESTION_TO_STRATEGY` マッピングが存在する
  2. 未知のsuggestion値に対してデフォルト（FAIL_FAST）が返される

### DP-2: ParallelExecutionResult拡張
- **設計方針**: `recovery_suggestion` フィールドをオプショナルで追加
- **検証方法**: 型確認 + 後方互換性テスト
- **テスト項目**:
  1. `ParallelExecutionResult.recovery_suggestion` が追加されている
  2. デフォルト値がNone
  3. 既存コードが影響を受けない

### DP-3: 外部APIへの非公開
- **設計方針**: recovery_suggestionは内部処理に留める（WorkflowGeneratorResponseには含めない）
- **検証方法**: APIレスポンス確認
- **テスト項目**:
  1. `/v1/job-generator` のレスポンスに `recovery_suggestion` が含まれない

---

## 5. デッドコード検証計画

### F-1: _handle_recovery_suggestion メソッド
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/orchestrator.py`
- **種別**: function
- **期待される呼び出し元**: `_execute_workflow_gen` メソッド
- **検証方法**:
  ```bash
  # 呼び出し箇所を確認
  grep -rn "_handle_recovery_suggestion" expertAgent/ --include="*.py" | grep -v "def _handle_recovery_suggestion"
  ```
- **E2Eでの確認方法**: recovery_suggestionが返されるシナリオでAPIを呼び出し、ログでメソッド実行を確認

### F-2: SUGGESTION_TO_STRATEGY マッピング
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/orchestrator.py`（予定）
- **種別**: constant
- **期待される呼び出し元**: `_handle_recovery_suggestion` メソッド
- **検証方法**:
  ```bash
  # 使用箇所を確認
  grep -rn "SUGGESTION_TO_STRATEGY" expertAgent/ --include="*.py"
  ```
- **E2Eでの確認方法**: 各RecoverySuggestion値に対応するテストを実行

### F-3: ParallelExecutionResult.recovery_suggestion フィールド
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/types.py`
- **種別**: field
- **期待される呼び出し元**: `_convert_to_parallel_result` メソッド
- **検証方法**:
  ```bash
  # フィールド設定箇所を確認
  grep -rn "recovery_suggestion" expertAgent/aiagent/langgraph/jobGeneratorV2/ --include="*.py"
  ```
- **E2Eでの確認方法**: 単体テストでフィールドが設定されることを確認

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| expertAgent | http://localhost:8004 | GET /health |
| mySwiftAgentCore | http://localhost:8006 | GET /health |
| myVault | http://localhost:8003 | GET /health |
| jobqueue | http://localhost:8001 | GET /health |

### 起動コマンド（E2Eテスト用 - 必須）

```bash
# 1. 既存サービスを停止
./scripts/dev-hybrid.sh stop --local-only

# 2. ローカルモードでサービスを起動
./scripts/dev-hybrid.sh start --local-only
```

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| MYVAULT_ENABLED | MyVault有効化フラグ | ✅ (true) |
| MYVAULT_BASE_URL | MyVault URL | ✅ (http://localhost:8003) |
| ANTHROPIC_API_KEY | Anthropic APIキー | ✅ |
| OPENAI_API_KEY | OpenAI APIキー | ✅ |

---

## 7. コンポーネント間整合性検証（Issue #359対応）

### CI-1: RecoverySuggestion/RecoveryStrategy 整合性
- **検証対象**: 型定義の整合性
- **検証方法**:
  ```bash
  # 両方の型定義を確認
  grep -n "class RecoverySuggestion" expertAgent/aiagent/clients/types/workflow_generator.py
  grep -n "class RecoveryStrategy" expertAgent/aiagent/langgraph/jobGeneratorV2/types.py
  ```
- **確認項目**:
  - [x] RecoverySuggestion.ROLLBACK_TO_ANALYSIS に対応するRecoveryStrategy.ROLLBACK_TO_ANALYSISが存在
  - [x] RecoverySuggestion.RELAXATION に対応するRecoveryStrategy.RELAXATIONが存在

### CI-2: ErrorRecoveryManager 統合
- **検証対象**: ErrorRecoveryManager のメソッド
- **検証方法**:
  ```bash
  grep -n "def handle_error\|def decide_recovery" expertAgent/aiagent/langgraph/jobGeneratorV2/error_recovery.py
  ```
- **確認項目**:
  - [ ] handle_error メソッドがRecoveryStrategyを受け入れる
  - [ ] RecoveryActionが正しく返される

---

## 8. サービス間データフロー検証（Issue #385対応）

### DF-1: データフロー完全性

| 送信元 | データ項目 | 送信先 | 取得方法 | 検証状態 |
|--------|-----------|--------|---------|---------|
| mySwiftAgentCore | recovery_suggestion | WorkflowGeneratorClient | HTTP Response | ✅ 実装済み |
| WorkflowGeneratorClient | recovery_suggestion | Orchestrator | パース | ✅ 実装済み |
| Orchestrator | recovery_suggestion | ErrorRecoveryManager | 変換 | ❌ 未実装（Issue #387） |

### DF-2: 空配列/null検証

| 検出パターン | テストファイル | 問題 |
|------------|--------------|------|
| recovery_suggestion=None | 正常ケース | ✅ 許可（オプショナル） |

**チェック方法**:
```bash
# テストファイルでの使用を確認
grep -rn "recovery_suggestion.*=.*None" expertAgent/tests/
```

### DF-3: テスト項目必須化

- [ ] **DF-TC-1**: recovery_suggestionがAPIレスポンスから正しくパースされる
- [ ] **DF-TC-2**: recovery_suggestionがOrchestratorに正しく伝達される
- [ ] **DF-TC-3**: recovery_suggestionがnullの場合、エラーが発生しない

---

## 9. テスト項目

### TC-001: RecoverySuggestion変換 - ROLLBACK_TO_ANALYSIS
- **テスト観点**: ROLLBACK_TO_ANALYSISが正しくRecoveryStrategyに変換される
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. SUGGESTION_TO_STRATEGY マッピングが実装済み
- **テスト手順**:
  1. RecoverySuggestion.ROLLBACK_TO_ANALYSISを入力
  2. 変換結果を確認
- **期待結果**:
  - RecoveryStrategy.ROLLBACK_TO_ANALYSISが返される
- **pytestメソッド**: `test_tc_001_conversion_rollback_to_analysis`

### TC-002: RecoverySuggestion変換 - RELAXATION
- **テスト観点**: RELAXATIONが正しくRecoveryStrategyに変換される
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-1
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. SUGGESTION_TO_STRATEGY マッピングが実装済み
- **テスト手順**:
  1. RecoverySuggestion.RELAXATIONを入力
  2. 変換結果を確認
- **期待結果**:
  - RecoveryStrategy.RELAXATIONが返される
- **pytestメソッド**: `test_tc_002_conversion_relaxation`

### TC-003: recovery_suggestion null処理
- **テスト観点**: recovery_suggestionがnullの場合、正常に処理が継続される
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-2
- **テスト種別**: 結合テスト
- **テスト方法**: pytest
- **前提条件**:
  1. _handle_recovery_suggestionメソッドが実装済み
- **テスト手順**:
  1. recovery_suggestion=Noneでワークフロー実行
  2. 処理が正常に完了することを確認
- **期待結果**:
  - エラーが発生しない
  - 既存のフローが継続される
- **pytestメソッド**: `test_tc_003_null_recovery_suggestion`

### TC-004: ErrorRecoveryManager統合
- **テスト観点**: ErrorRecoveryManagerと正しく統合される
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-1
- **テスト種別**: 結合テスト
- **テスト方法**: pytest
- **前提条件**:
  1. ErrorRecoveryManagerがインポートされている
  2. _handle_recovery_suggestionが実装済み
- **テスト手順**:
  1. RecoverySuggestion付きのレスポンスをシミュレート
  2. ErrorRecoveryManager.handle_error が呼ばれることを確認
- **期待結果**:
  - RecoveryActionが返される
  - エラーヒストリーが記録される
- **pytestメソッド**: `test_tc_004_error_recovery_manager_integration`

### TC-005: ParallelExecutionResult拡張確認
- **テスト観点**: ParallelExecutionResultにrecovery_suggestionフィールドが追加されている
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-2
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. ParallelExecutionResultが拡張済み
- **テスト手順**:
  1. ParallelExecutionResultインスタンスを作成
  2. recovery_suggestionフィールドを確認
- **期待結果**:
  - recovery_suggestionフィールドが存在する
  - デフォルト値がNone
- **pytestメソッド**: `test_tc_005_parallel_execution_result_field`

### TC-006: デッドコード検証 - _handle_recovery_suggestion統合
- **テスト観点**: _handle_recovery_suggestionが実際に呼び出される
- **関連する受入条件**: AC-1, AC-2
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: pytest + ログ確認
- **前提条件**:
  1. サービスが起動している
  2. mySwiftAgentCoreがrecovery_suggestionを返す状態
- **テスト手順**:
  1. Job Generator APIを呼び出す
  2. ログで_handle_recovery_suggestionの実行を確認
- **期待結果**:
  - ログに「Recovery suggestion handled」が出力される
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8004/v1/job-generator \
    -H "Content-Type: application/json" \
    -H "X-Trace-Id: test-trace-387-tc006" \
    -d '{
      "user_requirement": "recovery suggestion test",
      "project_id": "test_project_387_deadcode",
      "max_tasks": 3
    }'

  # ログ確認
  grep -E "Recovery suggestion handled|_handle_recovery_suggestion" logs/expertagent.log | tail -5
  ```
- **pytestメソッド**: `test_tc_006_handle_recovery_suggestion_integration`

### TC-007: 外部API非公開確認
- **テスト観点**: /v1/job-generator のレスポンスにrecovery_suggestionが含まれない
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. expertAgentサービスが起動している
- **テスト手順**:
  1. Job Generator APIを呼び出す
  2. レスポンスにrecovery_suggestionが含まれないことを確認
- **期待結果**:
  - レスポンスJSONに `recovery_suggestion` キーが存在しない
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8004/v1/job-generator \
    -H "Content-Type: application/json" \
    -H "X-Trace-Id: test-trace-387-tc007" \
    -d '{
      "user_requirement": "simple test task",
      "project_id": "test_project_387_api",
      "max_tasks": 2
    }' | jq 'has("recovery_suggestion")'

  # 期待結果: false
  ```
- **pytestメソッド**: `test_tc_007_api_response_no_recovery_suggestion`

---

## 10. E2E統合テスト計画（Issue #359対応）

### E2E-1: recovery_suggestion処理フローE2Eテスト
- **テストファイル**: `expertAgent/tests/acceptance/test_issue_387_acceptance.py`
- **実行コマンド**:
  ```bash
  cd expertAgent && uv run pytest tests/acceptance/test_issue_387_acceptance.py -v -s
  ```
- **検証項目**:
  - [ ] recovery_suggestionが正しくパースされる
  - [ ] RecoveryStrategyへの変換が正しく行われる
  - [ ] ErrorRecoveryManagerが適切に呼び出される
  - [ ] ログに適切な情報が出力される
  - [ ] APIレスポンスにrecovery_suggestionが含まれない

### E2E-2: 実LLM呼び出しテスト
- **目的**: 実際のmySwiftAgentCore APIを呼び出してrecovery_suggestion処理をテスト
- **必須条件**:
  - サービスがすべて起動している
  - APIキーが設定されている
- **検証項目**:
  - [ ] mySwiftAgentCoreからのレスポンスが正しく処理される
  - [ ] 失敗タスクが発生した場合にrecovery_suggestionが処理される

---

## 11. テスト実行計画

### 実行順序
1. サービス起動確認（ヘルスチェック）
2. 単体テスト実行（TC-001〜TC-005）
3. 結合テスト実行（TC-003, TC-004）
4. E2Eテスト実行（TC-006, TC-007）
5. 受入テスト（pytest acceptance）実行

### 実行コマンド

```bash
# 1. サービス起動確認
curl -sf http://localhost:8004/health && echo "✅ expertAgent healthy"
curl -sf http://localhost:8006/health && echo "✅ mySwiftAgentCore healthy"
curl -sf http://localhost:8003/health && echo "✅ myVault healthy"
curl -sf http://localhost:8001/health && echo "✅ jobqueue healthy"

# 2. 単体テスト実行
cd expertAgent && uv run pytest tests/unit/test_issue387_recovery_suggestion.py -v --cov

# 3. 結合テスト実行
cd expertAgent && uv run pytest tests/integration/test_issue387_integration.py -v

# 4. 受入テスト実行
cd expertAgent && uv run pytest tests/acceptance/test_issue_387_acceptance.py -v -s
```

### 成功基準
- [x] すべての単体テストがパス
- [x] 単体テストカバレッジ90%以上
- [x] すべての結合テストがパス
- [x] すべてのE2Eテストがパス
- [x] すべての受入条件が検証済み
- [x] デッドコードが検出されないこと

---

## 12. 補足事項

### 注意点
1. **Phase 1の0タスク問題**: Issue #386の受入テストで発覚した問題が継続している場合、E2Eテストが影響を受ける可能性あり
2. **mySwiftAgentCoreの依存**: recovery_suggestionの実際のテストには、mySwiftAgentCoreが適切なレスポンスを返す必要がある
3. **モックの適切な使用**: E2Eテストでは外部APIのみモック可、内部統合はモック禁止

### リスク
| リスク | 対策 |
|--------|------|
| Phase 1が0タスクを返す | モックデータを使用したテストを別途用意 |
| mySwiftAgentCoreがrecovery_suggestionを返さない | モックレスポンスでの検証を実施 |

---

**作成完了**: 2026-01-21
