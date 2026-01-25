# Issue #351 設計方針書

## 1. Issue概要

| 項目 | 内容 |
|------|------|
| Issue番号 | #351 |
| タイトル | TaskFlow V2: outputフィールドのJSON validation errorを修正 |
| 種別 | バグ修正 |
| 優先度 | 高（ワークフロー生成が完全に失敗） |
| 影響範囲 | TaskFlow V2 ワークフロー生成 |

## 2. 問題の詳細

### 2.1 現象

TaskFlow V2 ワークフロー生成時、LLMが `output` フィールドに変数参照（`${step.output}`）を含むJSON文字列を生成すると、Pydantic バリデーションエラーが発生する。

**エラーメッセージ:**
```
1 validation error for TaskFlowWorkflow
output
  Value error, Invalid JSON: Expecting value: line 1 column 20 (char 19)
  input_value='{"search_results": ${google_search.output.search_results}}'
```

### 2.2 発生条件

- TaskFlow V2 ワークフロー生成
- LLMが `output` フィールドに変数参照を生成
- 例: `{"result": "${step_001.output}"}`

### 2.3 根本原因

**設計上の矛盾が存在:**

| コンポーネント | 期待する動作 |
|---------------|-------------|
| プロンプトルール (`taskflow_rules.py`) | LLMに `${...}` 構文を使用するよう指示 |
| Few-shotパターン | `output: {"key": "${step.output}"}` を例示 |
| スキーマバリデーション | `json.loads()` で厳密なJSONパース → `${...}` を拒否 |

**問題箇所:** `taskflow_schema.py` の `validate_json_string` バリデーター

```python
@field_validator("input_schema", "output_schema", "output")
@classmethod
def validate_json_string(cls, value: str) -> str:
    import json as json_module
    try:
        parsed = json_module.loads(value)  # ← ここで ${...} が失敗
        if not isinstance(parsed, dict):
            raise ValueError(...)
        return value
    except json_module.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e
```

### 2.4 影響

- Langfuseトレース: 6回連続のChatOpenAIエラー
- 処理時間: 約5分47秒（すべて失敗）
- ワークフロー生成が100%失敗

## 3. 既存の変数参照ハンドリングパターン

### 3.1 URLフィールドのパターン（参考実装）

`taskflow_schema.py` の `validate_https_url` で変数参照を許可するパターンが存在:

```python
@field_validator("url")
@classmethod
def validate_https_url(cls, value: str | None) -> str | None:
    if value is None:
        return value

    # Allow variable references
    if value.startswith("${"):
        return value

    # 以降、通常のURL検証...
```

このパターンは `${inputs.url}` のような動的URL参照を許可している。

## 4. 解決策の設計

### 4.1 方針

**変数参照を含むJSON値を許可するバリデーションに変更**

変数参照（`${...}`）は実行時に解決されるため、スキーマバリデーション時点では「プレースホルダーを含む有効なJSON構造」として許可する必要がある。

### 4.2 推奨案: 変数参照を一時的に置換してJSONパース

変数参照を有効なJSONプレースホルダーに置換後、JSON構造を検証する。

## 5. 実装詳細

### 5.1 変更対象ファイル

| ファイル | 変更内容 |
|---------|---------|
| `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/schemas/variable_patterns.py` | **新規作成**: 変数パターン定数の共通モジュール |
| `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/schemas/taskflow_schema.py` | `validate_json_string` メソッドを修正、共通モジュールを使用 |
| `expertAgent/tests/unit/test_job_generator_v2/test_issue_351/test_variable_reference_validation.py` | **新規作成**: 変数参照バリデーションテスト |

### 5.2 共通モジュール: variable_patterns.py（SF-1対応）

