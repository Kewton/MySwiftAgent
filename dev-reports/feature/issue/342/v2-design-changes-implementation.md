# V2 設計変更 実装タスク一覧

## 概要

| 項目 | 値 |
|------|-----|
| Issue | #342 |
| 作成日 | 2026-01-09 |
| 参照ドキュメント | [v2-validator-design-review.md](./v2-validator-design-review.md) |
| ステータス | 実装準備完了 |

---

## 実装タスク一覧

### P0 (必須・即時対応)

| タスクID | 変更内容 | 対象ファイル | 見積 |
|---------|---------|-------------|------|
| DC-1 | 環境変数許可リスト追加 | `validators/agent_constraint_validator.py` | 30分 |
| DC-2 | V1互換パスパターン許可 | `validators/source_path_rule_engine.py` | 30分 |

### P1 (重要・次に対応)

| タスクID | 変更内容 | 対象ファイル | 見積 |
|---------|---------|-------------|------|
| DC-3 | テンプレートフォールバック修正 | `workflows/workflow_gen/yaml_generator.py` | 1時間 |

### P2 (改善・余裕があれば)

| タスクID | 変更内容 | 対象ファイル | 見積 |
|---------|---------|-------------|------|
| DC-4 | バリデーション厳格度設定 | `pipeline/validation_pipeline.py` | 30分 |

---

## DC-1: 環境変数許可リスト追加

### 対象ファイル
```
expertAgent/aiagent/langgraph/jobGeneratorV2/validators/agent_constraint_validator.py
```

### 変更内容

1. **定数追加** (ファイル先頭付近)

```python
# Allowed environment variables (resolved by graphAiServer at runtime)
# See: graphAiServer/src/services/graphai.ts:86-109
ALLOWED_ENV_VARS = {
    "${EXPERTAGENT_BASE_URL}",  # Resolved to http://localhost:8004 or configured URL
}
```

2. **validate_fetch_agent メソッド修正** (環境変数チェック部分)

```python
# Validate URL for environment variables
inputs = config.get("inputs", {})
url = inputs.get("url", "")

if isinstance(url, str) and url:
    for pattern in ENV_VAR_PATTERNS:
        match = pattern.search(url)
        if match:
            env_var = match.group(0)
            # Check if it's an allowed environment variable
            if env_var not in ALLOWED_ENV_VARS:
                errors.append(
                    f"URL contains unknown environment variable: '{env_var}'. "
                    f"Allowed: {', '.join(ALLOWED_ENV_VARS)}. "
                    "graphAiServer resolves these at runtime."
                )
            break  # Found a match, stop checking
```

### テスト追加

```python
# tests/unit/test_job_generator_v2/test_validators/test_agent_constraint_validator.py

def test_expertagent_base_url_allowed():
    """${EXPERTAGENT_BASE_URL} should be allowed."""
    validator = AgentConstraintValidator()
    config = {
        "agent": "fetchAgent",
        "inputs": {
            "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search"
        }
    }
    errors = validator.validate_fetch_agent(config)
    assert len(errors) == 0, f"Unexpected errors: {errors}"

def test_unknown_env_var_rejected():
    """Unknown environment variables should be rejected."""
    validator = AgentConstraintValidator()
    config = {
        "agent": "fetchAgent",
        "inputs": {
            "url": "${UNKNOWN_VAR}/api/endpoint"
        }
    }
    errors = validator.validate_fetch_agent(config)
    assert len(errors) == 1
    assert "unknown environment variable" in errors[0].lower()
```

---

## DC-2: V1互換パスパターン許可

### 対象ファイル
```
expertAgent/aiagent/langgraph/jobGeneratorV2/validators/source_path_rule_engine.py
```

### 変更内容

1. **定数の変更** (VALID_SOURCE_PREFIXES を VALID_SOURCE_PATTERNS に置換)

```python
import re

# V1 compatible: :source.fieldName (e.g., :source.query, :source.results)
# V2 extended: :source.user_input.fieldName, :source.job_params.fieldName
VALID_SOURCE_PATTERNS = [
    # V2 explicit patterns (preferred)
    re.compile(r"^:source\.user_input\.[\w\.]+$"),
    re.compile(r"^:source\.job_params\.[\w\.]+$"),
    # V1 compatible patterns (legacy support)
    re.compile(r"^:source\.[\w]+$"),  # :source.query, :source.results
    re.compile(r"^:source\.[\w]+\.[\w\.]+$"),  # :source.query.field
]

# Invalid patterns (must have at least one field after :source)
INVALID_SOURCE_PATTERNS = [
    re.compile(r"^:source$"),  # :source alone is invalid
    re.compile(r"^:source\.$"),  # :source. with trailing dot
]
```

