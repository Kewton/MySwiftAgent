"""Issue #213: Acceptance test directory structure verification tests.

This module contains tests that verify the acceptance test directory structure
is correctly created according to the design-policy.md specification.

Structure requirements:
- tests/acceptance/python/ with platform/, agent/, e2e/ subdirectories
- tests/acceptance/typescript/ with ui/, e2e/ subdirectories
- tests/fixtures/ with api_responses/, test_data/, factories/
- conftest.py hierarchy: L0 -> L1 -> L2
"""

from pathlib import Path

import pytest


@pytest.fixture
def tests_root(project_root: Path) -> Path:
    """Get the tests root directory.

    This is a module-level fixture to avoid duplication across test classes.
    Following DRY principle - defined once and reused.

    Args:
        project_root: The project root path from L0 conftest.

    Returns:
        Path: The absolute path to the tests directory.
    """
    return project_root / "tests"


class TestAcceptanceDirectoryStructure:
    """Test acceptance test directory structure existence."""

    def test_acceptance_python_directory_exists(self, tests_root: Path) -> None:
        """Verify tests/acceptance/python/ directory exists."""
        acceptance_python = tests_root / "acceptance" / "python"
        assert acceptance_python.exists(), f"Directory not found: {acceptance_python}"
        assert acceptance_python.is_dir(), f"Not a directory: {acceptance_python}"

    def test_acceptance_python_platform_directory_exists(self, tests_root: Path) -> None:
        """Verify tests/acceptance/python/platform/ directory exists."""
        platform_dir = tests_root / "acceptance" / "python" / "platform"
        assert platform_dir.exists(), f"Directory not found: {platform_dir}"
        assert platform_dir.is_dir(), f"Not a directory: {platform_dir}"

    def test_acceptance_python_agent_directory_exists(self, tests_root: Path) -> None:
        """Verify tests/acceptance/python/agent/ directory exists."""
        agent_dir = tests_root / "acceptance" / "python" / "agent"
        assert agent_dir.exists(), f"Directory not found: {agent_dir}"
        assert agent_dir.is_dir(), f"Not a directory: {agent_dir}"

    def test_acceptance_python_e2e_directory_exists(self, tests_root: Path) -> None:
        """Verify tests/acceptance/python/e2e/ directory exists."""
        e2e_dir = tests_root / "acceptance" / "python" / "e2e"
        assert e2e_dir.exists(), f"Directory not found: {e2e_dir}"
        assert e2e_dir.is_dir(), f"Not a directory: {e2e_dir}"

    def test_acceptance_python_e2e_scenarios_directory_exists(self, tests_root: Path) -> None:
        """Verify tests/acceptance/python/e2e/scenarios/ directory exists."""
        scenarios_dir = tests_root / "acceptance" / "python" / "e2e" / "scenarios"
        assert scenarios_dir.exists(), f"Directory not found: {scenarios_dir}"
        assert scenarios_dir.is_dir(), f"Not a directory: {scenarios_dir}"

    def test_acceptance_typescript_directory_exists(self, tests_root: Path) -> None:
        """Verify tests/acceptance/typescript/ directory exists."""
        acceptance_ts = tests_root / "acceptance" / "typescript"
        assert acceptance_ts.exists(), f"Directory not found: {acceptance_ts}"
        assert acceptance_ts.is_dir(), f"Not a directory: {acceptance_ts}"

    def test_acceptance_typescript_ui_directory_exists(self, tests_root: Path) -> None:
        """Verify tests/acceptance/typescript/ui/ directory exists."""
        ui_dir = tests_root / "acceptance" / "typescript" / "ui"
        assert ui_dir.exists(), f"Directory not found: {ui_dir}"
        assert ui_dir.is_dir(), f"Not a directory: {ui_dir}"

    def test_acceptance_typescript_e2e_directory_exists(self, tests_root: Path) -> None:
        """Verify tests/acceptance/typescript/e2e/ directory exists."""
        e2e_dir = tests_root / "acceptance" / "typescript" / "e2e"
        assert e2e_dir.exists(), f"Directory not found: {e2e_dir}"
        assert e2e_dir.is_dir(), f"Not a directory: {e2e_dir}"


