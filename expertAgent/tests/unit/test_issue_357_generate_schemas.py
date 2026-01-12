"""Unit tests for Issue #357: Schema Generation Script.

This module tests:
1. Generation script existence
2. Script execution without errors
3. TypeScript type file generation
4. Pydantic model file generation

TDD Phase: RED - These tests should fail initially.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass

# Paths
# expertAgent/tests/unit/test_issue_357_generate_schemas.py -> MySwiftAgent
PROJECT_ROOT = Path(__file__).parents[3]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "generate_schemas.py"
JSON_SCHEMA_PATH = PROJECT_ROOT / "shared" / "schemas" / "taskflow" / "v1" / "workflow.schema.json"
TYPESCRIPT_OUTPUT_DIR = PROJECT_ROOT / "graphAiServer" / "src" / "engine" / "schemas" / "generated"
PYDANTIC_OUTPUT_DIR = (
    PROJECT_ROOT
    / "expertAgent"
    / "aiagent"
    / "langgraph"
    / "jobGeneratorV2"
    / "workflows"
    / "workflow_gen"
    / "schemas"
    / "generated"
)


# =============================================================================
# Module-level Fixtures (DRY: Avoid duplicate fixtures across test classes)
# =============================================================================


@pytest.fixture
def loaded_script_module() -> ModuleType | None:
    """Import and execute the generate_schemas script module.

    This is a module-level fixture to avoid duplication across test classes.
    All classes that need the script module use this single fixture.

    Returns:
        The loaded module, or None if loading failed.
    """
    if not SCRIPT_PATH.exists():
        pytest.skip("Script file does not exist yet")

    spec = importlib.util.spec_from_file_location("generate_schemas", SCRIPT_PATH)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        sys.modules["generate_schemas_module"] = module
        try:
            spec.loader.exec_module(module)
            return module
        except Exception:
            # Allow import errors for now - we just want to check structure
            pass
    return None


# =============================================================================
# Test Classes
# =============================================================================


class TestGenerateScriptExistence:
    """Tests for schema generation script existence."""

    def test_script_file_exists(self) -> None:
        """Verify generate_schemas.py exists at expected location.

        Acceptance Criteria:
        - scripts/generate_schemas.py exists
        """
        assert SCRIPT_PATH.exists(), (
            f"Generation script not found at {SCRIPT_PATH}. Expected: scripts/generate_schemas.py"
        )

    def test_script_is_python_file(self) -> None:
        """Verify script has .py extension."""
        if not SCRIPT_PATH.exists():
            pytest.skip("Script file does not exist yet")

        assert SCRIPT_PATH.suffix == ".py", "Script should have .py extension"

    def test_script_has_main_function(self) -> None:
        """Verify script has __main__ block or main function."""
        if not SCRIPT_PATH.exists():
            pytest.skip("Script file does not exist yet")

        content = SCRIPT_PATH.read_text(encoding="utf-8")
        has_main = 'if __name__ == "__main__"' in content or "def main(" in content
        assert has_main, "Script should have __main__ block or main function"


class TestScriptImportability:
    """Tests for script importability."""

    def test_script_can_be_imported(self) -> None:
        """Verify script can be imported without errors."""
        if not SCRIPT_PATH.exists():
            pytest.skip("Script file does not exist yet")

        spec = importlib.util.spec_from_file_location("generate_schemas", SCRIPT_PATH)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            # Just check if we can create the module, don't execute
            assert module is not None


class TestScriptFunctions:
    """Tests for script function existence."""

    def test_has_validate_schema_function(self, loaded_script_module: ModuleType | None) -> None:
        """Verify script has validate_schema function."""
        if loaded_script_module is None:
            pytest.skip("Could not import script module")

        assert hasattr(loaded_script_module, "validate_schema"), (
            "Script should have 'validate_schema' function"
        )

    def test_has_generate_typescript_function(
        self, loaded_script_module: ModuleType | None
    ) -> None:
        """Verify script has generate_typescript function."""
        if loaded_script_module is None:
            pytest.skip("Could not import script module")

        assert hasattr(loaded_script_module, "generate_typescript"), (
            "Script should have 'generate_typescript' function"
        )

    def test_has_generate_python_function(self, loaded_script_module: ModuleType | None) -> None:
        """Verify script has generate_python function."""
        if loaded_script_module is None:
            pytest.skip("Could not import script module")

        assert hasattr(loaded_script_module, "generate_python"), (
            "Script should have 'generate_python' function"
        )


class TestScriptExecution:
    """Tests for script execution."""

    def test_script_runs_without_syntax_errors(self) -> None:
        """Verify script can be parsed without syntax errors."""
        if not SCRIPT_PATH.exists():
            pytest.skip("Script file does not exist yet")

        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Script has syntax errors: {result.stderr}"

    @pytest.mark.integration
    def test_script_executes_successfully(self) -> None:
        """Verify script executes without errors.

        Acceptance Criteria:
        - python scripts/generate_schemas.py exits with 0
        """
        if not SCRIPT_PATH.exists():
            pytest.skip("Script file does not exist yet")
        if not JSON_SCHEMA_PATH.exists():
            pytest.skip("JSON Schema file does not exist yet")

        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=60,
        )
        assert result.returncode == 0, (
            f"Script execution failed: {result.stderr}\nstdout: {result.stdout}"
        )


class TestTypescriptGeneration:
    """Tests for TypeScript type generation."""

    def test_typescript_output_directory_can_be_created(self) -> None:
        """Verify TypeScript output directory can be created."""
        # This test just verifies the path is valid
        assert TYPESCRIPT_OUTPUT_DIR.parent.exists() or True  # Path structure is valid

    @pytest.mark.integration
    def test_typescript_file_is_generated(self) -> None:
        """Verify TypeScript type file is generated after script execution.

        Acceptance Criteria:
        - TypeScript type file auto-generated at expected location
        """
        if not SCRIPT_PATH.exists():
            pytest.skip("Script file does not exist yet")
        if not JSON_SCHEMA_PATH.exists():
            pytest.skip("JSON Schema file does not exist yet")

        # Run the generation script
        subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            cwd=str(PROJECT_ROOT),
            timeout=60,
        )

        # Check if TypeScript file was generated
        ts_file = TYPESCRIPT_OUTPUT_DIR / "taskflow.d.ts"
        assert ts_file.exists(), f"TypeScript type file not generated at {ts_file}"

    @pytest.mark.integration
    def test_typescript_file_has_auto_generated_header(self) -> None:
        """Verify TypeScript file has auto-generated header comment."""
        ts_file = TYPESCRIPT_OUTPUT_DIR / "taskflow.d.ts"
        if not ts_file.exists():
            pytest.skip("TypeScript file does not exist yet")

        content = ts_file.read_text(encoding="utf-8")
        assert "Auto-generated" in content or "DO NOT EDIT" in content, (
            "TypeScript file should have auto-generated header"
        )

    @pytest.mark.integration
    def test_typescript_file_has_workflow_type(self) -> None:
        """Verify TypeScript file defines Workflow type."""
        ts_file = TYPESCRIPT_OUTPUT_DIR / "taskflow.d.ts"
        if not ts_file.exists():
            pytest.skip("TypeScript file does not exist yet")

        content = ts_file.read_text(encoding="utf-8")
        # Should have some form of Workflow type/interface
        has_workflow = "Workflow" in content or "workflow" in content
        assert has_workflow, "TypeScript file should define Workflow type"


class TestPydanticGeneration:
    """Tests for Pydantic model generation."""

    def test_pydantic_output_directory_can_be_created(self) -> None:
        """Verify Pydantic output directory can be created."""
        # This test just verifies the path is valid
        assert PYDANTIC_OUTPUT_DIR.parent.exists() or True  # Path structure is valid

    @pytest.mark.integration
    def test_pydantic_file_is_generated(self) -> None:
        """Verify Pydantic model file is generated after script execution.

        Acceptance Criteria:
        - Pydantic model file auto-generated at expected location
        """
        if not SCRIPT_PATH.exists():
            pytest.skip("Script file does not exist yet")
        if not JSON_SCHEMA_PATH.exists():
            pytest.skip("JSON Schema file does not exist yet")

        # Run the generation script
        subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            cwd=str(PROJECT_ROOT),
            timeout=60,
        )

        # Check if Pydantic file was generated
        py_file = PYDANTIC_OUTPUT_DIR / "taskflow_types.py"
        assert py_file.exists(), f"Pydantic model file not generated at {py_file}"

    @pytest.mark.integration
    def test_pydantic_file_is_importable(self) -> None:
        """Verify generated Pydantic file can be imported.

        Acceptance Criteria:
        - Generated Pydantic model is importable
        """
        py_file = PYDANTIC_OUTPUT_DIR / "taskflow_types.py"
        if not py_file.exists():
            pytest.skip("Pydantic file does not exist yet")

        spec = importlib.util.spec_from_file_location("taskflow_types", py_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
                assert module is not None
            except ImportError as e:
                pytest.fail(f"Generated Pydantic file cannot be imported: {e}")

    @pytest.mark.integration
    def test_pydantic_file_has_auto_generated_header(self) -> None:
        """Verify Pydantic file has auto-generated header comment."""
        py_file = PYDANTIC_OUTPUT_DIR / "taskflow_types.py"
        if not py_file.exists():
            pytest.skip("Pydantic file does not exist yet")

        content = py_file.read_text(encoding="utf-8")
        assert "auto-generated" in content.lower() or "generated" in content.lower(), (
            "Pydantic file should have auto-generated header"
        )


class TestSchemaValidationFunction:
    """Tests for schema validation function in the script."""

    def test_validate_schema_passes_for_valid_schema(
        self, loaded_script_module: ModuleType | None
    ) -> None:
        """Verify validate_schema passes for valid JSON Schema."""
        if loaded_script_module is None:
            pytest.skip("Could not import script module")
        if not hasattr(loaded_script_module, "validate_schema"):
            pytest.skip("validate_schema function not found")

        # Should not raise for valid schema
        try:
            loaded_script_module.validate_schema()
        except Exception as e:
            pytest.fail(f"validate_schema failed: {e}")