2. **validate_path メソッド修正** (source参照のチェック部分)

```python
def validate_path(self, path: str | None) -> tuple[bool, str]:
    if path is None:
        return True, ""

    if not isinstance(path, str):
        return False, f"Path must be a string, got {type(path).__name__}"

    # Check source references
    if path.startswith(":source"):
        # Check for invalid patterns first
        for pattern in INVALID_SOURCE_PATTERNS:
            if pattern.match(path):
                return False, (
                    f"Invalid source path '{path}'. "
                    ":source must be followed by a field name "
                    "(e.g., :source.query, :source.user_input.data)"
                )

        # Check for valid patterns
        for pattern in VALID_SOURCE_PATTERNS:
            if pattern.match(path):
                return True, ""

        # If no pattern matched, provide helpful error
        return False, (
            f"Invalid source path '{path}'. "
            "Valid formats: :source.fieldName, :source.user_input.field, :source.job_params.field"
        )

    # Other path validations...
    return True, ""
```

### テスト追加

```python
# tests/unit/test_job_generator_v2/test_validators/test_source_path_rule_engine.py

import pytest
from expertAgent.aiagent.langgraph.jobGeneratorV2.validators.source_path_rule_engine import (
    SourcePathRuleEngine,
)

class TestV1CompatiblePaths:
    """Test V1 compatible path patterns."""

    @pytest.fixture
    def engine(self):
        return SourcePathRuleEngine()

    @pytest.mark.parametrize("path", [
        ":source.query",
        ":source.results",
        ":source.data",
        ":source.user_input.query",
        ":source.job_params.model_name",
        ":source.query.nested.field",
    ])
    def test_valid_v1_paths(self, engine, path):
        """V1 compatible paths should be valid."""
        is_valid, error = engine.validate_path(path)
        assert is_valid is True, f"Path '{path}' should be valid, got error: {error}"

    @pytest.mark.parametrize("path,expected_error", [
        (":source", ":source must be followed by a field name"),
        (":source.", ":source must be followed by a field name"),
    ])
    def test_invalid_paths(self, engine, path, expected_error):
        """Invalid paths should be rejected."""
        is_valid, error = engine.validate_path(path)
        assert is_valid is False
        assert expected_error in error
```

---

## DC-3: テンプレートフォールバック修正

### 対象ファイル
```
expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/yaml_generator.py
```

### 変更内容

`_build_nodes` メソッドを修正し、V1互換のfetchAgent設定を生成:

```python
def _build_nodes(
    self,
    task_master_ids: list[str],
    interfaces: dict[str, InterfaceSchema],
    task_id_mapping: TaskIdMapping | None = None,
) -> list[WorkflowNodeDefinition]:
    """Build V1-compatible node definitions with proper fetchAgent configuration."""
    nodes = []

    for idx, tm_id in enumerate(task_master_ids):
        task_id = tm_id.replace("tm_", "") if tm_id.startswith("tm_") else tm_id
        normalized_task_id = _normalize_task_id(tm_id, task_id_mapping)
        interface = interfaces.get(normalized_task_id)

        # Get API endpoint from interface
        api_endpoint = self._get_api_endpoint(interface)

        # Build V1-compatible inputs
        if idx == 0:
            body_inputs = self._build_initial_body(interface)
        else:
            prev_task_id = task_master_ids[idx - 1].replace("tm_", "")
            body_inputs = self._build_chained_body(interface, prev_task_id)

        inputs = {
            "url": f"${{EXPERTAGENT_BASE_URL}}{api_endpoint}",
            "method": "POST",
            "body": body_inputs,
        }

        node = WorkflowNodeDefinition(
            node_id=task_id,
            agent="fetchAgent",
            inputs=inputs,
            params={"task_master_id": tm_id},
            is_result=idx == len(task_master_ids) - 1,
            timeout=30000,  # 30 seconds default
        )
        nodes.append(node)

    return nodes

def _get_api_endpoint(self, interface: InterfaceSchema | None) -> str:
    """Get API endpoint path from interface or return default."""
    if interface and interface.recommended_api:
        return interface.recommended_api
    return "/aiagent-api/v1/utility/echo"  # Safe default

def _build_initial_body(self, interface: InterfaceSchema | None) -> dict:
    """Build request body for first task using source references."""
    if interface and interface.input_schema:
        body = {}
        for field in interface.input_schema.get("required", []):
            body[field] = f":source.{field}"
        return body
    return {"query": ":source.query"}  # V1 compatible default

def _build_chained_body(self, interface: InterfaceSchema | None, prev_task_id: str) -> dict:
    """Build request body for chained task using previous task output."""
    return {"data": f":{prev_task_id}.result"}
```

