# Phase 2 作業計画: 全ノード/ルーターユニットテスト

**作成日**: 2025-10-24
**予定工数**: 2-3日（約16-24時間）
**目標**: 63テストの実装とPASS

---

## 📋 目的

Phase 1で作成したテストインフラを活用し、全ワークフローノードとルーターの包括的なユニットテストを実装します。これにより、ワークフロー全体の品質を保証し、将来的なバグを防止します。

---

## 🎯 Phase 2の目標

### 主要目標

1. **全ノードのユニットテスト実装** (33テスト)
   - 各ノードの正常系・異常系を網羅
   - retry_count処理の正確性を検証
   - LLM API呼び出しのモック化

2. **ルーター追加テスト実装** (15テスト)
   - より複雑なシナリオ
   - エッジケースの網羅

3. **ヘルパー関数テスト実装** (15テスト)
   - モックヘルパーの動作検証
   - フィクスチャの正確性確認

### 副次的目標

- API-key-free率 100%維持
- テスト実行時間 < 1秒（高速）
- カバレッジ90%以上達成

---

## 📊 実装計画詳細

### Phase 2-1: requirement_analysis_node テスト（6テスト）

**ファイル**: `tests/unit/test_requirement_analysis_node.py`

**テストケース**:

| # | テスト名 | 内容 | 優先度 |
|---|---------|------|--------|
| 1 | `test_requirement_analysis_success` | 正常系：要求分析成功、task_breakdown生成 | High |
| 2 | `test_requirement_analysis_with_llm_error` | LLM APIエラー時のエラーハンドリング | High |
| 3 | `test_requirement_analysis_empty_response` | LLM応答が空の場合の処理 | Medium |
| 4 | `test_requirement_analysis_invalid_json` | 不正なJSON応答の処理 | Medium |
| 5 | `test_requirement_analysis_with_retries` | retry_count > 0での動作 | Medium |
| 6 | `test_requirement_analysis_missing_user_request` | user_request欠落時のエラー | Low |

**モック対象**:
- `create_llm_with_fallback()` - LLMインスタンス生成
- LLM応答データ（`REQUIREMENT_ANALYSIS_SUCCESS` フィクスチャ使用）

**検証項目**:
- ✅ task_breakdownが正しく生成される
- ✅ エラー時にerror_messageが設定される
- ✅ retry_countが適切に処理される

---

### Phase 2-2: evaluator_node テスト（8テスト）

**ファイル**: `tests/unit/test_evaluator_node.py`

**テストケース**:

| # | テスト名 | 内容 | 優先度 |
|---|---------|------|--------|
| 1 | `test_evaluator_after_task_breakdown_success` | タスク分解後の評価成功 | High |
| 2 | `test_evaluator_after_task_breakdown_failure` | タスク分解後の評価失敗、retry_count++ | High |
| 3 | `test_evaluator_after_interface_definition_success` | インターフェース定義後の評価成功 | High |
| 4 | `test_evaluator_after_interface_definition_failure` | インターフェース定義後の評価失敗、retry_count++ | High |
| 5 | `test_evaluator_with_infeasible_tasks` | 実現不可能タスク検出 | Medium |
| 6 | `test_evaluator_with_llm_error` | LLM APIエラー時の処理 | Medium |
| 7 | `test_evaluator_unknown_stage` | 未知のevaluator_stageでのエラー | Low |
| 8 | `test_evaluator_missing_required_fields` | 必須フィールド欠落時のエラー | Low |

**モック対象**:
- `create_llm_with_fallback()` - LLMインスタンス生成
- LLM応答データ（`EVALUATOR_SUCCESS_AFTER_TASK_BREAKDOWN` 等）

**検証項目**:
- ✅ evaluation_resultが正しく生成される
- ✅ retry_countが評価失敗時にインクリメントされる
- ✅ evaluator_stageに応じた適切な処理
- ✅ infeasible_tasksが正しく記録される

---

### Phase 2-3: interface_definition_node テスト（7テスト）

**ファイル**: `tests/unit/test_interface_definition_node.py`

**テストケース**:

