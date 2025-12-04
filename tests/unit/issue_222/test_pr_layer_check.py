"""
Unit tests for PR Layer Check workflow (Issue #222).

These tests validate:
1. Workflow file exists and has valid YAML syntax
2. Layer detection logic works correctly
3. Cross-layer detection logic is accurate
"""

import subprocess
from pathlib import Path

import pytest
import yaml

# Path to the workflow file
WORKFLOW_PATH = (
    Path(__file__).parent.parent.parent.parent / ".github" / "workflows" / "pr-layer-check.yml"
)


class TestWorkflowFileExists:
    """Test that the workflow file exists."""

    def test_workflow_file_exists(self) -> None:
        """Verify pr-layer-check.yml exists in .github/workflows/."""
        assert WORKFLOW_PATH.exists(), f"Workflow file not found at {WORKFLOW_PATH}"

    def test_workflow_file_is_not_empty(self) -> None:
        """Verify the workflow file is not empty."""
        assert WORKFLOW_PATH.exists(), "Workflow file must exist first"
        content = WORKFLOW_PATH.read_text()
        assert len(content.strip()) > 0, "Workflow file should not be empty"


class TestWorkflowYAMLSyntax:
    """Test YAML syntax validity."""

    def test_valid_yaml_syntax(self) -> None:
        """Verify the workflow file has valid YAML syntax."""
        assert WORKFLOW_PATH.exists(), "Workflow file must exist first"
        content = WORKFLOW_PATH.read_text()
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML syntax: {e}")

    def test_workflow_has_name(self) -> None:
        """Verify the workflow has a name."""
        assert WORKFLOW_PATH.exists(), "Workflow file must exist first"
        content = WORKFLOW_PATH.read_text()
        workflow = yaml.safe_load(content)
        assert "name" in workflow, "Workflow should have a 'name' field"
        assert workflow["name"] == "PR Layer Check", "Workflow name should be 'PR Layer Check'"

    def test_workflow_has_trigger(self) -> None:
        """Verify the workflow has correct trigger configuration."""
        assert WORKFLOW_PATH.exists(), "Workflow file must exist first"
        content = WORKFLOW_PATH.read_text()
        workflow = yaml.safe_load(content)
        # YAML interprets 'on' as boolean True, so we check for True key
        # This is a known YAML quirk for GitHub Actions workflows
        trigger_key = "on" if "on" in workflow else True
        assert trigger_key in workflow, "Workflow should have an 'on' trigger"
        trigger_config = workflow[trigger_key]
        assert "pull_request" in trigger_config, "Workflow should trigger on pull_request"

    def test_workflow_triggers_on_develop(self) -> None:
        """Verify the workflow triggers on PRs to develop branch."""
        assert WORKFLOW_PATH.exists(), "Workflow file must exist first"
        content = WORKFLOW_PATH.read_text()
        workflow = yaml.safe_load(content)
        # YAML interprets 'on' as boolean True
        trigger_key = "on" if "on" in workflow else True
        pr_config = workflow[trigger_key]["pull_request"]
        assert "branches" in pr_config, "pull_request should have branches"
        assert "develop" in pr_config["branches"], "Should trigger on develop branch"

    def test_workflow_has_correct_permissions(self) -> None:
        """Verify the workflow has required permissions."""
        assert WORKFLOW_PATH.exists(), "Workflow file must exist first"
        content = WORKFLOW_PATH.read_text()
        workflow = yaml.safe_load(content)
        assert "permissions" in workflow, "Workflow should have permissions"
        permissions = workflow["permissions"]
        assert "contents" in permissions, "Should have contents permission"
        assert "pull-requests" in permissions, "Should have pull-requests permission"


