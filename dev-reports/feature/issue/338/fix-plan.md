# Issue #338 修正対応方針

**作成日**: 2026-01-04
**更新日**: 2026-01-04
**関連Issue**: #338, #341
**ステータス**: 対応待ち

---

## 1. 問題サマリ

Issue #338で計画された4つのPhaseのうち、Phase 1のみが完全に実装され、**Phase 2-4は関数が定義されたが実際のワークフローに統合されていない（デッドコード状態）**。

| Phase | 関数 | 定義場所 | 呼び出し状況 | 修正必要 |
|-------|------|---------|-------------|:--------:|
| 1 | 出力ノード命名規約 | プロンプト | 統合済み | - |
| 2 | `_transform_to_interface()` | `worker.py:606` | 未呼び出し | ✅ |
| 3 | `get_api_response_schemas()` | `workflow_helper.py:59` | 未呼び出し | ✅ |
| 4 | `check_interface_compatibility()` | `evaluator.py:30` | 未呼び出し | ✅ |

---

## 2. Phase別修正方針

### 2.1 Phase 2: output_interface変換の統合 [P0]

**対象ファイル**: `jobqueue/app/core/worker.py`

**現状** (205-227行目):
```python
# Validate output data against interfaces
if output_data:
    interfaces = await self.session.scalars(
        select(TaskMasterInterface)
        .where(TaskMasterInterface.task_master_id == task_master.id)
        .options(selectinload(TaskMasterInterface.interface_master))
    )
    for assoc in interfaces.all():
        if assoc.required and assoc.interface_master.output_schema:
            try:
                InterfaceValidator.validate_output(
                    output_data,
                    assoc.interface_master.output_schema,
                )
            except InterfaceValidationError as e:
                raise Exception(
                    f"Output validation failed: {'; '.join(e.errors)}"
                ) from e

# Store output (extract GraphAI output node result for task chains)
task.output_data = (
    _extract_graphai_output(output_data)
    if output_data
    else output_data
)
```

**問題点**:
- `assoc`はループ変数であり、ループ外では最後の値しか参照できない
- 複数のインターフェースがある場合、どれを変換用に使うか不明確

**修正方針**:
```python
# Validate output data against interfaces AND collect schema for transformation
output_schema_for_transform: dict | None = None

if output_data:
    interfaces = await self.session.scalars(
        select(TaskMasterInterface)
        .where(TaskMasterInterface.task_master_id == task_master.id)
        .options(selectinload(TaskMasterInterface.interface_master))
    )
    for assoc in interfaces.all():
        if assoc.required and assoc.interface_master.output_schema:
            try:
                InterfaceValidator.validate_output(
                    output_data,
                    assoc.interface_master.output_schema,
                )
            except InterfaceValidationError as e:
                raise Exception(
                    f"Output validation failed: {'; '.join(e.errors)}"
                ) from e

            # 変換用に最初のrequired=Trueのスキーマを保持
            if output_schema_for_transform is None:
                output_schema_for_transform = assoc.interface_master.output_schema

# Store output with interface transformation
extracted = _extract_graphai_output(output_data) if output_data else output_data
task.output_data = _transform_to_interface(extracted, output_schema_for_transform)

logger.debug(
    f"[TRANSFORM] Applied output_interface transformation for task {task.id}, "
    f"schema_applied={output_schema_for_transform is not None}"
)
```

**修正ポイント**:
1. ループ内で検証しつつ、最初のrequired=Trueのスキーマを変数に保持
2. ループ後に`_transform_to_interface`を呼び出し
3. デバッグログを追加

**後方互換性**:
- `output_schema_for_transform`がNoneの場合、`_transform_to_interface(raw, None)`は現行通りraw outputを返す

---

### 2.2 Phase 3: API応答スキーマの注入 [P1]

**対象ファイル**: `expertAgent/aiagent/langgraph/workflowGeneratorAgents/nodes/generator.py`

**修正方針**:

1. `get_api_response_schemas`をimport
2. `task_data`から`recommended_apis`を取得
3. プロンプト生成前にAPIスキーマを取得
4. `create_workflow_generation_prompt`にスキーマを渡す