| # | テスト名 | 内容 | 優先度 |
|---|---------|------|--------|
| 1 | `test_interface_definition_success` | 正常系：インターフェース定義成功 | High |
| 2 | `test_interface_definition_with_json_strings` | Gemini特有：JSON文字列応答の処理 | High |
| 3 | `test_interface_definition_with_retry` | retry_count > 0での動作 | Medium |
| 4 | `test_interface_definition_with_llm_error` | LLM APIエラー時の処理 | Medium |
| 5 | `test_interface_definition_empty_response` | 空応答の処理 | Medium |
| 6 | `test_interface_definition_invalid_schema` | 不正なスキーマ応答の処理 | Low |
| 7 | `test_interface_definition_missing_task_breakdown` | task_breakdown欠落時のエラー | Low |

**モック対象**:
- `create_llm_with_fallback()` - LLMインスタンス生成
- LLM応答データ（`INTERFACE_DEFINITION_SUCCESS` 等）

**検証項目**:
- ✅ interface_definitionsが正しく生成される
- ✅ JSON文字列がdictに変換される（Gemini対応）
- ✅ retry_countが適切に処理される
- ✅ エラー時にerror_messageが設定される

---

### Phase 2-4: master_creation_node テスト（6テスト）

**ファイル**: `tests/unit/test_master_creation_node.py`

**テストケース**:

| # | テスト名 | 内容 | 優先度 |
|---|---------|------|--------|
| 1 | `test_master_creation_success` | 正常系：JobMaster/TaskMaster作成成功 | High |
| 2 | `test_master_creation_with_api_error` | JobQueue APIエラー時の処理 | High |
| 3 | `test_master_creation_missing_interface_definitions` | interface_definitions欠落時のエラー | Medium |
| 4 | `test_master_creation_missing_task_breakdown` | task_breakdown欠落時のエラー | Medium |
| 5 | `test_master_creation_partial_success` | 一部作成成功、一部失敗の処理 | Low |
| 6 | `test_master_creation_duplicate_check` | 重複チェック機能の検証 | Low |

**モック対象**:
- `JobqueueClient` - JobQueue API呼び出し
- API応答データ（`MASTER_CREATION_SUCCESS` フィクスチャ使用）

**検証項目**:
- ✅ job_master_idが設定される
- ✅ task_master_idsが設定される
- ✅ interface_master_idsが設定される
- ✅ APIエラー時にerror_messageが設定される

---

### Phase 2-5: job_registration_node テスト（6テスト）

**ファイル**: `tests/unit/test_job_registration_node.py`

**テストケース**:

| # | テスト名 | 内容 | 優先度 |
|---|---------|------|--------|
| 1 | `test_job_registration_success` | 正常系：Job登録成功 | High |
| 2 | `test_job_registration_with_api_error` | JobQueue APIエラー時の処理 | High |
| 3 | `test_job_registration_missing_job_master_id` | job_master_id欠落時のエラー | Medium |
| 4 | `test_job_registration_missing_task_breakdown` | task_breakdown欠落時のエラー | Medium |
| 5 | `test_job_registration_with_dependencies` | タスク依存関係の処理 | Low |
| 6 | `test_job_registration_status_check` | 登録後のステータス確認 | Low |

**モック対象**:
- `JobqueueClient` - JobQueue API呼び出し
- API応答データ（`JOB_REGISTRATION_SUCCESS` フィクスチャ使用）

**検証項目**:
- ✅ job_idが設定される
- ✅ statusが"success"になる
- ✅ APIエラー時にerror_messageが設定される
- ✅ task_idsが正しく設定される

---

### Phase 2-6: ルーター追加テスト（15テスト）

**ファイル**: `tests/unit/test_router_edge_cases.py`

**テストケース**:

#### Evaluator Router Edge Cases (8テスト)

| # | テスト名 | 内容 |
|---|---------|------|
| 1 | `test_evaluator_router_with_quality_score_threshold` | quality_scoreがしきい値以下での処理 |
| 2 | `test_evaluator_router_with_feasibility_score_threshold` | feasibility_scoreがしきい値以下での処理 |
| 3 | `test_evaluator_router_transition_stage` | evaluator_stage遷移の正確性 |
| 4 | `test_evaluator_router_with_multiple_infeasible_tasks` | 複数の実現不可能タスク |
| 5 | `test_evaluator_router_with_warning_only` | 警告のみ（エラーなし）での処理 |
| 6 | `test_evaluator_router_retry_count_persistence` | retry_count永続性の確認 |
| 7 | `test_evaluator_router_concurrent_errors` | 同時エラー発生時の処理 |
| 8 | `test_evaluator_router_state_consistency` | 状態の整合性チェック |