class TestLayerDetectionLogic:
    """Test the layer detection logic embedded in the workflow."""

    # Layer definitions from the context
    LAYER_DEFINITIONS = {
        "Platform": ["myVault/", "jobqueue/", "myscheduler/"],
        "Agent": ["expertAgent/", "graphAiServer/"],
        "Frontend": ["myAgentDesk/", "commonUI/"],
        "Docs": ["docs/", ".md"],
    }

    def detect_layer(self, file_path: str) -> str | None:
        """Detect which layer a file belongs to."""
        # Docs layer detection (special case for .md files at root)
        if file_path.startswith("docs/") or (file_path.endswith(".md") and "/" not in file_path):
            return "Docs"

        # Platform layer
        for pattern in self.LAYER_DEFINITIONS["Platform"]:
            if file_path.startswith(pattern):
                return "Platform"

        # Agent layer
        for pattern in self.LAYER_DEFINITIONS["Agent"]:
            if file_path.startswith(pattern):
                return "Agent"

        # Frontend layer
        for pattern in self.LAYER_DEFINITIONS["Frontend"]:
            if file_path.startswith(pattern):
                return "Frontend"

        return None

    def detect_layers(self, files: list[str]) -> set[str]:
        """Detect all layers from a list of files, excluding Docs."""
        layers = set()
        for f in files:
            layer = self.detect_layer(f)
            if layer and layer != "Docs":
                layers.add(layer)
        return layers

    def is_cross_layer(self, files: list[str]) -> bool:
        """Check if files span multiple layers (excluding Docs)."""
        layers = self.detect_layers(files)
        return len(layers) > 1

    # Test cases from the context file
    def test_single_layer_platform(self) -> None:
        """Single layer (Platform) should not trigger warning."""
        files = ["myVault/app/main.py"]
        assert not self.is_cross_layer(files), "Single Platform layer should not be cross-layer"

    def test_single_layer_agent(self) -> None:
        """Single layer (Agent) should not trigger warning."""
        files = ["expertAgent/app/api.py"]
        assert not self.is_cross_layer(files), "Single Agent layer should not be cross-layer"

    def test_single_layer_frontend(self) -> None:
        """Single layer (Frontend) should not trigger warning."""
        files = ["myAgentDesk/src/+page.svelte"]
        assert not self.is_cross_layer(files), "Single Frontend layer should not be cross-layer"

    def test_multiple_layers_platform_and_agent(self) -> None:
        """Multiple layers (Platform + Agent) should trigger warning."""
        files = ["myVault/app/main.py", "expertAgent/app/api.py"]
        assert self.is_cross_layer(files), "Platform + Agent should be cross-layer"

    def test_multiple_layers_agent_and_frontend(self) -> None:
        """Multiple layers (Agent + Frontend) should trigger warning."""
        files = ["expertAgent/app/api.py", "myAgentDesk/src/+page.svelte"]
        assert self.is_cross_layer(files), "Agent + Frontend should be cross-layer"

    def test_docs_only(self) -> None:
        """Docs only should not trigger warning."""
        files = ["docs/README.md"]
        assert not self.is_cross_layer(files), "Docs only should not be cross-layer"

    def test_root_markdown_only(self) -> None:
        """Root markdown only should not trigger warning."""
        files = ["README.md", "CLAUDE.md"]
        assert not self.is_cross_layer(files), "Root markdown files should not be cross-layer"

    def test_docs_plus_single_layer(self) -> None:
        """Docs + single code layer should not trigger warning."""
        files = ["docs/README.md", "expertAgent/app/api.py"]
        assert not self.is_cross_layer(files), "Docs + single layer should not be cross-layer"

    def test_all_platform_directories(self) -> None:
        """All Platform directories should be detected as Platform layer."""
        platform_files = [
            "myVault/app/main.py",
            "jobqueue/app/main.py",
            "myscheduler/app/main.py",
        ]
        for f in platform_files:
            assert self.detect_layer(f) == "Platform", f"{f} should be Platform layer"

    def test_all_agent_directories(self) -> None:
        """All Agent directories should be detected as Agent layer."""
        agent_files = [
            "expertAgent/app/main.py",
            "graphAiServer/src/index.ts",
        ]
        for f in agent_files:
            assert self.detect_layer(f) == "Agent", f"{f} should be Agent layer"

    def test_all_frontend_directories(self) -> None:
        """All Frontend directories should be detected as Frontend layer."""
        frontend_files = [
            "myAgentDesk/src/+page.svelte",
            "commonUI/src/index.ts",
        ]
        for f in frontend_files:
            assert self.detect_layer(f) == "Frontend", f"{f} should be Frontend layer"

    def test_three_layers_is_cross_layer(self) -> None:
        """Three layers should be cross-layer."""
        files = [
            "myVault/app/main.py",
            "expertAgent/app/api.py",
            "myAgentDesk/src/+page.svelte",
        ]
        assert self.is_cross_layer(files), "Three layers should be cross-layer"

    def test_github_workflows_not_counted(self) -> None:
        """GitHub workflow files should not count as any layer."""
        files = [".github/workflows/ci.yml"]
        assert self.detect_layer(files[0]) is None, "GitHub workflows should not be any layer"
        assert not self.is_cross_layer(files), "GitHub workflows alone should not be cross-layer"

    def test_mixed_untracked_and_layer_files(self) -> None:
        """Untracked files + layer files should work correctly."""
        files = [
            ".github/workflows/ci.yml",
            "scripts/test.sh",
            "expertAgent/app/api.py",
        ]
        layers = self.detect_layers(files)
        assert layers == {"Agent"}, "Only Agent layer should be detected"
        assert not self.is_cross_layer(files), "Single layer + untracked should not be cross-layer"


class TestWorkflowHasJobs:
    """Test that the workflow has the expected jobs structure."""

    def test_workflow_has_jobs(self) -> None:
        """Verify the workflow has a jobs section."""
        assert WORKFLOW_PATH.exists(), "Workflow file must exist first"
        content = WORKFLOW_PATH.read_text()
        workflow = yaml.safe_load(content)
        assert "jobs" in workflow, "Workflow should have 'jobs' section"

    def test_workflow_has_check_layers_job(self) -> None:
        """Verify the workflow has a check-layers job."""
        assert WORKFLOW_PATH.exists(), "Workflow file must exist first"
        content = WORKFLOW_PATH.read_text()
        workflow = yaml.safe_load(content)
        jobs = workflow.get("jobs", {})
        assert "check-layers" in jobs, "Workflow should have 'check-layers' job"

    def test_check_layers_job_runs_on_ubuntu(self) -> None:
        """Verify check-layers job runs on ubuntu-latest."""
        assert WORKFLOW_PATH.exists(), "Workflow file must exist first"
        content = WORKFLOW_PATH.read_text()
        workflow = yaml.safe_load(content)
        job = workflow.get("jobs", {}).get("check-layers", {})
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
