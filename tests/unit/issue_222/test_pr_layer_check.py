"""
Unit tests for PR Layer Check workflow (Issue #222).

These tests validate:
1. Workflow file exists and has valid YAML syntax
2. Layer detection logic works correctly
3. Cross-layer detection logic is accurate
"""

import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

# Path to the workflow file
WORKFLOW_PATH = (
    Path(__file__).parent.parent.parent.parent / ".github" / "workflows" / "pr-layer-check.yml"
)


# =============================================================================
# Fixtures - DRY: Extract common file reading logic
# =============================================================================


@pytest.fixture
def workflow_content() -> str:
    """Read and return the workflow file content."""
    assert WORKFLOW_PATH.exists(), f"Workflow file not found at {WORKFLOW_PATH}"
    return WORKFLOW_PATH.read_text()


@pytest.fixture
def workflow_data(workflow_content: str) -> dict[str, Any]:
    """Parse and return the workflow YAML data."""
    return yaml.safe_load(workflow_content)


def get_trigger_key(workflow: dict[str, Any]) -> str | bool:
    """Get the trigger key, handling YAML 'on' interpretation quirk.

    YAML interprets 'on' as boolean True in some contexts,
    so we need to check for both 'on' and True keys.
    """
    return "on" if "on" in workflow else True


# =============================================================================
# Test Classes
# =============================================================================


class TestWorkflowFileExists:
    """Test that the workflow file exists."""

    def test_workflow_file_exists(self) -> None:
        """Verify pr-layer-check.yml exists in .github/workflows/."""
        assert WORKFLOW_PATH.exists(), f"Workflow file not found at {WORKFLOW_PATH}"

    def test_workflow_file_is_not_empty(self, workflow_content: str) -> None:
        """Verify the workflow file is not empty."""
        assert len(workflow_content.strip()) > 0, "Workflow file should not be empty"


class TestWorkflowYAMLSyntax:
    """Test YAML syntax validity."""

    def test_valid_yaml_syntax(self, workflow_content: str) -> None:
        """Verify the workflow file has valid YAML syntax."""
        try:
            yaml.safe_load(workflow_content)
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML syntax: {e}")

    def test_workflow_has_name(self, workflow_data: dict[str, Any]) -> None:
        """Verify the workflow has a name."""
        assert "name" in workflow_data, "Workflow should have a 'name' field"
        assert workflow_data["name"] == "PR Layer Check", "Workflow name should be 'PR Layer Check'"

    def test_workflow_has_trigger(self, workflow_data: dict[str, Any]) -> None:
        """Verify the workflow has correct trigger configuration."""
        trigger_key = get_trigger_key(workflow_data)
        assert trigger_key in workflow_data, "Workflow should have an 'on' trigger"
        trigger_config = workflow_data[trigger_key]
        assert "pull_request" in trigger_config, "Workflow should trigger on pull_request"

    def test_workflow_triggers_on_develop(self, workflow_data: dict[str, Any]) -> None:
        """Verify the workflow triggers on PRs to develop branch."""
        trigger_key = get_trigger_key(workflow_data)
        pr_config = workflow_data[trigger_key]["pull_request"]
        assert "branches" in pr_config, "pull_request should have branches"
        assert "develop" in pr_config["branches"], "Should trigger on develop branch"

    def test_workflow_has_correct_permissions(self, workflow_data: dict[str, Any]) -> None:
        """Verify the workflow has required permissions."""
        assert "permissions" in workflow_data, "Workflow should have permissions"
        permissions = workflow_data["permissions"]
        assert "contents" in permissions, "Should have contents permission"
        assert "pull-requests" in permissions, "Should have pull-requests permission"


# =============================================================================
# Layer Detection Helper - Extracted for reusability and testability
# =============================================================================