```python
"""TaskFlow V2 Variable Pattern Definitions.

Issue #351: Centralized variable pattern definitions for TaskFlow V2.

This module provides:
- TASKFLOW_VARIABLE_PATTERN: Compiled regex for variable references
- contains_variable_reference(): Check if value contains variables
- replace_variables_with_placeholder(): Replace variables for validation
- mask_secret_references(): Mask ${secrets.*} for logging
"""

from __future__ import annotations

import re

# TaskFlow V2 variable reference pattern (MF-1: Unified pattern with hyphen support)
# Matches: ${inputs.query}, ${step_001.output}, ${step-001.output.data.name}, ${secrets.API_KEY}
# Pattern breakdown:
#   \$\{                           - Literal ${
#   [a-zA-Z_][a-zA-Z0-9_-]*        - Identifier (starts with letter/underscore, allows hyphen)
#   (?:\.[a-zA-Z_][a-zA-Z0-9_-]*)* - Optional dot-separated nested identifiers
#   \}                             - Literal }
TASKFLOW_VARIABLE_PATTERN = re.compile(
    r'\$\{[a-zA-Z_][a-zA-Z0-9_-]*(?:\.[a-zA-Z_][a-zA-Z0-9_-]*)*\}'
)

# Placeholder used during JSON validation
_VALIDATION_PLACEHOLDER = '"__TASKFLOW_VAR_PLACEHOLDER__"'


def contains_variable_reference(value: str) -> bool:
    """Check if value contains TaskFlow variable references.

    Args:
        value: String to check

    Returns:
        True if value contains ${...} variable references

    Example:
        >>> contains_variable_reference('{"result": "${step.output}"}')
        True
        >>> contains_variable_reference('{"result": "static"}')
        False
    """
    return bool(TASKFLOW_VARIABLE_PATTERN.search(value))


def replace_variables_with_placeholder(value: str) -> str:
    """Replace variable references with valid JSON placeholder.

    Used during validation to check JSON structure while allowing variables.

    Args:
        value: JSON string potentially containing variable references

    Returns:
        String with variables replaced by placeholder

    Example:
        >>> replace_variables_with_placeholder('{"result": "${step.output}"}')
        '{"result": "__TASKFLOW_VAR_PLACEHOLDER__"}'
    """
    return TASKFLOW_VARIABLE_PATTERN.sub(_VALIDATION_PLACEHOLDER, value)


def mask_secret_references(value: str) -> str:
    """Mask secret references for safe logging.

    Replaces ${secrets.KEY_NAME} with ${secrets.***} to prevent
    secret key names from appearing in logs.

    Args:
        value: String potentially containing secret references

    Returns:
        String with secret references masked

    Example:
        >>> mask_secret_references('Bearer ${secrets.API_TOKEN}')
        'Bearer ${secrets.***}'
    """
    return re.sub(r'\$\{secrets\.[^}]+\}', '${secrets.***}', value)


def validate_variable_syntax(value: str) -> list[str]:
    """Validate that all ${...} patterns have valid variable syntax.

    Returns list of invalid variable references found. Empty list means
    all variable references are valid.

    Args:
        value: String to validate

    Returns:
        List of invalid variable reference strings

    Example:
        >>> validate_variable_syntax('${valid.ref} and ${123invalid}')
        ['${123invalid}']
    """
    # Find all ${...} patterns (including potentially invalid ones)
    all_refs = re.findall(r'\$\{([^}]*)\}', value)
    invalid = []
    valid_pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_-]*(?:\.[a-zA-Z_][a-zA-Z0-9_-]*)*$')
    for ref in all_refs:
        if not valid_pattern.match(ref):
            invalid.append(f"${{{ref}}}")
    return invalid


__all__ = [
    "TASKFLOW_VARIABLE_PATTERN",
    "contains_variable_reference",
    "replace_variables_with_placeholder",
    "mask_secret_references",
    "validate_variable_syntax",
]
```

### 5.3 validate_json_string の修正（MF-1, SF-2対応）

```python
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.schemas.variable_patterns import (
    replace_variables_with_placeholder,
    mask_secret_references,
)

@field_validator("input_schema", "output_schema", "output")
@classmethod
def validate_json_string(cls, value: str) -> str:
    """Validate JSON string allowing TaskFlow variable references.

    Variable references like ${step.output} are replaced with placeholder
    strings during validation, then the original value is returned.

    This allows LLM-generated workflows to include dynamic references
    while still validating the JSON structure.

    Args:
        value: JSON string, potentially containing ${...} variable references

    Returns:
        Original value (unmodified) if valid

    Raises:
        ValueError: If JSON structure is invalid
    """
    import json as json_module

    # Replace variable references with valid JSON placeholders
    placeholder_value = replace_variables_with_placeholder(value)

    try:
        parsed = json_module.loads(placeholder_value)
        if not isinstance(parsed, dict):
            raise ValueError(f"Must be a JSON object, got {type(parsed).__name__}")
        return value  # Return original with variables intact
    except json_module.JSONDecodeError as e:
        # SF-2: Improved error message with original value (masked for security)
        masked_value = mask_secret_references(value)
        raise ValueError(
            f"Invalid JSON structure (variable references like ${{step.output}} are allowed): {e}. "
            f"Input: {masked_value[:200]}{'...' if len(masked_value) > 200 else ''}"
        ) from e
```

