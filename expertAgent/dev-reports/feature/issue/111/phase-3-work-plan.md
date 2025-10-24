# Phase 3 作業計画: E2E Workflow Tests

**作成日**: 2025-10-24
**予定工数**: 2-3時間
**目標**: 10テストの実装とPASS

---

## 📋 目的

Phase 2で個別ノード・ルーターの動作を検証したので、Phase 3では**ワークフロー全体**の統合テストを実施します。これにより、エンドツーエンドでの動作保証を確立します。

---

## 🎯 Phase 3の目標

### 主要目標

1. **エンドツーエンドワークフロー実行** (6テスト)
   - requirement_analysis → evaluator → interface_definition → evaluator → master_creation → job_registration の完全フロー
   - 正常系シナリオの検証
   - リトライループの検証

2. **失敗シナリオの検証** (2テスト)
   - Max retries 到達 → END
   - infeasible_tasks 検出 → status="failed"

3. **エッジケースの検証** (2テスト)
   - Empty results の処理
   - 並行実行の安全性

### 副次的目標

- API-key-free率 100%維持
- テスト実行時間 < 5秒
- カバレッジ測定・報告

---

## 📊 実装計画詳細

### Phase 3-1: 正常系ワークフローテスト (3テスト)

**ファイル**: `tests/integration/test_e2e_workflow.py`

#### テストケース

| # | テスト名 | 内容 | 優先度 |
|---|---------|------|--------|
| 1 | `test_e2e_workflow_success_first_try` | 1回目で全ステージ成功 | High |
| 2 | `test_e2e_workflow_success_with_retry` | task_breakdown評価失敗 → リトライ → 成功 | High |
| 3 | `test_e2e_workflow_success_after_interface_retry` | interface_definition評価失敗 → リトライ → 成功 | High |

**検証項目**:
- ✅ 最終状態が `status="completed"` になる
- ✅ `job_id` が設定される
- ✅ `job_master_id` が設定される
- ✅ `task_master_ids` が設定される
- ✅ retry_count が適切に処理される
- ✅ すべてのノードが実行される

---

### Phase 3-2: 失敗シナリオテスト (2テスト)

#### テストケース

| # | テスト名 | 内容 | 優先度 |
|---|---------|------|--------|
| 4 | `test_e2e_workflow_max_retries_reached` | Max retries (5回) 到達 → END | High |
| 5 | `test_e2e_workflow_infeasible_tasks_detected` | 実現不可能タスク検出 → status="failed" | High |

**検証項目**:
- ✅ retry_count が MAX_RETRY_COUNT (5) に到達
- ✅ `error_message` が設定される
- ✅ `status="failed"` になる
- ✅ `infeasible_tasks` が記録される
- ✅ `requirement_relaxation_suggestions` が生成される

---

### Phase 3-3: エッジケーステスト (3テスト)

#### テストケース

| # | テスト名 | 内容 | 優先度 |
|---|---------|------|--------|
| 6 | `test_e2e_workflow_empty_task_breakdown` | 空のタスク分解 → END | Medium |
| 7 | `test_e2e_workflow_empty_interface_definitions` | 空のインターフェース定義 → END | Medium |
| 8 | `test_e2e_workflow_llm_error_during_flow` | ワークフロー実行中にLLMエラー | Medium |

**検証項目**:
- ✅ Empty results で適切に終了
- ✅ LLMエラーでワークフロー停止
- ✅ エラーメッセージが明確

---

### Phase 3-4: パフォーマンステスト (2テスト)

#### テストケース

| # | テスト名 | 内容 | 優先度 |
|---|---------|------|--------|
| 9 | `test_e2e_workflow_execution_time` | ワークフロー実行時間の測定 | Low |
| 10 | `test_e2e_workflow_state_consistency` | 状態の整合性確認 | Low |

**検証項目**:
- ✅ 実行時間が妥当（モック化された場合、< 1秒）
- ✅ 状態遷移の整合性
- ✅ retry_count の一貫性

---

## 🛠️ 実装方針

### 1. StateGraph.invoke() の使用

Phase 3 では、StateGraph の `invoke()` メソッドを使用してワークフロー全体を実行します：

```python
from aiagent.langgraph.jobTaskGeneratorAgents.agent import app

# app は StateGraph のインスタンス
result = await app.ainvoke(initial_state)
```