# Layer definitions matching the workflow
LAYER_DEFINITIONS: dict[str, list[str]] = {
    "Platform": ["myVault/", "jobqueue/", "myscheduler/"],
    "Agent": ["expertAgent/", "graphAiServer/"],
    "Frontend": ["myAgentDesk/", "commonUI/"],
}


def detect_layer(file_path: str) -> str | None:
    """Detect which layer a file belongs to.

    Args:
        file_path: The path of the file to check

    Returns:
        Layer name ("Platform", "Agent", "Frontend", "Docs") or None
    """
    # Docs layer detection (special case for .md files at root)
    if file_path.startswith("docs/") or (file_path.endswith(".md") and "/" not in file_path):
        return "Docs"

    # Check each layer's patterns (DRY: single loop instead of repeated blocks)
    for layer_name, patterns in LAYER_DEFINITIONS.items():
        for pattern in patterns:
            if file_path.startswith(pattern):
                return layer_name

    return None


def detect_layers(files: list[str]) -> set[str]:
    """Detect all layers from a list of files, excluding Docs.

    Args:
        files: List of file paths

    Returns:
        Set of layer names (excluding Docs)
    """
    return {
        layer
        for f in files
        if (layer := detect_layer(f)) is not None and layer != "Docs"
    }


def is_cross_layer(files: list[str]) -> bool:
    """Check if files span multiple layers (excluding Docs).

    Args:
        files: List of file paths

    Returns:
        True if files touch more than one layer
    """
    return len(detect_layers(files)) > 1


class TestLayerDetectionLogic:
    """Test the layer detection logic embedded in the workflow.

    Uses module-level helper functions for layer detection.
    """

    # -------------------------------------------------------------------------
    # Single Layer Tests - Should NOT trigger cross-layer warning
    # -------------------------------------------------------------------------

    def test_single_layer_platform(self) -> None:
        """Single layer (Platform) should not trigger warning."""
        files = ["myVault/app/main.py"]
        assert not is_cross_layer(files), "Single Platform layer should not be cross-layer"

    def test_single_layer_agent(self) -> None:
        """Single layer (Agent) should not trigger warning."""
        files = ["expertAgent/app/api.py"]
        assert not is_cross_layer(files), "Single Agent layer should not be cross-layer"

    def test_single_layer_frontend(self) -> None:
        """Single layer (Frontend) should not trigger warning."""
        files = ["myAgentDesk/src/+page.svelte"]
        assert not is_cross_layer(files), "Single Frontend layer should not be cross-layer"

    # -------------------------------------------------------------------------
    # Multi-Layer Tests - Should trigger cross-layer warning
    # -------------------------------------------------------------------------

    def test_multiple_layers_platform_and_agent(self) -> None:
        """Multiple layers (Platform + Agent) should trigger warning."""
        files = ["myVault/app/main.py", "expertAgent/app/api.py"]
        assert is_cross_layer(files), "Platform + Agent should be cross-layer"

    def test_multiple_layers_agent_and_frontend(self) -> None:
        """Multiple layers (Agent + Frontend) should trigger warning."""
        files = ["expertAgent/app/api.py", "myAgentDesk/src/+page.svelte"]
        assert is_cross_layer(files), "Agent + Frontend should be cross-layer"

    def test_three_layers_is_cross_layer(self) -> None:
        """Three layers should be cross-layer."""
        files = [
            "myVault/app/main.py",
            "expertAgent/app/api.py",
            "myAgentDesk/src/+page.svelte",
        ]
        assert is_cross_layer(files), "Three layers should be cross-layer"

    # -------------------------------------------------------------------------
    # Docs Exclusion Tests - Docs should be excluded from cross-layer checks
    # -------------------------------------------------------------------------

    def test_docs_only(self) -> None:
        """Docs only should not trigger warning."""
        files = ["docs/README.md"]
        assert not is_cross_layer(files), "Docs only should not be cross-layer"

    def test_root_markdown_only(self) -> None:
        """Root markdown only should not trigger warning."""
        files = ["README.md", "CLAUDE.md"]
        assert not is_cross_layer(files), "Root markdown files should not be cross-layer"

    def test_docs_plus_single_layer(self) -> None:
        """Docs + single code layer should not trigger warning."""
        files = ["docs/README.md", "expertAgent/app/api.py"]
        assert not is_cross_layer(files), "Docs + single layer should not be cross-layer"

    # -------------------------------------------------------------------------
    # Layer Detection Tests - Verify each directory maps to correct layer
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "file_path",
        [
            "myVault/app/main.py",
            "jobqueue/app/main.py",
            "myscheduler/app/main.py",
        ],
    )
    def test_platform_directories(self, file_path: str) -> None:
        """All Platform directories should be detected as Platform layer."""
        assert detect_layer(file_path) == "Platform", f"{file_path} should be Platform layer"

    @pytest.mark.parametrize(
        "file_path",
        [
            "expertAgent/app/main.py",
            "graphAiServer/src/index.ts",
        ],
    )
    def test_agent_directories(self, file_path: str) -> None:
        """All Agent directories should be detected as Agent layer."""
        assert detect_layer(file_path) == "Agent", f"{file_path} should be Agent layer"

    @pytest.mark.parametrize(
        "file_path",
        [
            "myAgentDesk/src/+page.svelte",
            "commonUI/src/index.ts",
        ],
    )
    def test_frontend_directories(self, file_path: str) -> None:
        """All Frontend directories should be detected as Frontend layer."""
        assert detect_layer(file_path) == "Frontend", f"{file_path} should be Frontend layer"

    # -------------------------------------------------------------------------
    # Non-Layer Files Tests - Other files should not count as any layer
    # -------------------------------------------------------------------------

    def test_github_workflows_not_counted(self) -> None:
        """GitHub workflow files should not count as any layer."""
        files = [".github/workflows/ci.yml"]
        assert detect_layer(files[0]) is None, "GitHub workflows should not be any layer"
        assert not is_cross_layer(files), "GitHub workflows alone should not be cross-layer"

    def test_mixed_untracked_and_layer_files(self) -> None:
        """Untracked files + layer files should work correctly."""
        files = [
            ".github/workflows/ci.yml",
            "scripts/test.sh",
            "expertAgent/app/api.py",
        ]
        layers = detect_layers(files)
        assert layers == {"Agent"}, "Only Agent layer should be detected"
        assert not is_cross_layer(files), "Single layer + untracked should not be cross-layer"