#### Validation Router Edge Cases (7テスト)

| # | テスト名 | 内容 |
|---|---------|------|
| 9 | `test_validation_router_with_fix_proposals` | fix_proposals存在時の処理 |
| 10 | `test_validation_router_with_manual_action` | manual_action_required時の処理 |
| 11 | `test_validation_router_retry_with_different_errors` | 異なるエラーでのリトライ |
| 12 | `test_validation_router_state_transition` | 状態遷移の正確性 |
| 13 | `test_validation_router_error_priority` | エラー優先度の処理 |
| 14 | `test_validation_router_timeout_handling` | タイムアウト時の処理 |
| 15 | `test_validation_router_cascading_failures` | 連鎖失敗の処理 |

---

### Phase 2-7: ヘルパー関数テスト（15テスト）

**ファイル**: `tests/unit/test_helpers.py`

**テストケース**:

#### Mock Helpers Tests (8テスト)

| # | テスト名 | 内容 |
|---|---------|------|
| 1 | `test_create_mock_llm` | create_mock_llm動作確認 |
| 2 | `test_create_mock_llm_with_structured_output` | 構造化出力モック動作確認 |
| 3 | `test_create_mock_workflow_state` | ワークフロー状態生成確認 |
| 4 | `test_create_mock_task_breakdown` | タスク分解生成確認 |
| 5 | `test_create_mock_interface_schemas` | インターフェーススキーマ生成確認 |
| 6 | `test_create_mock_validation_result` | 検証結果生成確認 |
| 7 | `test_create_mock_evaluation_result` | 評価結果生成確認 |
| 8 | `test_mock_helpers_with_custom_data` | カスタムデータでの動作確認 |

#### Fixture Tests (7テスト)

| # | テスト名 | 内容 |
|---|---------|------|
| 9 | `test_validation_success_response_structure` | VALIDATION_SUCCESS_RESPONSE構造確認 |
| 10 | `test_validation_failure_response_structure` | VALIDATION_FAILURE_RESPONSE構造確認 |
| 11 | `test_interface_definition_success_structure` | INTERFACE_DEFINITION_SUCCESS構造確認 |
| 12 | `test_evaluator_success_structure` | EVALUATOR_SUCCESS構造確認 |
| 13 | `test_requirement_analysis_success_structure` | REQUIREMENT_ANALYSIS_SUCCESS構造確認 |
| 14 | `test_master_creation_success_structure` | MASTER_CREATION_SUCCESS構造確認 |
| 15 | `test_job_registration_success_structure` | JOB_REGISTRATION_SUCCESS構造確認 |

---

## 📅 実装スケジュール

### Day 1（約8時間）

**午前（4時間）**:
- Phase 2-1: requirement_analysis_node テスト（6テスト）
- Phase 2-2: evaluator_node テスト（8テスト）

**午後（4時間）**:
- Phase 2-3: interface_definition_node テスト（7テスト）
- Phase 2-4: master_creation_node テスト（6テスト）

**成果物**: 27テスト実装、すべてPASS

---

### Day 2（約8時間）

**午前（4時間）**:
- Phase 2-5: job_registration_node テスト（6テスト）
- Phase 2-6: ルーター追加テスト（15テスト）

**午後（4時間）**:
- Phase 2-7: ヘルパー関数テスト（15テスト）
- 全テスト実行・検証

**成果物**: 36テスト実装、合計63テストPASS

---

### Day 3（予備日・約8時間）

**必要に応じて実施**:
- バグ修正
- カバレッジ改善
- パフォーマンス最適化
- ドキュメント作成

---

## 🎯 成功基準

### 必須基準