### 5.4 テストケース（SF-3対応）

```python
"""Unit tests for TaskFlow V2 variable reference validation.

Issue #351: Tests for variable reference handling in JSON fields.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.schemas.taskflow_schema import (
    TaskFlowStep,
    TaskFlowWorkflow,
    UnifiedStepConfig,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.schemas.variable_patterns import (
    TASKFLOW_VARIABLE_PATTERN,
    contains_variable_reference,
    mask_secret_references,
    replace_variables_with_placeholder,
    validate_variable_syntax,
)


class TestVariablePatternModule:
    """Tests for variable_patterns.py module."""

    def test_pattern_matches_simple_reference(self) -> None:
        """Pattern should match simple variable references."""
        assert TASKFLOW_VARIABLE_PATTERN.search("${inputs.query}")
        assert TASKFLOW_VARIABLE_PATTERN.search("${step_001.output}")

    def test_pattern_matches_nested_reference(self) -> None:
        """Pattern should match nested variable references."""
        assert TASKFLOW_VARIABLE_PATTERN.search("${step.output.data.name}")
        assert TASKFLOW_VARIABLE_PATTERN.search("${fetch_user.output.user.profile.email}")

    def test_pattern_matches_hyphenated_step_id(self) -> None:
        """Pattern should match step IDs with hyphens."""
        assert TASKFLOW_VARIABLE_PATTERN.search("${step-001.output}")
        assert TASKFLOW_VARIABLE_PATTERN.search("${my-step.output.data}")

    def test_pattern_matches_secrets_reference(self) -> None:
        """Pattern should match secrets references."""
        assert TASKFLOW_VARIABLE_PATTERN.search("${secrets.API_KEY}")
        assert TASKFLOW_VARIABLE_PATTERN.search("${secrets.GOOGLE_API_TOKEN}")

    def test_pattern_rejects_invalid_start(self) -> None:
        """Pattern should not match references starting with numbers."""
        match = TASKFLOW_VARIABLE_PATTERN.search("${123step.output}")
        assert match is None

    def test_contains_variable_reference_true(self) -> None:
        """contains_variable_reference returns True for strings with variables."""
        assert contains_variable_reference('{"result": "${step.output}"}') is True
        assert contains_variable_reference("URL: ${inputs.url}") is True

    def test_contains_variable_reference_false(self) -> None:
        """contains_variable_reference returns False for static strings."""
        assert contains_variable_reference('{"result": "static"}') is False
        assert contains_variable_reference("No variables here") is False

    def test_replace_variables_with_placeholder(self) -> None:
        """replace_variables_with_placeholder replaces all variable references."""
        result = replace_variables_with_placeholder('{"a": "${x.y}", "b": "${z}"}')
        assert "${" not in result
        assert "__TASKFLOW_VAR_PLACEHOLDER__" in result

    def test_mask_secret_references(self) -> None:
        """mask_secret_references masks secret key names."""
        result = mask_secret_references("Bearer ${secrets.API_TOKEN}")
        assert result == "Bearer ${secrets.***}"
        assert "API_TOKEN" not in result

    def test_mask_secret_preserves_non_secrets(self) -> None:
        """mask_secret_references preserves non-secret references."""
        result = mask_secret_references("${inputs.query} and ${secrets.KEY}")
        assert "${inputs.query}" in result
        assert "${secrets.***}" in result

    def test_validate_variable_syntax_valid(self) -> None:
        """validate_variable_syntax returns empty list for valid syntax."""
        assert validate_variable_syntax("${step.output}") == []
        assert validate_variable_syntax("${a.b.c.d}") == []
        assert validate_variable_syntax("${step-001.output}") == []

    def test_validate_variable_syntax_invalid(self) -> None:
        """validate_variable_syntax returns invalid references."""
        invalid = validate_variable_syntax("${123.invalid}")
        assert "${123.invalid}" in invalid

        invalid = validate_variable_syntax("${valid} and ${.invalid}")
        assert "${.invalid}" in invalid
        assert "${valid}" not in invalid


class TestVariableReferenceInOutput:
    """Tests for variable reference handling in TaskFlowWorkflow output field."""

    def _create_minimal_step(self) -> TaskFlowStep:
        """Create a minimal valid step for testing."""
        return TaskFlowStep(
            id="step_001",
            type="transform",
            config=UnifiedStepConfig(
                step_type="transform",
                mode="template",
                template="${inputs.query}",
            ),
        )

    def test_output_with_simple_variable(self) -> None:
        """Simple variable reference should be accepted."""
        workflow = TaskFlowWorkflow(
            workflow_name="test_workflow",
            input_schema='{"query": "string"}',
            output_schema='{"result": "string"}',
            steps=[self._create_minimal_step()],
            output='{"result": "${step_001.output}"}',
        )
        assert workflow.output == '{"result": "${step_001.output}"}'

    def test_output_with_nested_variable(self) -> None:
        """Nested variable reference should be accepted."""
        workflow = TaskFlowWorkflow(
            workflow_name="test_workflow",
            input_schema='{"query": "string"}',
            output_schema='{"data": "object"}',
            steps=[self._create_minimal_step()],
            output='{"data": "${step_001.output.data.items}"}',
        )
        assert workflow.output == '{"data": "${step_001.output.data.items}"}'

    def test_output_with_hyphenated_step_id(self) -> None:
        """Variable reference with hyphenated step ID should be accepted."""
        step = TaskFlowStep(
            id="fetch-user",
            type="transform",
            config=UnifiedStepConfig(
                step_type="transform",
                mode="template",
                template="${inputs.query}",
            ),
        )
        workflow = TaskFlowWorkflow(
            workflow_name="test_workflow",
            input_schema='{"query": "string"}',
            output_schema='{"result": "string"}',
            steps=[step],
            output='{"result": "${fetch-user.output}"}',
        )
        assert workflow.output == '{"result": "${fetch-user.output}"}'

    def test_output_with_mixed_content(self) -> None:
        """Mixed static and variable content should be accepted."""
        workflow = TaskFlowWorkflow(
            workflow_name="test_workflow",
            input_schema='{"query": "string"}',
            output_schema='{"status": "string", "data": "object"}',
            steps=[self._create_minimal_step()],
            output='{"status": "success", "data": "${step_001.output}"}',
        )
        assert '"status": "success"' in workflow.output
        assert "${step_001.output}" in workflow.output

    def test_output_with_multiple_variables(self) -> None:
        """Multiple variable references should be accepted."""
        step1 = TaskFlowStep(
            id="step_001",
            type="transform",
            config=UnifiedStepConfig(
                step_type="transform",
                mode="template",
                template="${inputs.query}",
            ),
        )
        step2 = TaskFlowStep(
            id="step_002",
            type="transform",
            config=UnifiedStepConfig(
                step_type="transform",
                mode="template",
                template="${step_001.output}",
            ),
        )
        workflow = TaskFlowWorkflow(
            workflow_name="test_workflow",
            input_schema='{"query": "string"}',
            output_schema='{"a": "string", "b": "string"}',
            steps=[step1, step2],
            output='{"a": "${step_001.output}", "b": "${step_002.output}"}',
        )
        assert "${step_001.output}" in workflow.output
        assert "${step_002.output}" in workflow.output

    def test_invalid_json_structure_with_variable(self) -> None:
        """Invalid JSON structure should still fail even with variables."""
        with pytest.raises(ValidationError) as exc_info:
            TaskFlowWorkflow(
                workflow_name="test_workflow",
                input_schema='{"query": "string"}',
                output_schema='{"result": "string"}',
                steps=[self._create_minimal_step()],
                output='{"result": ${step_001.output}}',  # Missing quotes around value
            )
        error_str = str(exc_info.value).lower()
        assert "json" in error_str

    def test_invalid_json_missing_brace(self) -> None:
        """Missing closing brace should fail validation."""
        with pytest.raises(ValidationError):
            TaskFlowWorkflow(
                workflow_name="test_workflow",
                input_schema='{"query": "string"}',
                output_schema='{"result": "string"}',
                steps=[self._create_minimal_step()],
                output='{"result": "${step.output}"',  # Missing closing }
            )

    def test_output_pure_static_json_still_works(self) -> None:
        """Pure static JSON without variables should still work."""
        workflow = TaskFlowWorkflow(
            workflow_name="test_workflow",
            input_schema='{"query": "string"}',
            output_schema='{"message": "string"}',
            steps=[self._create_minimal_step()],
            output='{"message": "Hello, World!"}',
        )
        assert workflow.output == '{"message": "Hello, World!"}'


class TestVariableReferenceInInputOutputSchema:
    """Tests for variable reference handling in input_schema and output_schema."""

    def _create_minimal_step(self) -> TaskFlowStep:
        """Create a minimal valid step for testing."""
        return TaskFlowStep(
            id="step_001",
            type="transform",
            config=UnifiedStepConfig(
                step_type="transform",
                mode="template",
                template="${inputs.query}",
            ),
        )

    def test_input_schema_static_only(self) -> None:
        """input_schema typically contains static type definitions."""
        workflow = TaskFlowWorkflow(
            workflow_name="test_workflow",
            input_schema='{"query": "string", "limit": "number"}',
            output_schema='{"result": "string"}',
            steps=[self._create_minimal_step()],
            output='{"result": "${step_001.output}"}',
        )
        assert workflow.input_schema == '{"query": "string", "limit": "number"}'

    def test_output_schema_static_only(self) -> None:
        """output_schema typically contains static type definitions."""
        workflow = TaskFlowWorkflow(
            workflow_name="test_workflow",
            input_schema='{"query": "string"}',
            output_schema='{"result": "array", "count": "number"}',
            steps=[self._create_minimal_step()],
            output='{"result": "${step_001.output}"}',
        )
        assert workflow.output_schema == '{"result": "array", "count": "number"}'


class TestLangfuseErrorScenario:
    """Reproduce the exact error scenario from Langfuse trace.

    Trace ID: e5eff2c5134442999d725b36f105a4dd
    Error: output field validation failed for variable reference.
    """

    def test_google_search_workflow_scenario(self) -> None:
        """Reproduce the Google search workflow that failed in production."""
        google_search_step = TaskFlowStep(
            id="google_search",
            type="api_rest",
            config=UnifiedStepConfig(
                step_type="api_rest",
                method="POST",
                url="http://localhost:8004/v1/utility/google_search",
                headers={"Content-Type": "application/json"},
                body='{"queries": ["${inputs.query}"], "num": 10}',
            ),
        )

        # This was failing before the fix
        workflow = TaskFlowWorkflow(
            workflow_name="google_search_workflow",
            description="Search Google and return results",
            input_schema='{"query": "string"}',
            output_schema='{"search_results": "array"}',
            steps=[google_search_step],
            output='{"search_results": "${google_search.output.search_results}"}',
        )

        # Verify the workflow was created successfully
        assert workflow.workflow_name == "google_search_workflow"
        assert "${google_search.output.search_results}" in workflow.output
```