### テスト追加

```python
# tests/unit/test_job_generator_v2/test_yaml_generator_template.py

def test_build_nodes_generates_v1_compatible_yaml():
    """_build_nodes should generate V1-compatible fetchAgent config."""
    generator = YAMLGenerator()

    task_master_ids = ["tm_001", "tm_002"]
    interfaces = {
        "task_001": InterfaceSchema(
            recommended_api="/aiagent-api/v1/utility/google_search",
            input_schema={"required": ["query"]},
        ),
    }

    nodes = generator._build_nodes(task_master_ids, interfaces)

    # First node should have V1-compatible structure
    assert len(nodes) == 2
    assert nodes[0].inputs["url"] == "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search"
    assert nodes[0].inputs["method"] == "POST"
    assert "body" in nodes[0].inputs
    assert nodes[0].inputs["body"]["query"] == ":source.query"
```

---

## DC-4: バリデーション厳格度設定

### 対象ファイル
```
expertAgent/aiagent/langgraph/jobGeneratorV2/pipeline/validation_pipeline.py
```

### 変更内容

```python
from enum import Enum

class ValidationStrictness(Enum):
    """Validation strictness levels."""
    STRICT = "strict"       # All rules enforced (for new development)
    V1_COMPATIBLE = "v1"    # Allow V1 patterns (default for production)
    PERMISSIVE = "permissive"  # Minimal validation (for debugging)

class ValidationPipeline:
    def __init__(
        self,
        validators: list[WorkflowValidator] | None = None,
        observer: "ValidationObserver | None" = None,
        strictness: ValidationStrictness = ValidationStrictness.V1_COMPATIBLE,
    ):
        self.strictness = strictness

        if validators is None:
            self.validators = self._create_default_validators()
        else:
            self.validators = validators

        self.observer = observer

    def _create_default_validators(self) -> list[WorkflowValidator]:
        """Create validators based on strictness level."""
        if self.strictness == ValidationStrictness.PERMISSIVE:
            return []  # No validation

        # For both STRICT and V1_COMPATIBLE, use all validators
        # The validators themselves check their configuration
        validators = [
            SourcePathRuleEngine(v1_compatible=self.strictness == ValidationStrictness.V1_COMPATIBLE),
            AgentConstraintValidator(allow_known_env_vars=self.strictness == ValidationStrictness.V1_COMPATIBLE),
        ]

        return validators
```

---

## 実装順序

```
Phase 1: P0タスク (DC-1, DC-2)
├── DC-1: agent_constraint_validator.py 修正
├── DC-2: source_path_rule_engine.py 修正
├── テスト追加・実行
└── V2生成テスト (LLM生成が成功することを確認)

Phase 2: P1タスク (DC-3)
├── DC-3: yaml_generator.py 修正
├── テスト追加・実行
└── テンプレートフォールバックテスト

Phase 3: P2タスク (DC-4) + E2E検証
├── DC-4: validation_pipeline.py 修正
├── テスト追加・実行
└── UI経由でワークフロー生成・実行成功を確認
```

---

## 検証手順

### Phase 1完了後

```bash
# 単体テスト
PYTHONPATH=. uv run pytest tests/unit/test_job_generator_v2/test_validators/ -v

# V2でジョブ生成（LLM生成が成功することを確認）
USE_JOB_GENERATOR_V2=true ./scripts/dev-hybrid.sh
# → UIからジョブ生成、ログで "LLM generation successful" を確認
```

### Phase 2完了後

```bash
# テンプレート生成テスト
PYTHONPATH=. uv run pytest tests/unit/test_job_generator_v2/test_yaml_generator*.py -v

# フォールバックのみで動作確認
# → LLM生成を無効化し、テンプレート生成でも動作することを確認
```

### Phase 3完了後 (E2E検証)

```bash
# サービス起動
USE_JOB_GENERATOR_V2=true ./scripts/dev-hybrid.sh

# UIからジョブ生成・実行
# → v1.88+ が成功することを確認

# ログ確認
tail -f expertAgent/logs/expertagent.log | grep -E "(V2|workflow|validation)"
```

---

## 成功基準

| 基準 | 確認方法 |
|------|---------|
| LLM生成が成功する | ログに "LLM generation successful" |
| バリデーションエラーがない | ログに "validation error" がない |
| ワークフロー実行が成功する | v1.88+ のステータスが "completed" |
| V1との互換性維持 | v1.85 (V1) が引き続き動作する |

---

*このドキュメントは v2-validator-design-review.md の設計変更案を実装タスクとして整理したものです。*