- ✅ **63テストすべてPASS**
- ✅ **API-key-free率 100%** (63/63テスト)
- ✅ **テスト実行時間 < 1秒**
- ✅ **カバレッジ90%以上** (全ノード・ルーター)

### 推奨基準

- ✅ Ruff linting: エラーゼロ
- ✅ MyPy type checking: エラーゼロ
- ✅ すべてのエッジケースをカバー
- ✅ ドキュメント完備

---

## 🛡️ リスク管理

### リスク1: テスト実装時間の超過

**対策**:
- 優先度High/Mediumのテストを優先実装
- 優先度Lowは必要に応じてスキップ
- 1日8時間を超えない

### リスク2: 複雑なモックの作成

**対策**:
- Phase 1で作成したヘルパー関数を最大活用
- 既存フィクスチャを再利用
- 新規フィクスチャは最小限に

### リスク3: 予期しないバグの発見

**対策**:
- バグ発見時は即座に修正
- 修正後のテスト再実行で検証
- Day 3を予備日として確保

---

## 📊 進捗管理

### 各Phase完了時のチェックリスト

- [ ] テストファイル作成完了
- [ ] すべてのテストケース実装完了
- [ ] テスト実行でPASS確認
- [ ] Ruff linting通過
- [ ] MyPy type checking通過
- [ ] コミット完了
- [ ] 進捗レポート更新

### 全Phase完了時のチェックリスト

- [ ] 63テストすべてPASS
- [ ] カバレッジ90%以上達成
- [ ] API-key-free率100%確認
- [ ] 実行時間1秒以内確認
- [ ] Phase 2最終レポート作成
- [ ] Phase 3準備完了

---

## 💡 実装のポイント

### 1. 既存インフラの活用

Phase 1で作成したテストインフラを最大限活用:
- `tests/utils/mock_helpers.py` - すべてのヘルパー関数
- `tests/integration/fixtures/llm_responses.py` - すべてのフィクスチャ
- `tests/integration/conftest.py` - APIキーフィクスチャ

### 2. テストの独立性

各テストは完全に独立:
- 他のテストに依存しない
- 状態を共有しない
- 並列実行可能

### 3. モック戦略

一貫したモック戦略:
- 外部依存（LLM, JobQueue API）のみモック
- 内部ロジック（ノード、ルーター）は実コード実行
- retry_count処理は実コードで検証

### 4. フィクスチャ再利用

既存フィクスチャを最大限再利用:
- `REQUIREMENT_ANALYSIS_SUCCESS`
- `EVALUATOR_SUCCESS_AFTER_TASK_BREAKDOWN`
- `INTERFACE_DEFINITION_SUCCESS`
- `MASTER_CREATION_SUCCESS`
- `JOB_REGISTRATION_SUCCESS`

新規フィクスチャは必要最小限のみ作成。

---

## 📚 参考資料

### 実装済みファイル（Phase 1）

- `tests/unit/test_validation_node.py` (170行) - 参考実装
- `tests/unit/test_routers.py` (354行) - ルーターテストの参考
- `tests/unit/test_recursion_limit.py` (313行) - 境界値テストの参考
- `tests/utils/mock_helpers.py` (206行) - ヘルパー関数
- `tests/integration/fixtures/llm_responses.py` (259行) - フィクスチャ

### 実装対象ファイル

- `aiagent/langgraph/jobTaskGeneratorAgents/nodes/requirement_analysis.py`
- `aiagent/langgraph/jobTaskGeneratorAgents/nodes/evaluator.py`
- `aiagent/langgraph/jobTaskGeneratorAgents/nodes/interface_definition.py`
- `aiagent/langgraph/jobTaskGeneratorAgents/nodes/master_creation.py`
- `aiagent/langgraph/jobTaskGeneratorAgents/nodes/job_registration.py`

### 関連ドキュメント

- `dev-reports/feature/issue/111/test-implementation-work-plan.md` - 全体計画
- `dev-reports/feature/issue/111/phase-1-progress.md` - Phase 1進捗
- `dev-reports/feature/issue/111/進捗サマリー.md` - 進捗サマリー

---

**Phase 2作業計画作成日**: 2025-10-24
**予定開始日**: 2025-10-24（即日）
**予定完了日**: 2025-10-26（3日後）
