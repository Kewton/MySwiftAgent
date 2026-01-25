# Issue #342: V2 タスク分割 API情報欠落問題 修正案

## 1. 問題の概要

V2 Job Generator でタスク分割時に利用可能なAPI情報がLLMに渡されておらず、以下の問題が発生している：

1. `recommended_apis` が空になる
2. ワークフロー生成がテンプレートにフォールバック
3. TaskMaster の URL が汎用エンドポイントを指す
4. 生成されたワークフローが実行不可能

## 2. 根本原因

### 2.1 TaskDecomposer に API 情報が渡されていない

**問題箇所**: `jobGeneratorV2/workflows/task_breakdown/workflow.py`

```python
# 現状 (Line 99-102)
decomposer = TaskDecomposerSubWorkflow()
tasks = await decomposer.decompose(input_data, context)
# ↑ capabilities が渡されていない

# その後 (Line 125-127) で capabilities をロードするが、decomposer には渡されない
capabilities = input_data.available_capabilities
if not capabilities:
    capabilities = load_capabilities_from_yaml()
```

### 2.2 V2 システムプロンプトに API 情報がない

**問題箇所**: `jobGeneratorV2/llm_utils.py`

```python
TASK_BREAKDOWN_SYSTEM_PROMPT = """You are an expert task decomposition assistant.
...
"""
# ↑ API情報が一切含まれていない
```

### 2.3 TaskMaster URL が汎用エンドポイント

**問題箇所**: `jobGeneratorV2/workflows/registration/master_manager.py`

```python
# Line 461
task_url = f"{self._graphai_server_url}/api/v1/myagent"
# ↑ 全タスクが同じ URL を使用
```

## 3. 修正案

### Phase 1: タスク分割の API 情報注入 (P0 - Critical)

#### 3.1.1 `task_breakdown/workflow.py` の修正

```python
# 修正前
async def execute(self, input_data: TaskBreakdownInput, context: "ExecutionContext") -> TaskBreakdownOutput:
    # Step 1: Decompose requirements into tasks
    decomposer = TaskDecomposerSubWorkflow()
    tasks = await decomposer.decompose(input_data, context)

# 修正後
async def execute(self, input_data: TaskBreakdownInput, context: "ExecutionContext") -> TaskBreakdownOutput:
    # Load capabilities FIRST (before decomposition)
    capabilities = input_data.available_capabilities
    if not capabilities:
        capabilities = load_capabilities_from_yaml()

    # Step 1: Decompose requirements into tasks WITH capabilities
    decomposer = TaskDecomposerSubWorkflow(capabilities=capabilities)
    tasks = await decomposer.decompose(input_data, context)
```

#### 3.1.2 `task_breakdown/decomposer.py` の修正

```python
# 修正前
class TaskDecomposerSubWorkflow:
    async def decompose(self, input_data: TaskBreakdownInput, context: "ExecutionContext") -> list[TaskDefinition]:
        system_prompt = _build_task_breakdown_system_prompt()
        user_prompt = create_task_breakdown_prompt(input_data.user_requirement)

# 修正後
class TaskDecomposerSubWorkflow:
    def __init__(self, capabilities: list[Capability] | None = None) -> None:
        self._capabilities = capabilities or []

    async def decompose(self, input_data: TaskBreakdownInput, context: "ExecutionContext") -> list[TaskDefinition]:
        system_prompt = _build_task_breakdown_system_prompt(self._capabilities)
        user_prompt = create_task_breakdown_prompt(
            input_data.user_requirement,
            available_capabilities=self._format_capabilities(),
        )

    def _format_capabilities(self) -> list[dict[str, Any]]:
        """Format capabilities for prompt."""
        return [
            {
                "name": cap.name,
                "endpoint": cap.endpoint,
                "description": cap.description,
                "use_cases": cap.use_cases,
            }
            for cap in self._capabilities
        ]
```

#### 3.1.3 `llm_utils.py` のシステムプロンプト拡張