class TestFixturesDirectoryStructure:
    """Test fixtures directory structure existence."""

    def test_fixtures_directory_exists(self, tests_root: Path) -> None:
        """Verify tests/fixtures/ directory exists."""
        fixtures_dir = tests_root / "fixtures"
        assert fixtures_dir.exists(), f"Directory not found: {fixtures_dir}"
        assert fixtures_dir.is_dir(), f"Not a directory: {fixtures_dir}"

    def test_fixtures_api_responses_directory_exists(self, tests_root: Path) -> None:
        """Verify tests/fixtures/api_responses/ directory exists."""
        api_responses_dir = tests_root / "fixtures" / "api_responses"
        assert api_responses_dir.exists(), f"Directory not found: {api_responses_dir}"
        assert api_responses_dir.is_dir(), f"Not a directory: {api_responses_dir}"

    def test_fixtures_api_responses_myvault_directory_exists(self, tests_root: Path) -> None:
        """Verify tests/fixtures/api_responses/myvault/ directory exists."""
        myvault_dir = tests_root / "fixtures" / "api_responses" / "myvault"
        assert myvault_dir.exists(), f"Directory not found: {myvault_dir}"
        assert myvault_dir.is_dir(), f"Not a directory: {myvault_dir}"

    def test_fixtures_api_responses_expertagent_directory_exists(self, tests_root: Path) -> None:
        """Verify tests/fixtures/api_responses/expertagent/ directory exists."""
        expertagent_dir = tests_root / "fixtures" / "api_responses" / "expertagent"
        assert expertagent_dir.exists(), f"Directory not found: {expertagent_dir}"
        assert expertagent_dir.is_dir(), f"Not a directory: {expertagent_dir}"

    def test_fixtures_test_data_directory_exists(self, tests_root: Path) -> None:
        """Verify tests/fixtures/test_data/ directory exists."""
        test_data_dir = tests_root / "fixtures" / "test_data"
        assert test_data_dir.exists(), f"Directory not found: {test_data_dir}"
        assert test_data_dir.is_dir(), f"Not a directory: {test_data_dir}"

    def test_fixtures_test_data_job_requests_directory_exists(self, tests_root: Path) -> None:
        """Verify tests/fixtures/test_data/job_requests/ directory exists."""
        job_requests_dir = tests_root / "fixtures" / "test_data" / "job_requests"
        assert job_requests_dir.exists(), f"Directory not found: {job_requests_dir}"
        assert job_requests_dir.is_dir(), f"Not a directory: {job_requests_dir}"

    def test_fixtures_test_data_workflows_directory_exists(self, tests_root: Path) -> None:
        """Verify tests/fixtures/test_data/workflows/ directory exists."""
        workflows_dir = tests_root / "fixtures" / "test_data" / "workflows"
        assert workflows_dir.exists(), f"Directory not found: {workflows_dir}"
        assert workflows_dir.is_dir(), f"Not a directory: {workflows_dir}"

    def test_fixtures_factories_directory_exists(self, tests_root: Path) -> None:
        """Verify tests/fixtures/factories/ directory exists."""
        factories_dir = tests_root / "fixtures" / "factories"
        assert factories_dir.exists(), f"Directory not found: {factories_dir}"
        assert factories_dir.is_dir(), f"Not a directory: {factories_dir}"


class TestConftestPyFiles:
    """Test conftest.py file existence at all levels."""

    def test_l0_conftest_exists(self, tests_root: Path) -> None:
        """Verify L0 conftest.py exists at tests/conftest.py."""
        conftest = tests_root / "conftest.py"
        assert conftest.exists(), f"L0 conftest.py not found: {conftest}"
        assert conftest.is_file(), f"Not a file: {conftest}"

    def test_l1_acceptance_python_conftest_exists(self, tests_root: Path) -> None:
        """Verify L1 conftest.py exists at tests/acceptance/python/conftest.py."""
        conftest = tests_root / "acceptance" / "python" / "conftest.py"
        assert conftest.exists(), f"L1 conftest.py not found: {conftest}"
        assert conftest.is_file(), f"Not a file: {conftest}"

    def test_l2_platform_conftest_exists(self, tests_root: Path) -> None:
        """Verify L2 conftest.py exists at tests/acceptance/python/platform/conftest.py."""
        conftest = tests_root / "acceptance" / "python" / "platform" / "conftest.py"
        assert conftest.exists(), f"L2 platform conftest.py not found: {conftest}"
        assert conftest.is_file(), f"Not a file: {conftest}"

    def test_l2_agent_conftest_exists(self, tests_root: Path) -> None:
        """Verify L2 conftest.py exists at tests/acceptance/python/agent/conftest.py."""
        conftest = tests_root / "acceptance" / "python" / "agent" / "conftest.py"
        assert conftest.exists(), f"L2 agent conftest.py not found: {conftest}"
        assert conftest.is_file(), f"Not a file: {conftest}"

    def test_l2_e2e_conftest_exists(self, tests_root: Path) -> None:
        """Verify L2 conftest.py exists at tests/acceptance/python/e2e/conftest.py."""
        conftest = tests_root / "acceptance" / "python" / "e2e" / "conftest.py"
        assert conftest.exists(), f"L2 e2e conftest.py not found: {conftest}"
        assert conftest.is_file(), f"Not a file: {conftest}"


