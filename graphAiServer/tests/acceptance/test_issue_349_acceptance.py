"""
Issue #349 L3 Acceptance Test: TaskFlow V2 Transform/Conditional Improvements

This test module verifies the acceptance criteria for Issue #349:
"TaskFlow V2: Tutorial verification issues (Transform/Conditional)"

Target Project: graphAiServer
Test Level: L3 (Local Acceptance Test)
Requires: graphAiServer running on http://localhost:8000

Acceptance Criteria:
AC-1: Map mode with @index, @first, @last helpers work correctly
AC-2: Merge mode auto-parses JSON strings
AC-3: Coalesce chain provides conditional output method
AC-4: Tutorial 9, 11, 12 execute successfully

Usage:
    cd graphAiServer
    uv run pytest tests/acceptance/test_issue_349_acceptance.py -v

Environment Variables:
    GRAPHAI_SERVER_URL: Override default server URL (default: http://localhost:8000)
"""

import json
import os
from pathlib import Path

import pytest
import requests

# Test configuration
BASE_URL = os.getenv("GRAPHAI_SERVER_URL", "http://localhost:8000")
API_V2_URL = f"{BASE_URL}/api/v2"

# Tutorial workflow paths
TUTORIAL_DIR = Path(__file__).parent.parent.parent / "config" / "taskflow" / "tutorial"