## 6. リスク評価

| リスク | 影響度 | 発生確率 | 対策 |
|--------|--------|---------|------|
| 正規表現の性能 | 低 | 低 | 短い文字列なので影響なし |
| 変数参照パターンの漏れ | 低 | 低 | 統一パターンで網羅的にテスト済み |
| 後方互換性 | 低 | 低 | 既存の有効なJSONは変更なしで動作 |
| エラー位置のずれ | 低 | 中 | SF-2対応: 元の値をエラーメッセージに含める |
| シークレット漏洩 | 低 | 低 | mask_secret_references() でログ出力時にマスク |

## 7. 実装ステップ

1. **共通モジュール作成**
   - `variable_patterns.py` を新規作成
   - 変数パターン定数と関連関数を定義

2. **単体テスト作成（TDD）**
   - `test_variable_reference_validation.py` を新規作成
   - 全テストケースを実装

3. **スキーマ修正**
   - `taskflow_schema.py` の `validate_json_string` を修正
   - 共通モジュールをインポート

4. **結合テスト**
   - 実際のワークフロー生成での動作確認

5. **受入テスト**
   - Langfuseトレースでエラーが解消されることを確認

## 8. 完了条件

- [x] 正規表現パターンが統一されている（MF-1）
- [x] 変数パターン定数が共通モジュール化されている（SF-1）
- [x] エラーメッセージが改善されている（SF-2）
- [x] テストケースが完成している（SF-3）
- [ ] 変数参照を含むoutputフィールドがバリデーションを通過する
- [ ] 不正なJSON構造は引き続き拒否される
- [ ] 既存のテストがすべて通過する
- [ ] 新規テストケースがすべて通過する
- [ ] 実際のワークフロー生成でエラーが発生しない

## 9. 参考資料

- Langfuse トレース: `e5eff2c5134442999d725b36f105a4dd`
- 関連Issue: #350 (TaskFlow V2 基盤実装)
- 参考実装: `validate_https_url` の変数参照許可パターン

---

## 変更履歴

| 日付 | 変更内容 |
|------|---------|
| 2026-01-11 | 初版作成 |
| 2026-01-11 | アーキテクチャレビュー指摘事項対応（MF-1, SF-1, SF-2, SF-3） |