```python
from aiagent.langgraph.jobTaskGeneratorAgents.utils.workflow_helper import (
    get_api_response_schemas,
)

async def generator_node(state: WorkflowGeneratorState) -> WorkflowGeneratorState:
    """Generate GraphAI workflow YAML from TaskMaster metadata using LLM."""
    logger.info("Starting generator node")

    task_data = state.get("task_data")
    if task_data is None:
        message = "Workflow generation failed: task_data missing from state"
        logger.error(message)
        return {
            **state,
            "status": "failed",
            "error_message": message,
        }
    error_feedback = state.get("error_feedback")

    # Load capabilities
    graphai_capabilities, expert_agent_capabilities = _load_capabilities()

    # Issue #338 Phase 3: Get API response schemas for recommended APIs
    recommended_apis = task_data.get("recommended_apis", [])
    api_schemas: dict = {}
    if recommended_apis:
        try:
            api_schemas = await get_api_response_schemas(recommended_apis)
            logger.info(
                "Retrieved API schemas for %d APIs: %s",
                len(api_schemas),
                list(api_schemas.keys()),
            )
        except Exception as e:
            logger.warning(f"Failed to get API schemas: {e}")
            # Continue without schemas (non-blocking)

    # Create prompt (with feedback and API schemas)
    if error_feedback:
        user_prompt = create_workflow_generation_prompt_with_feedback(
            task_data,
            graphai_capabilities,
            expert_agent_capabilities,
            error_feedback,
            api_schemas=api_schemas,  # 新規パラメータ
        )
    else:
        user_prompt = create_workflow_generation_prompt(
            task_data,
            graphai_capabilities,
            expert_agent_capabilities,
            api_schemas=api_schemas,  # 新規パラメータ
        )

    # ... 以下既存処理 ...
```

**追加修正ファイル**:

1. `expertAgent/.../prompts/workflow_generation.py`:
   - `create_workflow_generation_prompt`に`api_schemas`パラメータを追加
   - `create_workflow_generation_prompt_with_feedback`に`api_schemas`パラメータを追加
   - プロンプトテンプレートにAPIスキーマセクションを追加

```python
def create_workflow_generation_prompt(
    task_data: dict,
    graphai_capabilities: dict,
    expert_agent_capabilities: dict,
    api_schemas: dict | None = None,  # 追加
) -> str:
    # ... 既存処理 ...

    # API応答スキーマセクションを追加
    if api_schemas:
        prompt += "\n\n## API Response Schemas\n"
        prompt += "Use the following response field names when referencing API outputs:\n"
        for api_path, schema in api_schemas.items():
            prompt += f"\n### {api_path}\n"
            prompt += f"```json\n{json.dumps(schema, indent=2)}\n```\n"

    return prompt
```

---

### 2.3 Phase 4: インターフェース整合性検証の統合 [P0]

**対象ファイル**: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/evaluator.py`

**データ構造の確認**:

- `task_breakdown`: `list[dict[str, Any]]` - タスクリスト（task_idなど含む）
- `interface_definitions`: `dict[str, dict[str, Any]]` - task_id → interface schema bundle

`check_interface_compatibility`は`tasks[i].get("output_interface", {})`を期待するため、
`task_breakdown`と`interface_definitions`をマージする必要がある。

**修正方針**:

```python
async def evaluator_node(state: JobTaskGeneratorState) -> JobTaskGeneratorState:
    """Evaluate task breakdown quality and feasibility."""

    # ... 既存の評価処理 ...

    task_breakdown = state.get("task_breakdown", [])
    interface_definitions = state.get("interface_definitions", {})

    # ... LLM評価処理 ...

    response = call_result.result

    # Issue #338 Phase 4: インターフェース整合性検証
    # interface_definitionsをtask_breakdownにマージしてcheck_interface_compatibilityを呼び出し
    interface_warnings: list[str] = []

    if len(task_breakdown) >= 2 and interface_definitions:
        # task_breakdownにinterface情報をマージ
        tasks_with_interfaces = []
        for task in task_breakdown:
            task_id = task.get("task_id")
            task_with_interface = dict(task)  # コピー

            if task_id and task_id in interface_definitions:
                interface_bundle = interface_definitions[task_id]
                task_with_interface["input_interface"] = interface_bundle.get("input_schema", {})
                task_with_interface["output_interface"] = interface_bundle.get("output_schema", {})

            tasks_with_interfaces.append(task_with_interface)

        # 整合性検証を実行
        interface_warnings = check_interface_compatibility(tasks_with_interfaces)

        if interface_warnings:
            logger.warning(
                "Interface compatibility issues detected (%d warnings): %s",
                len(interface_warnings),
                interface_warnings,
            )

    # stateに警告を追加して返却
    return {
        **state,
        "evaluation_result": response,
        "interface_warnings": interface_warnings,  # 追加
    }
```

**追加修正ファイル**:

1. `expertAgent/.../state.py`:
   - `JobTaskGeneratorState`に`interface_warnings: list[str]`フィールドを追加
   - `create_initial_state`に初期値を追加

```python
class JobTaskGeneratorState(TypedDict, total=False):
    # ... 既存フィールド ...

    # ===== Issue #338: Interface Compatibility =====
    interface_warnings: list[str]

