"""
Test Issue #214: CI exclusion settings for acceptance tests.

These tests verify that:
1. CI workflow files exclude tests/acceptance/** from paths
2. Root pytest.ini has norecursedirs setting for tests/acceptance
3. YAML files have valid syntax
"""

import re
from pathlib import Path

import pytest
import yaml

# Paths to files under test
PROJECT_ROOT = Path(__file__).resolve().parents[3]
CI_FEATURE_YML = PROJECT_ROOT / ".github" / "workflows" / "ci-feature.yml"
CD_DEVELOP_YML = PROJECT_ROOT / ".github" / "workflows" / "cd-develop.yml"
CI_MAIN_YML = PROJECT_ROOT / ".github" / "workflows" / "ci-main.yml"
ROOT_PYTEST_INI = PROJECT_ROOT / "pytest.ini"


class TestCIWorkflowExclusion:
    """Tests for CI workflow exclusion of acceptance tests."""

    def test_ci_feature_yml_exists(self) -> None:
        """ci-feature.yml should exist."""
        assert CI_FEATURE_YML.exists(), f"File not found: {CI_FEATURE_YML}"

    def test_ci_feature_yml_valid_yaml(self) -> None:
        """ci-feature.yml should be valid YAML."""
        content = CI_FEATURE_YML.read_text()
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML in ci-feature.yml: {e}")

    def test_ci_feature_yml_excludes_acceptance_tests(self) -> None:
        """ci-feature.yml should exclude tests/acceptance/** from paths."""
        content = CI_FEATURE_YML.read_text()
        # Check for exclusion pattern in paths section
        assert (
            "!tests/acceptance/**" in content
        ), "ci-feature.yml should exclude '!tests/acceptance/**' in paths"

    def test_cd_develop_yml_exists(self) -> None:
        """cd-develop.yml should exist."""
        assert CD_DEVELOP_YML.exists(), f"File not found: {CD_DEVELOP_YML}"

    def test_cd_develop_yml_valid_yaml(self) -> None:
        """cd-develop.yml should be valid YAML."""
        content = CD_DEVELOP_YML.read_text()
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML in cd-develop.yml: {e}")

    def test_cd_develop_yml_excludes_acceptance_tests(self) -> None:
        """cd-develop.yml should exclude tests/acceptance/** from paths."""
        content = CD_DEVELOP_YML.read_text()
        # Check for exclusion pattern in paths section
        assert (
            "!tests/acceptance/**" in content
        ), "cd-develop.yml should exclude '!tests/acceptance/**' in paths"

    def test_ci_main_yml_exists(self) -> None:
        """ci-main.yml should exist."""
        assert CI_MAIN_YML.exists(), f"File not found: {CI_MAIN_YML}"

    def test_ci_main_yml_valid_yaml(self) -> None:
        """ci-main.yml should be valid YAML."""
        content = CI_MAIN_YML.read_text()
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML in ci-main.yml: {e}")

    def test_ci_main_yml_excludes_acceptance_tests(self) -> None:
        """ci-main.yml should exclude tests/acceptance/** from paths."""
        content = CI_MAIN_YML.read_text()
        # Check for exclusion pattern in paths section
        assert (
            "!tests/acceptance/**" in content
        ), "ci-main.yml should exclude '!tests/acceptance/**' in paths"


class TestPytestIniConfiguration:
    """Tests for pytest.ini norecursedirs configuration."""

    def test_root_pytest_ini_exists(self) -> None:
        """Root pytest.ini should exist."""
        assert ROOT_PYTEST_INI.exists(), f"File not found: {ROOT_PYTEST_INI}"

    def test_root_pytest_ini_has_norecursedirs(self) -> None:
        """Root pytest.ini should have norecursedirs setting."""
        content = ROOT_PYTEST_INI.read_text()
        assert "norecursedirs" in content, "pytest.ini should have norecursedirs setting"

    def test_root_pytest_ini_excludes_acceptance_directory(self) -> None:
        """Root pytest.ini norecursedirs should include tests/acceptance."""
        content = ROOT_PYTEST_INI.read_text()
        # norecursedirs should contain tests/acceptance
        # Need to handle multiline norecursedirs setting
        # First extract the norecursedirs block
        if "norecursedirs" in content:
            # Find lines after norecursedirs
            lines = content.split("\n")
            in_norecursedirs = False
            norecursedirs_content = []
            for line in lines:
                if "norecursedirs" in line:
                    in_norecursedirs = True
                    norecursedirs_content.append(line)
                elif in_norecursedirs:
                    # Continue until we hit a line that starts a new setting
                    if re.match(r"^[a-zA-Z]", line) and "=" in line:
                        break
                    norecursedirs_content.append(line)

            norecursedirs_block = "\n".join(norecursedirs_content)
            assert (
                "tests/acceptance" in norecursedirs_block
            ), f"norecursedirs should include 'tests/acceptance'. Found: {norecursedirs_block}"
        else:
            pytest.fail("norecursedirs setting not found in pytest.ini")


class TestAcceptanceTestDirectory:
    """Tests to verify acceptance test directory structure."""

    def test_acceptance_test_directory_exists(self) -> None:
        """tests/acceptance directory should exist."""
        acceptance_dir = PROJECT_ROOT / "tests" / "acceptance"
        assert acceptance_dir.exists(), f"Directory not found: {acceptance_dir}"

    def test_acceptance_test_directory_has_python_tests(self) -> None:
        """tests/acceptance should have Python test directory."""
        python_acceptance_dir = PROJECT_ROOT / "tests" / "acceptance" / "python"
        assert python_acceptance_dir.exists(), f"Directory not found: {python_acceptance_dir}"