```python
def _build_task_breakdown_system_prompt(capabilities: list[Capability] | None = None) -> str:
    """Build the system prompt for task breakdown with API capabilities."""

    # Format capabilities section
    capabilities_section = ""
    if capabilities:
        api_list = []
        for cap in capabilities:
            use_cases = "、".join(cap.use_cases) if cap.use_cases else ""
            api_list.append(f"- **{cap.name}** (`{cap.endpoint}`): {cap.description} - {use_cases}")
        capabilities_section = f"""
## 利用可能なAPI

{chr(10).join(api_list)}
"""

    return f"""You are an expert task decomposition assistant.
Your task is to decompose user requirements into executable workflow tasks.

## Principles
1. Hierarchical decomposition - Break complex tasks into smaller units
2. Clear dependencies - Define which tasks depend on others
3. Specificity and executability - Each task should be specific and actionable
4. Modularity and reusability - Design tasks that can be reused
5. **API Selection** - Each task MUST specify recommended_apis from available APIs

{capabilities_section}

## recommended_apis の記述ルール

**重要**: 各タスクには必ず `recommended_apis` を指定してください。

1. タスク実行に必要なAPIを列挙
2. 利用可能なAPIから選択（上記リスト参照）
3. 各APIには endpoint と reason を含める

### 例
```json
{{
  "task_id": "task_001",
  "name": "Google検索",
  "description": "キーワードでWeb検索を実行",
  "recommended_apis": [
    {{
      "api_name": "Google検索",
      "endpoint": "/v1/utility/google_search",
      "method": "POST",
      "reason": "Web検索機能を提供"
    }}
  ]
}}
```

## Output Format
Return a structured response with:
- tasks: List of TaskBreakdownItem with task_id, name, description, dependencies, recommended_apis
- overall_summary: Summary of the entire workflow
- job_body_parameters: Parameters extracted from the requirements
"""
```

### Phase 2: TaskMaster URL の API 固有化 (P1 - High)

#### 3.2.1 `registration/master_manager.py` の修正

```python
# 修正前
async def _create_task_master(self, task: TaskDefinition, ...) -> str:
    task_url = f"{self._graphai_server_url}/api/v1/myagent"

# 修正後
async def _create_task_master(self, task: TaskDefinition, ...) -> str:
    # Determine task URL based on recommended_api
    task_url = self._resolve_task_url(task)
    body_template = self._build_api_specific_body_template(task, order)

def _resolve_task_url(self, task: TaskDefinition) -> str:
    """Resolve API URL based on recommended_api."""
    if task.recommended_api:
        # Map API endpoint to full URL
        endpoint = task.recommended_api
        if endpoint.startswith("/v1/utility/"):
            return f"{self._expertagent_url}{endpoint}"
        elif endpoint.startswith("/v1/aiagent/"):
            return f"{self._expertagent_url}{endpoint}"

    # Fallback to graphai server
    return f"{self._graphai_server_url}/api/v1/myagent"

def _build_api_specific_body_template(self, task: TaskDefinition, order: int) -> dict[str, Any]:
    """Build API-specific body template."""
    endpoint = task.recommended_api or ""

    if "/google_search" in endpoint:
        return {
            "queries": ["{{job.body.query}}"] if order == 0 else [f"{{{{tasks[{order-1}].output_data.query}}}}"],
            "num": 3,
        }
    elif "/gmail/send" in endpoint:
        return {
            "to": "{{job.body.to}}" if order == 0 else f"{{{{tasks[{order-1}].output_data.to}}}}",
            "subject": "{{job.body.subject}}",
            "body": f"{{{{tasks[{order-1}].output_data.summary}}}}" if order > 0 else "{{job.body.body}}",
        }
    elif "/jsonoutput" in endpoint or "/myllm" in endpoint:
        return {
            "prompt": f"{{{{tasks[{order-1}].output_data}}}}" if order > 0 else "{{job.body.prompt}}",
            "schema": "{{job.body.schema}}",
        }

    # Default template
    return {
        "user_input": "{{job.body}}" if order == 0 else f"{{{{tasks[{order-1}].output_data}}}}",
        "job_params": "{{job.body}}",
    }
```

### Phase 3: ワークフロー生成プロンプト改善 (P1 - High)

#### 3.3.1 `workflow_gen/prompt_builder/` の修正

API情報をワークフロー生成プロンプトにも含める：

```python
# prompt_builder/workflow_prompt.py
def build(self, ..., api_mappings: list[dict] | None = None) -> WorkflowPrompt:
    """Build workflow generation prompt with API mappings."""

    api_section = ""
    if api_mappings:
        api_lines = []
        for mapping in api_mappings:
            api_lines.append(
                f"- {mapping['api_name']}: {mapping['endpoint_url']} ({mapping['http_method']})"
            )
        api_section = f"""
## 利用可能なAPI

{chr(10).join(api_lines)}

各タスクは上記のAPIを使用してワークフローを構成してください。
"""

    return WorkflowPrompt(
        system=self._build_system_prompt(api_section),
        user=self._build_user_prompt(...),
    )
```