def create_initial_state(...) -> JobTaskGeneratorState:
    return {
        # ... 既存初期値 ...
        "interface_warnings": [],
    }
```

---

## 3. 修正優先順位

| 優先度 | Phase | 影響 | 工数目安 |
|:------:|:-----:|------|:--------:|
| **P0** | 2 | タスク間データ変換が機能しない | 2h |
| **P0** | 4 | 事前検証なしで問題が実行時まで発覚しない | 3h |
| **P1** | 3 | LLMが正確なフィールド名を参照できない | 3h |

---

## 4. 追加すべきテスト

### 4.1 統合確認テスト（不足していた観点）

| Phase | テストファイル | テスト内容 |
|-------|--------------|-----------|
| 2 | `jobqueue/tests/integration/test_task_chain_transformation.py` | 既存ファイルに統合テスト追加 |
| 3 | `expertAgent/tests/integration/test_generator_schema_injection.py` | 新規作成 |
| 4 | `expertAgent/tests/integration/test_evaluator_compatibility_check.py` | 新規作成 |

### 4.2 テスト例（Phase 2 - 既存ファイルに追加）

```python
# jobqueue/tests/integration/test_task_chain_transformation.py に追加

@pytest.mark.asyncio
async def test_worker_applies_transform_to_interface():
    """worker.pyがタスク実行後に_transform_to_interfaceを適用することを確認"""

    # Setup: output_schemaを持つTaskMasterInterfaceを作成
    # ...

    # Execute: タスクを実行
    # ...

    # Assert: task.output_dataがoutput_schemaに基づいて変換されている
    assert task.output_data is not None
    # output_schema.propertiesで定義されたフィールドのみ含まれていることを確認
```

### 4.3 テスト例（Phase 4 - 新規ファイル）

```python
# expertAgent/tests/integration/test_evaluator_compatibility_check.py

import pytest
from aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator import evaluator_node

@pytest.mark.asyncio
async def test_evaluator_detects_interface_mismatch():
    """evaluator_nodeがインターフェース不整合を検出することを確認"""

    state = {
        "user_requirement": "テスト要件",
        "task_breakdown": [
            {"task_id": "task_0", "name": "検索実行"},
            {"task_id": "task_1", "name": "結果分析"},
        ],
        "interface_definitions": {
            "task_0": {
                "output_schema": {
                    "properties": {"results": {"type": "array"}},
                    "required": ["results"],
                }
            },
            "task_1": {
                "input_schema": {
                    "properties": {"search_results": {"type": "array"}},  # 不一致
                    "required": ["search_results"],
                }
            },
        },
        "evaluator_stage": "after_interface_definition",
    }

    result = await evaluator_node(state)

    # 警告が検出されていることを確認
    assert "interface_warnings" in result
    assert len(result["interface_warnings"]) > 0
    assert any("results" in w or "search_results" in w for w in result["interface_warnings"])


@pytest.mark.asyncio
async def test_evaluator_passes_compatible_interfaces():
    """evaluator_nodeが整合性のあるインターフェースでは警告しないことを確認"""

    state = {
        "user_requirement": "テスト要件",
        "task_breakdown": [
            {"task_id": "task_0", "name": "検索実行"},
            {"task_id": "task_1", "name": "結果分析"},
        ],
        "interface_definitions": {
            "task_0": {
                "output_schema": {
                    "properties": {"results": {"type": "array"}},
                    "required": ["results"],
                }
            },
            "task_1": {
                "input_schema": {
                    "properties": {"results": {"type": "array"}},  # 一致
                    "required": ["results"],
                }
            },
        },
        "evaluator_stage": "after_interface_definition",
    }

    result = await evaluator_node(state)

    # 警告がないことを確認
    assert result.get("interface_warnings", []) == []
