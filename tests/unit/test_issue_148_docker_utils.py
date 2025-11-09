"""
Unit tests for Issue #148: Docker Compose Integration

Tests for scripts/lib/docker-utils.sh functionality.
"""

import subprocess
import pytest
from pathlib import Path


@pytest.fixture
def project_root():
    """Get project root directory."""
    return Path(__file__).parent.parent.parent


@pytest.fixture
def docker_utils_script(project_root):
    """Get path to docker-utils.sh script."""
    script_path = project_root / "scripts" / "lib" / "docker-utils.sh"
    return script_path


class TestDockerUtilsScriptExists:
    """Test that docker-utils.sh script exists."""

    def test_docker_utils_script_exists(self, docker_utils_script):
        """受入条件: docker-utils.shスクリプトが存在すること."""
        assert docker_utils_script.exists(), f"Script not found: {docker_utils_script}"

    def test_docker_utils_script_is_executable(self, docker_utils_script):
        """docker-utils.shスクリプトが実行可能であること."""
        assert docker_utils_script.exists(), f"Script not found: {docker_utils_script}"
        # Check if file has execute permission
        import os
        assert os.access(docker_utils_script, os.X_OK), "Script is not executable"


class TestDockerDesktopCheck:
    """Test Docker Desktop availability check."""

    def test_check_docker_available_function_exists(self, docker_utils_script):
        """check_docker_available関数が定義されていること."""
        # Given: docker-utils.sh script exists
        assert docker_utils_script.exists()

        # When: Sourcing the script and checking for function
        result = subprocess.run(
            f"bash -c 'source {docker_utils_script} && declare -F check_docker_available'",
            shell=True,
            capture_output=True,
            text=True,
        )

        # Then: Function should be defined
        assert result.returncode == 0, f"Function not defined: {result.stderr}"
        assert "check_docker_available" in result.stdout


class TestDockerComposeOperations:
    """Test Docker Compose start/stop operations."""

    def test_start_docker_compose_function_exists(self, docker_utils_script):
        """start_docker_compose関数が定義されていること."""
        assert docker_utils_script.exists()

        result = subprocess.run(
            f"bash -c 'source {docker_utils_script} && declare -F start_docker_compose'",
            shell=True,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Function not defined: {result.stderr}"
        assert "start_docker_compose" in result.stdout

    def test_stop_docker_compose_function_exists(self, docker_utils_script):
        """stop_docker_compose関数が定義されていること."""
        assert docker_utils_script.exists()

        result = subprocess.run(
            f"bash -c 'source {docker_utils_script} && declare -F stop_docker_compose'",
            shell=True,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Function not defined: {result.stderr}"
        assert "stop_docker_compose" in result.stdout


class TestDockerHealthCheck:
    """Test Docker container health check integration."""

    def test_check_docker_service_health_function_exists(self, docker_utils_script):
        """check_docker_service_health関数が定義されていること."""
        assert docker_utils_script.exists()

        result = subprocess.run(
            f"bash -c 'source {docker_utils_script} && declare -F check_docker_service_health'",
            shell=True,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Function not defined: {result.stderr}"
        assert "check_docker_service_health" in result.stdout


class TestWorktreeIsolation:
    """Test worktree-specific Docker environment isolation."""

    def test_get_worktree_project_name_function_exists(self, docker_utils_script):
        """get_worktree_project_name関数が定義されていること."""
        assert docker_utils_script.exists()

        result = subprocess.run(
            f"bash -c 'source {docker_utils_script} && declare -F get_worktree_project_name'",
            shell=True,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Function not defined: {result.stderr}"
        assert "get_worktree_project_name" in result.stdout