## 4. テスト計画

### 4.1 単体テスト

```python
# tests/unit/test_job_generator_v2/test_decomposer_with_capabilities.py

def test_decomposer_receives_capabilities():
    """Test that decomposer receives capabilities."""
    capabilities = [
        Capability(name="Gmail検索", endpoint="/v1/utility/gmail/search", ...),
        Capability(name="Google検索", endpoint="/v1/utility/google_search", ...),
    ]
    decomposer = TaskDecomposerSubWorkflow(capabilities=capabilities)
    assert decomposer._capabilities == capabilities

def test_system_prompt_includes_api_list():
    """Test that system prompt includes API list."""
    capabilities = [
        Capability(name="Gmail検索", endpoint="/v1/utility/gmail/search", ...),
    ]
    prompt = _build_task_breakdown_system_prompt(capabilities)
    assert "/v1/utility/gmail/search" in prompt
    assert "Gmail検索" in prompt

def test_task_has_recommended_apis():
    """Test that decomposed tasks have recommended_apis."""
    # Mock LLM response with recommended_apis
    ...
```

### 4.2 結合テスト

```python
# tests/integration/test_v2_task_breakdown_integration.py

async def test_full_task_breakdown_with_api_assignment():
    """Test full task breakdown flow assigns correct APIs."""
    input_data = TaskBreakdownInput(
        user_requirement="Google検索してメール送信",
    )

    workflow = TaskBreakdownWorkflow()
    output = await workflow.execute(input_data, context)

    # Verify recommended_apis are assigned
    for task in output.tasks:
        assert task.recommended_api, f"Task {task.id} missing recommended_api"
```

### 4.3 受入テスト

```bash
# tests/acceptance/test_issue_342_api_assignment.sh

#!/bin/bash
# Test that V2 job generation assigns correct APIs

# 1. Generate job
RESULT=$(curl -s -X POST http://localhost:8004/v1/job-generator \
  -H "Content-Type: application/json" \
  -d '{"user_requirement": "Google検索してメール送信"}')

JOB_ID=$(echo $RESULT | jq -r '.job_id')

# 2. Wait for completion
sleep 60

# 3. Check task breakdown
STATUS=$(curl -s "http://localhost:8004/v1/jobs/$JOB_ID/status")

# 4. Verify recommended_apis
TASK1_API=$(echo $STATUS | jq -r '.task_breakdown[0].recommended_apis[0]')
TASK2_API=$(echo $STATUS | jq -r '.task_breakdown[1].recommended_apis[0]')

if [[ "$TASK1_API" == *"google_search"* ]]; then
  echo "✅ Task 1 has correct API"
else
  echo "❌ Task 1 missing google_search API"
  exit 1
fi
```

## 5. 実装順序

| 順序 | Phase | タスク | 見積時間 |
|------|-------|--------|---------|
| 1 | P0 | `workflow.py` で capabilities を decomposer に渡す | 0.5h |
| 2 | P0 | `decomposer.py` に capabilities 対応追加 | 1h |
| 3 | P0 | `llm_utils.py` のシステムプロンプト拡張 | 1h |
| 4 | P0 | 単体テスト作成・実行 | 1h |
| 5 | P1 | `master_manager.py` の URL 解決ロジック追加 | 1.5h |
| 6 | P1 | `prompt_builder` の API 情報追加 | 1h |
| 7 | P1 | 結合テスト作成・実行 | 1h |
| 8 | - | 受入テスト・動作確認 | 1h |

**合計見積**: 8時間

## 6. リスクと対策

| リスク | 影響 | 対策 |
|--------|------|------|
| LLMがAPI情報を無視 | recommended_apis が空のまま | Few-shot例を追加、プロンプト強化 |
| 既存V1との互換性 | V1ジョブに影響 | V2のみに変更を限定 |
| API URL解決の失敗 | TaskMaster作成失敗 | フォールバックURL設定 |

## 7. 成功基準

1. タスク分割で `recommended_apis` が全タスクに設定される
2. TaskMaster の URL が API 固有エンドポイントを指す
3. ワークフロー生成が LLM ベースで成功する（テンプレートフォールバックなし）
4. 生成されたジョブが実行可能

---

**作成日**: 2026-01-07
**Issue**: #342
**関連ドキュメント**:
- `v2-workflow-quality-improvement-design.md`
- `v2-workflow-quality-work-plan.md`