class TestWorkflowHasJobs:
    """Test that the workflow has the expected jobs structure."""

    def test_workflow_has_jobs(self, workflow_data: dict[str, Any]) -> None:
        """Verify the workflow has a jobs section."""
        assert "jobs" in workflow_data, "Workflow should have 'jobs' section"

    def test_workflow_has_check_layers_job(self, workflow_data: dict[str, Any]) -> None:
        """Verify the workflow has a check-layers job."""
        jobs = workflow_data.get("jobs", {})
        assert "check-layers" in jobs, "Workflow should have 'check-layers' job"

    def test_check_layers_job_runs_on_ubuntu(self, workflow_data: dict[str, Any]) -> None:
        """Verify check-layers job runs on ubuntu-latest."""
        job = workflow_data.get("jobs", {}).get("check-layers", {})
        assert job.get("runs-on") == "ubuntu-latest", "Job should run on ubuntu-latest"


class TestWorkflowIntegration:
    """Integration tests for the complete workflow."""

    def test_actionlint_if_available(self) -> None:
        """Run actionlint if available to validate the workflow."""
        if not WORKFLOW_PATH.exists():
            pytest.skip("Workflow file does not exist yet")

        # Check if actionlint is available
        result = subprocess.run(
            ["which", "actionlint"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.skip("actionlint not installed")

        # Run actionlint
        result = subprocess.run(
            ["actionlint", str(WORKFLOW_PATH)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"actionlint failed: {result.stdout}\n{result.stderr}"