### 2. LLM API のモック化

Phase 2 と同様、LLM API はモック化します：

```python
@patch("...nodes.requirement_analysis.create_llm_with_fallback")
@patch("...nodes.evaluator.create_llm_with_fallback")
@patch("...nodes.interface_definition.create_llm_with_fallback")
async def test_e2e_workflow_success_first_try(
    self,
    mock_llm_interface,
    mock_llm_evaluator,
    mock_llm_requirement,
):
    # 各ノードのLLMをモック
    mock_llm_requirement.return_value = create_mock_llm_with_structured_output(
        REQUIREMENT_ANALYSIS_SUCCESS
    )
    mock_llm_evaluator.return_value = create_mock_llm_with_structured_output(
        EVALUATOR_SUCCESS_AFTER_TASK_BREAKDOWN
    )
    # ... 以下同様
```

### 3. JobqueueClient/SchemaMatcher のモック化

master_creation_node および job_registration_node で使用される外部APIもモック化：

```python
@patch("...nodes.master_creation.SchemaMatcher")
@patch("...nodes.master_creation.JobqueueClient")
@patch("...nodes.job_registration.JobqueueClient")
async def test_e2e_workflow_success_first_try(
    self,
    mock_jobqueue_job_reg,
    mock_jobqueue_master,
    mock_schema_matcher,
    # ... LLM mocks
):
    # JobqueueClient と SchemaMatcher のモック設定
```

### 4. 複数ステージのLLMモック

evaluator_node は2回呼び出される（after_task_breakdown, after_interface_definition）ため、以下のように2つのレスポンスを用意：

```python
# 1回目: task_breakdown 評価
mock_llm_evaluator.return_value = create_mock_llm_with_structured_output(
    EVALUATOR_SUCCESS_AFTER_TASK_BREAKDOWN
)

# 2回目: interface_definition 評価
# ainvoke が2回呼ばれるため、side_effect を使用
mock_structured = AsyncMock()
mock_structured.ainvoke = AsyncMock(
    side_effect=[
        EVALUATOR_SUCCESS_AFTER_TASK_BREAKDOWN,
        EVALUATOR_SUCCESS_AFTER_INTERFACE_DEFINITION,
    ]
)
mock_llm_evaluator.return_value.with_structured_output.return_value = mock_structured
```

### 5. リトライシナリオのモック

リトライシナリオでは、最初は失敗、2回目は成功のように設定：

```python
# evaluator の1回目は失敗、2回目は成功
mock_structured.ainvoke = AsyncMock(
    side_effect=[
        EVALUATOR_FAILURE_AFTER_TASK_BREAKDOWN,  # 1回目: 失敗
        EVALUATOR_SUCCESS_AFTER_TASK_BREAKDOWN,  # 2回目: 成功（リトライ後）
        EVALUATOR_SUCCESS_AFTER_INTERFACE_DEFINITION,  # 3回目: 成功
    ]
)
```

### 6. 初期状態の設定

ワークフロー開始時の初期状態：

```python
initial_state = {
    "user_requirement": "Search Gmail and extract content",
    "retry_count": 0,
}

result = await app.ainvoke(initial_state)
```

---

## 📅 実装スケジュール

### 1時間目: 正常系テスト (3テスト)

- Phase 3-1: 正常系ワークフローテスト
- テスト1-3の実装・実行

### 2時間目: 失敗/エッジケース (5テスト)

- Phase 3-2: 失敗シナリオテスト (2テスト)
- Phase 3-3: エッジケーステスト (3テスト)
- テスト4-8の実装・実行

### 3時間目: パフォーマンス/最終検証 (2テスト + 検証)

- Phase 3-4: パフォーマンステスト (2テスト)
- テスト9-10の実装・実行
- カバレッジ測定
- 最終検証・ドキュメント作成

---

## 🎯 成功基準

### 必須基準

- ✅ **10テストすべてPASS**
- ✅ **API-key-free率 100%** (10/10テスト)
- ✅ **テスト実行時間 < 5秒**
- ✅ **カバレッジ測定完了**

### 推奨基準

- ✅ Ruff linting: エラーゼロ
- ✅ MyPy type checking: エラーゼロ
- ✅ すべてのワークフローパスをカバー
- ✅ ドキュメント完備