```

---

## 5. 修正ファイル一覧

| ファイル | 修正内容 | Phase |
|---------|---------|:-----:|
| `jobqueue/app/core/worker.py` | `_transform_to_interface`呼び出し追加、ループ内でスキーマ保持 | 2 |
| `expertAgent/.../nodes/generator.py` | `get_api_response_schemas`呼び出し追加 | 3 |
| `expertAgent/.../prompts/workflow_generation.py` | `api_schemas`パラメータ追加、テンプレート更新 | 3 |
| `expertAgent/.../nodes/evaluator.py` | `check_interface_compatibility`呼び出し追加、マージ処理 | 4 |
| `expertAgent/.../state.py` | `interface_warnings`フィールド追加 | 4 |
| `jobqueue/tests/integration/test_task_chain_transformation.py` | 統合確認テスト追加 | 2 |
| `expertAgent/tests/integration/test_generator_schema_injection.py` | 新規作成 | 3 |
| `expertAgent/tests/integration/test_evaluator_compatibility_check.py` | 新規作成 | 4 |

---

## 6. 検証チェックリスト

修正完了後、以下を必ず確認:

### 6.1 コード統合確認

```bash
# Phase 2: worker.pyで_transform_to_interfaceが呼び出されているか
grep -n "_transform_to_interface" jobqueue/app/core/worker.py | grep -v "^.*:def "
# 期待: 呼び出し行が1つ以上表示される

# Phase 3: generator.pyでget_api_response_schemasが呼び出されているか
grep -n "get_api_response_schemas" expertAgent/aiagent/langgraph/workflowGeneratorAgents/nodes/generator.py
# 期待: import行と呼び出し行が表示される

# Phase 4: evaluator.pyでcheck_interface_compatibilityが呼び出されているか
grep -n "check_interface_compatibility" expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/evaluator.py | grep -v "^.*:def "
# 期待: 呼び出し行が1つ以上表示される
```

### 6.2 テスト実行

```bash
# 単体テスト
pytest jobqueue/tests/unit/ -v
pytest expertAgent/tests/unit/ -v

# 結合テスト
pytest jobqueue/tests/integration/test_task_chain_transformation.py -v
pytest expertAgent/tests/integration/test_generator_schema_injection.py -v
pytest expertAgent/tests/integration/test_evaluator_compatibility_check.py -v

# 全テスト
./scripts/pre-push-check-all.sh
```

### 6.3 動作確認

- [ ] タスクチェーン実行時、`output_interface`に基づいてデータが変換される
- [ ] ワークフロー生成時、APIスキーマがプロンプトに含まれる
- [ ] インターフェース不整合時、`interface_warnings`に警告が格納される
- [ ] 既存テストがすべてパスする（後方互換性）

---

## 7. エラーハンドリング

### 7.1 Phase 2: 変換失敗時

```python
try:
    task.output_data = _transform_to_interface(extracted, output_schema_for_transform)
except Exception as e:
    logger.error(f"Interface transformation failed for task {task.id}: {e}")
    # フォールバック: 変換せずそのまま使用（既存動作を維持）
    task.output_data = extracted
```

### 7.2 Phase 3: スキーマ取得失敗時

```python
try:
    api_schemas = await get_api_response_schemas(recommended_apis)
except Exception as e:
    logger.warning(f"Failed to get API schemas: {e}")
    api_schemas = {}  # 空辞書で継続（non-blocking）
```

### 7.3 Phase 4: 整合性検証失敗時

```python
try:
    interface_warnings = check_interface_compatibility(tasks_with_interfaces)
except Exception as e:
    logger.error(f"Interface compatibility check failed: {e}")
    interface_warnings = [f"Compatibility check error: {e}"]
```

---

## 8. 関連ドキュメント

- [バグ報告](./bug/bug-report.md)
- [機能強化設計](./bug/enhancement-design.md)
- [実装サマリ](./implementation-summary.md)
- [Issue #338](https://github.com/kewton/MySwiftAgent/issues/338)
- [Issue #341](https://github.com/kewton/MySwiftAgent/issues/341)

---

## 9. 教訓と再発防止

### 9.1 問題の根本原因

> 受入テストが「存在確認」のみで「統合確認」が不足していた

### 9.2 今後のテスト設計基準

| 確認レベル | 内容 | 必須 |
|-----------|------|:----:|
| 存在確認 | 関数/クラスが定義されているか | ✅ |
| 単体確認 | 関数単体で正しく動作するか | ✅ |
| **統合確認** | 関数が実際に呼び出されているか | ✅ |
| E2E確認 | エンドツーエンドで機能するか | ✅ |

### 9.3 CLAUDE.md への反映

この問題を受けて、CLAUDE.mdの「サブエージェント利用時の必須検証ルール」に以下を追加済み:

```markdown
| 検証項目 | 確認方法 |
|---------|---------|
| 定数/関数が実際に使用されているか | Grep で参照箇所を確認 |
| グラフ/ワークフローに組み込まれたか | 該当ファイルを Read して確認 |
```

---

## 変更履歴

| 日付 | 変更内容 |
|------|---------|
| 2026-01-04 | 初版作成 |
| 2026-01-04 | レビュー指摘反映: Phase 2のスキーマ取得方法修正、Phase 4のデータマージ処理追加、エラーハンドリング追加 |