class TestConftestMarkers:
    """Test that conftest.py contains required markers."""

    def test_l0_conftest_has_platform_marker(self, tests_root: Path) -> None:
        """Verify L0 conftest.py defines 'platform' marker."""
        conftest = tests_root / "conftest.py"
        content = conftest.read_text()
        assert "platform" in content, "L0 conftest.py missing 'platform' marker"

    def test_l0_conftest_has_agent_marker(self, tests_root: Path) -> None:
        """Verify L0 conftest.py defines 'agent' marker."""
        conftest = tests_root / "conftest.py"
        content = conftest.read_text()
        assert "agent" in content, "L0 conftest.py missing 'agent' marker"

    def test_l0_conftest_has_frontend_marker(self, tests_root: Path) -> None:
        """Verify L0 conftest.py defines 'frontend' marker."""
        conftest = tests_root / "conftest.py"
        content = conftest.read_text()
        assert "frontend" in content, "L0 conftest.py missing 'frontend' marker"

    def test_l0_conftest_has_requires_api_key_marker(self, tests_root: Path) -> None:
        """Verify L0 conftest.py defines 'requires_api_key' marker."""
        conftest = tests_root / "conftest.py"
        content = conftest.read_text()
        assert "requires_api_key" in content, "L0 conftest.py missing 'requires_api_key' marker"

    def test_l0_conftest_has_acceptance_marker(self, tests_root: Path) -> None:
        """Verify L0 conftest.py defines 'acceptance' marker."""
        conftest = tests_root / "conftest.py"
        content = conftest.read_text()
        assert "acceptance" in content, "L0 conftest.py missing 'acceptance' marker"


class TestConfigurationFiles:
    """Test configuration file existence."""

    def test_acceptance_python_pytest_ini_exists(self, tests_root: Path) -> None:
        """Verify tests/acceptance/python/pytest.ini exists."""
        pytest_ini = tests_root / "acceptance" / "python" / "pytest.ini"
        assert pytest_ini.exists(), f"pytest.ini not found: {pytest_ini}"
        assert pytest_ini.is_file(), f"Not a file: {pytest_ini}"

    def test_acceptance_python_requirements_txt_exists(self, tests_root: Path) -> None:
        """Verify tests/acceptance/python/requirements.txt exists."""
        requirements = tests_root / "acceptance" / "python" / "requirements.txt"
        assert requirements.exists(), f"requirements.txt not found: {requirements}"
        assert requirements.is_file(), f"Not a file: {requirements}"

    def test_acceptance_typescript_playwright_config_exists(self, tests_root: Path) -> None:
        """Verify tests/acceptance/typescript/playwright.config.ts exists."""
        playwright_config = tests_root / "acceptance" / "typescript" / "playwright.config.ts"
        assert playwright_config.exists(), f"playwright.config.ts not found: {playwright_config}"
        assert playwright_config.is_file(), f"Not a file: {playwright_config}"

    def test_acceptance_typescript_package_json_exists(self, tests_root: Path) -> None:
        """Verify tests/acceptance/typescript/package.json exists."""
        package_json = tests_root / "acceptance" / "typescript" / "package.json"
        assert package_json.exists(), f"package.json not found: {package_json}"
        assert package_json.is_file(), f"Not a file: {package_json}"

    def test_acceptance_typescript_tsconfig_json_exists(self, tests_root: Path) -> None:
        """Verify tests/acceptance/typescript/tsconfig.json exists."""
        tsconfig = tests_root / "acceptance" / "typescript" / "tsconfig.json"
        assert tsconfig.exists(), f"tsconfig.json not found: {tsconfig}"
        assert tsconfig.is_file(), f"Not a file: {tsconfig}"


class TestDocumentationFiles:
    """Test documentation file existence."""

    def test_readme_md_exists(self, tests_root: Path) -> None:
        """Verify tests/README.md exists."""
        readme = tests_root / "README.md"
        assert readme.exists(), f"README.md not found: {readme}"
        assert readme.is_file(), f"Not a file: {readme}"

    def test_readme_contains_quick_reference(self, tests_root: Path) -> None:
        """Verify tests/README.md contains test location quick reference."""
        readme = tests_root / "README.md"
        content = readme.read_text()
        assert "quick" in content.lower() or "reference" in content.lower(), (
            "README.md missing quick reference section"
        )

    def test_env_example_exists(self, tests_root: Path) -> None:
        """Verify tests/.env.example exists."""
        env_example = tests_root / ".env.example"
        assert env_example.exists(), f".env.example not found: {env_example}"
        assert env_example.is_file(), f"Not a file: {env_example}"

    def test_env_example_documents_required_variables(self, tests_root: Path) -> None:
        """Verify tests/.env.example documents required environment variables."""
        env_example = tests_root / ".env.example"
        content = env_example.read_text()
        # Check for essential environment variable documentation
        assert "GOOGLE_API_KEY" in content or "API_KEY" in content, (
            ".env.example missing API key documentation"
        )


class TestInitFiles:
    """Test __init__.py file existence."""

    def test_fixtures_init_py_exists(self, tests_root: Path) -> None:
        """Verify tests/fixtures/__init__.py exists."""
        init_file = tests_root / "fixtures" / "__init__.py"
        assert init_file.exists(), f"__init__.py not found: {init_file}"
        assert init_file.is_file(), f"Not a file: {init_file}"

    def test_fixtures_factories_init_py_exists(self, tests_root: Path) -> None:
        """Verify tests/fixtures/factories/__init__.py exists."""
        init_file = tests_root / "fixtures" / "factories" / "__init__.py"
        assert init_file.exists(), f"__init__.py not found: {init_file}"
        assert init_file.is_file(), f"Not a file: {init_file}"