def load_tutorial(name: str) -> dict:
    """Load tutorial workflow definition from JSON file."""
    file_path = TUTORIAL_DIR / f"{name}.json"
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestIssue349TransformConditional:
    """L3 Acceptance Tests for Issue #349 Transform/Conditional Improvements."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Verify server is running before each test."""
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            assert response.status_code == 200
            health_data = response.json()
            assert health_data.get("status") == "healthy"
        except requests.RequestException as e:
            pytest.skip(f"graphAiServer not available at {BASE_URL}: {e}")

    def execute_workflow(self, definition: dict, inputs: dict) -> dict:
        """Execute a workflow via the v2 API."""
        response = requests.post(
            f"{API_V2_URL}/workflows/",
            json={
                "definition": definition,
                "inputs": inputs,
            },
            timeout=30,
        )
        assert response.status_code == 200, f"Response: {response.text}"
        return response.json()

    # ================================================================
    # AC-1: Map mode @index, @first, @last helpers
    # ================================================================

    def test_ac1_map_index_produces_numbered_list(self):
        """
        AC-1: Map mode @index helper produces numbered list.

        Expected: Template with {{@index}} produces "0. apple", "1. orange", "2. banana"
        """
        definition = load_tutorial("9_transform_map")
        result = self.execute_workflow(
            definition,
            {
                "products": [
                    {"name": "apple", "price": 150},
                    {"name": "orange", "price": 100},
                    {"name": "banana", "price": 200},
                ]
            },
        )

        # Check no errors in execution
        errors = result.get("errors", {})
        assert len(errors) == 0, f"Workflow had errors: {errors}"

        # Get output
        output = result.get("results", {}).get("_output", {})
        numbered_list = output.get("numbered_list", [])

        # STRICT assertion: verify numbered list contains indices
        if isinstance(numbered_list, list):
            numbered_str = "\n".join(numbered_list)
        else:
            numbered_str = str(numbered_list)

        assert "0." in numbered_str, f"@index not starting at 0: {numbered_str}"
        assert "1." in numbered_str, f"@index not incrementing to 1: {numbered_str}"
        assert "2." in numbered_str, f"@index not incrementing to 2: {numbered_str}"

    def test_ac1_map_last_helper_marks_final_item(self):
        """
        AC-1: Map mode @last helper marks the final item.

        Expected: Last item should have "(最後)" marker from {{#if @last}}
        """
        definition = load_tutorial("9_transform_map")
        result = self.execute_workflow(
            definition,
            {
                "products": [
                    {"name": "first_item", "price": 100},
                    {"name": "middle_item", "price": 200},
                    {"name": "last_item", "price": 300},
                ]
            },
        )

        errors = result.get("errors", {})
        assert len(errors) == 0, f"Workflow had errors: {errors}"

        output = result.get("results", {}).get("_output", {})
        numbered_list = output.get("numbered_list", [])

        if isinstance(numbered_list, list):
            numbered_str = "\n".join(numbered_list)
        else:
            numbered_str = str(numbered_list)

        # @last should mark the final item with 最後
        assert "最後" in numbered_str, f"@last helper not marking final item: {numbered_str}"

    # ================================================================
    # AC-2: Merge mode JSON auto-parse
    # ================================================================

    def test_ac2_merge_shallow_preserves_user_theme(self):
        """
        AC-2: Shallow merge correctly applies user settings over defaults.

        Expected:
        - theme: "dark" (user setting)
        - language: "ja" (default preserved)
        """
        definition = load_tutorial("11_transform_merge")
        result = self.execute_workflow(
            definition,
            {
                "user_settings": {
                    "theme": "dark",
                    "notifications": {"push": True},
                }
            },
        )

        errors = result.get("errors", {})
        assert len(errors) == 0, f"Workflow had errors: {errors}"

        output = result.get("results", {}).get("_output", {})
        shallow_config = output.get("shallow_config", {})

        # STRICT assertions for shallow merge
        assert shallow_config.get("theme") == "dark", f"User theme not applied: {shallow_config}"
        assert shallow_config.get("language") == "ja", (
            f"Default language not preserved: {shallow_config}"
        )

    def test_ac2_merge_deep_preserves_nested_defaults(self):
        """
        AC-2: Deep merge preserves nested default values.

        Expected:
        - notifications.push: true (user setting)
        - notifications.email: true (default preserved in deep merge)
        """
        definition = load_tutorial("11_transform_merge")
        result = self.execute_workflow(
            definition,
            {
                "user_settings": {
                    "theme": "dark",
                    "notifications": {"push": True},
                }
            },
        )

        errors = result.get("errors", {})
        assert len(errors) == 0, f"Workflow had errors: {errors}"

        output = result.get("results", {}).get("_output", {})
        deep_config = output.get("deep_config", {})

        # STRICT assertions for deep merge
        notifications = deep_config.get("notifications", {})
        assert notifications.get("push") == True, (
            f"User notification setting not applied: {notifications}"
        )
        assert notifications.get("email") == True, (
            f"Default email setting not preserved in deep merge: {notifications}"
        )

    # ================================================================
    # AC-3: Coalesce chain for conditional output
    # ================================================================

    def test_ac3_coalesce_returns_grade_a_for_high_score(self):
        """
        AC-3: Coalesce chain returns correct grade for score >= 80.

        Expected: grade = "A (優秀)"
        """
        definition = load_tutorial("12_conditional_basic")
        result = self.execute_workflow(definition, {"score": 85})

        errors = result.get("errors", {})
        assert len(errors) == 0, f"Workflow had errors: {errors}"

        output = result.get("results", {}).get("_output", {})

        # STRICT assertion: exact grade value
        grade = output.get("grade", "")
        assert grade == "A (優秀)", f"Expected 'A (優秀)' for score=85, got: {grade}"

        # STRICT assertion: message contains score
        message = output.get("message", "")
        assert "85" in message, f"Message should contain score 85: {message}"
        assert "合格" in message, f"Message should indicate pass: {message}"

    def test_ac3_coalesce_returns_grade_b_for_mid_score(self):
        """
        AC-3: Coalesce chain returns correct grade for 60 <= score < 80.

        Expected: grade = "B (合格)"
        """
        definition = load_tutorial("12_conditional_basic")
        result = self.execute_workflow(definition, {"score": 70})

        errors = result.get("errors", {})
        assert len(errors) == 0, f"Workflow had errors: {errors}"

        output = result.get("results", {}).get("_output", {})

        # STRICT assertion: exact grade value
        grade = output.get("grade", "")
        assert grade == "B (合格)", f"Expected 'B (合格)' for score=70, got: {grade}"

    def test_ac3_coalesce_returns_grade_c_for_low_score(self):
        """
        AC-3: Coalesce chain returns correct grade for score < 60.

        Expected: grade = "C (不合格)"
        """
        definition = load_tutorial("12_conditional_basic")
        result = self.execute_workflow(definition, {"score": 45})

        errors = result.get("errors", {})
        assert len(errors) == 0, f"Workflow had errors: {errors}"

        output = result.get("results", {}).get("_output", {})

        # STRICT assertion: exact grade value
        grade = output.get("grade", "")
        assert grade == "C (不合格)", f"Expected 'C (不合格)' for score=45, got: {grade}"

        # STRICT assertion: message indicates failure
        message = output.get("message", "")
        assert "45" in message, f"Message should contain score 45: {message}"
        assert "不合格" in message, f"Message should indicate fail: {message}"

    def test_ac3_coalesce_boundary_score_60(self):
        """
        AC-3: Boundary test - score=60 should be grade B (合格).
        """
        definition = load_tutorial("12_conditional_basic")
        result = self.execute_workflow(definition, {"score": 60})

        errors = result.get("errors", {})
        assert len(errors) == 0, f"Workflow had errors: {errors}"

        output = result.get("results", {}).get("_output", {})

        grade = output.get("grade", "")
        assert grade == "B (合格)", f"Expected 'B (合格)' for boundary score=60, got: {grade}"

    def test_ac3_coalesce_boundary_score_80(self):
        """
        AC-3: Boundary test - score=80 should be grade A (優秀).
        """
        definition = load_tutorial("12_conditional_basic")
        result = self.execute_workflow(definition, {"score": 80})

        errors = result.get("errors", {})
        assert len(errors) == 0, f"Workflow had errors: {errors}"

        output = result.get("results", {}).get("_output", {})

        grade = output.get("grade", "")
        assert grade == "A (優秀)", f"Expected 'A (優秀)' for boundary score=80, got: {grade}"

    # ================================================================
    # AC-4: Tutorial 9, 11, 12 regression tests
    # ================================================================

    def test_ac4_tutorial1_regression(self):
        """
        AC-4: Regression test - Tutorial 1 (Hello) still works.
        """
        definition = load_tutorial("1_hello")
        result = self.execute_workflow(definition, {})

        errors = result.get("errors", {})
        assert len(errors) == 0, f"Tutorial 1 regression failed: {errors}"

    def test_ac4_tutorial9_complete_workflow(self):
        """
        AC-4: Tutorial 9 complete workflow execution with all map features.
        """
        definition = load_tutorial("9_transform_map")
        result = self.execute_workflow(
            definition,
            {
                "products": [
                    {"name": "apple", "price": 150},
                    {"name": "orange", "price": 100},
                ]
            },
        )

        errors = result.get("errors", {})
        assert len(errors) == 0, f"Tutorial 9 failed: {errors}"

        output = result.get("results", {}).get("_output", {})
        assert output, "Tutorial 9 returned no output"

    def test_ac4_tutorial11_complete_workflow(self):
        """
        AC-4: Tutorial 11 complete workflow execution with both merge strategies.
        """
        definition = load_tutorial("11_transform_merge")
        result = self.execute_workflow(
            definition,
            {"user_settings": {"theme": "light"}},
        )

        errors = result.get("errors", {})
        assert len(errors) == 0, f"Tutorial 11 failed: {errors}"

        output = result.get("results", {}).get("_output", {})
        assert "shallow_config" in output, f"shallow_config missing: {output}"
        assert "deep_config" in output, f"deep_config missing: {output}"

    def test_ac4_tutorial12_complete_workflow(self):
        """
        AC-4: Tutorial 12 complete workflow with all output fields.
        """
        definition = load_tutorial("12_conditional_basic")
        result = self.execute_workflow(definition, {"score": 75})

        errors = result.get("errors", {})
        assert len(errors) == 0, f"Tutorial 12 failed: {errors}"

        output = result.get("results", {}).get("_output", {})
        assert "grade" in output, f"grade field missing: {output}"
        assert "message" in output, f"message field missing: {output}"

        # Verify grade is correct for score=75
        assert output.get("grade") == "B (合格)", (
            f"Expected 'B (合格)' for score=75, got: {output.get('grade')}"
        )