---

## 🛡️ リスク管理

### リスク1: 複雑なモック設定

**対策**:
- Phase 2 で確立したモックパターンを再利用
- side_effect を使用した複数回呼び出しのモック
- ヘルパー関数で共通モック設定を抽出

### リスク2: StateGraph の動作理解

**対策**:
- agent.py の StateGraph 定義を事前確認
- ノード間の遷移ロジックを理解
- evaluator_router の分岐パターンを把握

### リスク3: テスト実行時間の長期化

**対策**:
- すべての外部依存をモック化
- 実行時間測定テストで監視
- 必要に応じてモック最適化

---

## 📊 進捗管理

### Phase 3完了時のチェックリスト

- [ ] test_e2e_workflow.py 作成完了
- [ ] 10テストケース実装完了
- [ ] テスト実行でPASS確認（10/10）
- [ ] Ruff linting通過
- [ ] MyPy type checking通過
- [ ] カバレッジ測定完了
- [ ] カバレッジレポート作成
- [ ] コミット完了
- [ ] Phase 3進捗レポート作成

---

## 💡 実装のポイント

### 1. StateGraph の理解

agent.py の StateGraph 定義を確認：

```python
workflow = StateGraph(JobTaskGeneratorState)

# ノード追加
workflow.add_node("requirement_analysis", requirement_analysis_node)
workflow.add_node("evaluator", evaluator_node)
workflow.add_node("interface_definition", interface_definition_node)
workflow.add_node("master_creation", master_creation_node)
workflow.add_node("job_registration", job_registration_node)

# エントリーポイント
workflow.set_entry_point("requirement_analysis")

# ルーティング
workflow.add_conditional_edges(
    "evaluator",
    evaluator_router,
    {
        "requirement_analysis": "requirement_analysis",
        "interface_definition": "interface_definition",
        "master_creation": "master_creation",
        "END": END,
    },
)

# ... その他のエッジ定義
```

この構造を理解することで、ワークフローの流れを正確にテストできます。

### 2. フィクスチャの再利用

Phase 1 で作成したフィクスチャを最大限再利用：

- `REQUIREMENT_ANALYSIS_SUCCESS`
- `EVALUATOR_SUCCESS_AFTER_TASK_BREAKDOWN`
- `EVALUATOR_SUCCESS_AFTER_INTERFACE_DEFINITION`
- `INTERFACE_DEFINITION_SUCCESS`

新規フィクスチャは必要最小限のみ作成。

### 3. retry_count の追跡

ワークフロー実行中の retry_count の変化を追跡：

```python
# 初期状態
assert initial_state["retry_count"] == 0

# 評価失敗後
# (evaluator_node が retry_count++ を実行)

# 最終状態
assert result["retry_count"] == 0  # 成功時はリセット
```

### 4. ワークフロー実行パスの検証

各テストで、どのノードが実行されたかを検証：

```python
# モック呼び出し回数で検証
assert mock_llm_requirement.call_count == 1  # requirement_analysis_node
assert mock_llm_evaluator.call_count == 2   # evaluator_node (2回)
assert mock_llm_interface.call_count == 1   # interface_definition_node
assert mock_jobqueue_master.call_count == 1 # master_creation_node
assert mock_jobqueue_job_reg.call_count == 1 # job_registration_node
```

---

## 📚 参考資料

### 実装対象ファイル

- `aiagent/langgraph/jobTaskGeneratorAgents/agent.py` - StateGraph定義
- `tests/integration/test_e2e_workflow.py` - 新規作成

### 参考実装（Phase 2）

- `tests/unit/test_requirement_analysis_node.py` - LLMモックパターン
- `tests/unit/test_evaluator_node.py` - 複数ステージテスト
- `tests/unit/test_master_creation_node.py` - JobqueueClient モック
- `tests/unit/test_job_registration_node.py` - Job作成検証

### フィクスチャ

- `tests/integration/fixtures/llm_responses.py` - すべてのLLM応答フィクスチャ
- `tests/utils/mock_helpers.py` - モックヘルパー関数

---

**Phase 3作業計画作成日**: 2025-10-24
**予定開始日**: 2025-10-24（即日）
**予定完了日**: 2025-10-24（同日、2-3時間後）
