"""Unit tests for Issue #177: YAML prompt migration.

This test suite verifies that all jobTaskGeneratorAgents and workflowGeneratorAgents
prompts have been successfully migrated to YAML format.

Tests cover:
- Existence of YAML files in prompts/ directory
- YAML structure validation
- Required fields presence
- Compatibility with PromptLoader
"""

from pathlib import Path

import pytest
import yaml

from app.services.prompt_loader import PromptLoader

# Base paths
EXPERT_AGENT_ROOT = Path(__file__).parent.parent.parent
PROMPTS_DIR = EXPERT_AGENT_ROOT / "prompts"


class TestJobTaskGeneratorPromptsYAML:
    """Test that all jobTaskGeneratorAgents prompts are migrated to YAML."""

    REQUIRED_PROMPTS = [
        "requirement_clarification",
        "task_breakdown",
        "interface_schema",
        "evaluation",
        "validation_fix",
    ]

    @pytest.mark.parametrize("prompt_name", REQUIRED_PROMPTS)
    def test_prompt_default_yaml_exists(self, prompt_name: str) -> None:
        """Test that default.yaml exists for each jobTaskGeneratorAgents prompt."""
        prompt_dir = PROMPTS_DIR / prompt_name
        default_yaml = prompt_dir / "default.yaml"

        assert prompt_dir.exists(), f"Prompt directory not found: {prompt_dir}"
        assert default_yaml.exists(), f"default.yaml not found for {prompt_name}"

    @pytest.mark.parametrize("prompt_name", REQUIRED_PROMPTS)
    def test_prompt_yaml_is_valid(self, prompt_name: str) -> None:
        """Test that YAML file is valid and parseable."""
        default_yaml = PROMPTS_DIR / prompt_name / "default.yaml"

        with open(default_yaml, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert isinstance(data, dict), f"{prompt_name} YAML must be a dictionary"
        assert len(data) > 0, f"{prompt_name} YAML must not be empty"

    @pytest.mark.parametrize("prompt_name", REQUIRED_PROMPTS)
    def test_prompt_has_system_prompt(self, prompt_name: str) -> None:
        """Test that each prompt has a system_prompt field."""
        default_yaml = PROMPTS_DIR / prompt_name / "default.yaml"

        with open(default_yaml, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert "system_prompt" in data, f"{prompt_name} must have system_prompt field"
        assert isinstance(data["system_prompt"], str), "system_prompt must be a string"
        assert len(data["system_prompt"]) > 0, "system_prompt must not be empty"

    @pytest.mark.parametrize("prompt_name", REQUIRED_PROMPTS)
    def test_prompt_loadable_via_promptloader(self, prompt_name: str) -> None:
        """Test that prompt can be loaded via PromptLoader."""
        loader = PromptLoader(base_dir=PROMPTS_DIR)

        # Should not raise exception
        data = loader.load_prompt(prompt_name)

        assert "system_prompt" in data
        assert isinstance(data["system_prompt"], str)


class TestWorkflowGeneratorPromptsYAML:
    """Test that workflowGeneratorAgents prompt is migrated to YAML."""

    def test_workflow_generation_yaml_exists(self) -> None:
        """Test that workflow_generation prompt has default.yaml."""
        prompt_dir = PROMPTS_DIR / "workflow_generation"
        default_yaml = prompt_dir / "default.yaml"

        assert prompt_dir.exists(), "workflow_generation directory not found"
        assert default_yaml.exists(), "default.yaml not found for workflow_generation"

    def test_workflow_generation_yaml_is_valid(self) -> None:
        """Test that workflow_generation YAML is valid."""
        default_yaml = PROMPTS_DIR / "workflow_generation" / "default.yaml"

        with open(default_yaml, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert isinstance(data, dict), "workflow_generation YAML must be a dictionary"
        assert len(data) > 0, "workflow_generation YAML must not be empty"

    def test_workflow_generation_has_system_prompt(self) -> None:
        """Test that workflow_generation has system_prompt field."""
        default_yaml = PROMPTS_DIR / "workflow_generation" / "default.yaml"

        with open(default_yaml, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert "system_prompt" in data, (
            "workflow_generation must have system_prompt field"
        )
        assert isinstance(data["system_prompt"], str), "system_prompt must be a string"
        assert len(data["system_prompt"]) > 0, "system_prompt must not be empty"

    def test_workflow_generation_loadable_via_promptloader(self) -> None:
        """Test that workflow_generation can be loaded via PromptLoader."""
        loader = PromptLoader(base_dir=PROMPTS_DIR)

        data = loader.load_prompt("workflow_generation")

        assert "system_prompt" in data
        assert isinstance(data["system_prompt"], str)


class TestPromptYAMLStructure:
    """Test YAML structure and metadata for all migrated prompts."""

    ALL_PROMPTS = [
        "requirement_clarification",
        "task_breakdown",
        "interface_schema",
        "evaluation",
        "validation_fix",
        "workflow_generation",
    ]

    @pytest.mark.parametrize("prompt_name", ALL_PROMPTS)
    def test_prompt_has_metadata(self, prompt_name: str) -> None:
        """Test that each prompt has metadata fields."""
        default_yaml = PROMPTS_DIR / prompt_name / "default.yaml"

        with open(default_yaml, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # At minimum, should have description
        # (version and other metadata are optional)
        assert "description" in data, f"{prompt_name} should have description field"

    @pytest.mark.parametrize("prompt_name", ALL_PROMPTS)
    def test_prompt_system_prompt_is_substantial(self, prompt_name: str) -> None:
        """Test that system_prompt has substantial content (>100 chars)."""
        default_yaml = PROMPTS_DIR / prompt_name / "default.yaml"

        with open(default_yaml, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        system_prompt = data.get("system_prompt", "")
        assert len(system_prompt) > 100, (
            f"{prompt_name} system_prompt is too short (should be >100 chars)"
        )


class TestPromptVersioning:
    """Test that prompts support versioning."""

    def test_can_load_default_version(self) -> None:
        """Test that default version can be loaded."""
        loader = PromptLoader(base_dir=PROMPTS_DIR)

        # Load without specifying version (should use default)
        data = loader.load_prompt("requirement_clarification")

        assert "system_prompt" in data

    def test_can_list_versions(self) -> None:
        """Test that versions can be listed."""
        loader = PromptLoader(base_dir=PROMPTS_DIR)

        versions = loader.list_versions("requirement_clarification")

        # At minimum, should have "default"
        assert "default" in versions
        assert isinstance(versions, list)
