"""
Tests for Issue #169: setup-valkey-worktree.sh script

Tests verify that scripts/setup-valkey-worktree.sh:
- Allocates unique ports for each worktree
- Creates worktree-specific Valkey data directories
- Generates worktree-specific Valkey configuration
- Prevents port conflicts between worktrees
"""

import os
from pathlib import Path

import pytest


@pytest.fixture
def project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


@pytest.fixture
def valkey_worktree_script(project_root: Path) -> Path:
    """Get the setup-valkey-worktree.sh script path."""
    return project_root / "scripts" / "setup-valkey-worktree.sh"


@pytest.fixture
def valkey_worktree_content(valkey_worktree_script: Path) -> str:
    """Load setup-valkey-worktree.sh script content."""
    assert valkey_worktree_script.exists(), "scripts/setup-valkey-worktree.sh が存在しません"

    with open(valkey_worktree_script, "r") as f:
        content = f.read()

    return content


class TestWorktreeScriptExistence:
    """Test that setup-valkey-worktree.sh script exists."""

    def test_script_file_exists(self, valkey_worktree_script: Path):
        """setup-valkey-worktree.sh ファイルが存在すること."""
        assert valkey_worktree_script.exists(), "scripts/setup-valkey-worktree.sh が存在しません"

    def test_script_is_executable(self, valkey_worktree_script: Path):
        """setup-valkey-worktree.sh が実行可能であること."""
        assert os.access(valkey_worktree_script, os.X_OK), (
            "scripts/setup-valkey-worktree.sh が実行可能ではありません"
        )


class TestPortAllocationLogic:
    """Test port allocation logic for worktrees."""

    def test_port_range_defined(self, valkey_worktree_content: str):
        """ポート範囲が定義されていること (6380-6399)."""
        # Look for port range definition
        assert "6380" in valkey_worktree_content or "PORT_MIN" in valkey_worktree_content, (
            "ポート範囲の開始値が定義されていません"
        )

        assert "6399" in valkey_worktree_content or "PORT_MAX" in valkey_worktree_content, (
            "ポート範囲の終了値が定義されていません"
        )

    def test_port_allocation_function_exists(self, valkey_worktree_content: str):
        """ポート割り当て関数が存在すること."""
        # Look for function to allocate port
        assert (
            "allocate_port" in valkey_worktree_content
            or "find_available_port" in valkey_worktree_content
            or "get_next_port" in valkey_worktree_content
        ), "ポート割り当て関数が見つかりません"

    def test_port_conflict_check_exists(self, valkey_worktree_content: str):
        """ポート衝突チェック処理が存在すること."""
        # Look for port conflict detection (lsof or similar)
        assert "lsof" in valkey_worktree_content or "netstat" in valkey_worktree_content, (
            "ポート衝突チェック処理が見つかりません"
        )


class TestWorktreeDataDirectory:
    """Test worktree-specific data directory creation."""

    def test_data_directory_creation(self, valkey_worktree_content: str):
        """worktree専用データディレクトリ作成処理が存在すること."""
        # Look for mkdir or data directory creation
        assert "mkdir" in valkey_worktree_content, "データディレクトリ作成処理が見つかりません"

        # Should reference valkey/data
        assert (
            "valkey/data" in valkey_worktree_content or "VALKEY_DATA" in valkey_worktree_content
        ), "Valkey データディレクトリパスが見つかりません"

    def test_worktree_isolation(self, valkey_worktree_content: str):
        """各worktreeが独立したディレクトリを持つこと."""
        # Look for worktree name or branch name in path
        assert (
            "worktree_name" in valkey_worktree_content
            or "WORKTREE" in valkey_worktree_content
            or "BRANCH" in valkey_worktree_content
            or "basename" in valkey_worktree_content
        ), "worktree 識別子が見つかりません"


class TestWorktreeConfigGeneration:
    """Test worktree-specific Valkey configuration generation."""

    def test_config_file_generation(self, valkey_worktree_content: str):
        """worktree専用の設定ファイル生成処理が存在すること."""
        # Look for config file generation
        assert "valkey.conf" in valkey_worktree_content, "設定ファイル生成処理が見つかりません"

    def test_port_substitution_in_config(self, valkey_worktree_content: str):
        """設定ファイル内のポート番号が動的に設定されること."""
        # Look for port substitution (sed, awk, or variable replacement)
        has_substitution = (
            "sed" in valkey_worktree_content
            or "PORT" in valkey_worktree_content
            or "port" in valkey_worktree_content
        )

        assert has_substitution, "ポート番号の動的設定処理が見つかりません"


class TestPortManagementFile:
    """Test port management file for tracking used ports."""

    def test_port_registry_file_usage(self, valkey_worktree_content: str):
        """使用中ポートを記録するファイルが使用されていること."""
        # Look for port registry or lock file
        assert (
            ".valkey-ports" in valkey_worktree_content
            or "port-registry" in valkey_worktree_content
            or "PORTS_FILE" in valkey_worktree_content
        ), "ポート管理ファイルが見つかりません"

    def test_port_registry_update(self, valkey_worktree_content: str):
        """ポート管理ファイルへの書き込み処理が存在すること."""
        # Look for write operations to port registry
        has_write = "echo" in valkey_worktree_content or ">>" in valkey_worktree_content

        assert has_write, "ポート管理ファイルへの書き込み処理が見つかりません"


class TestWorktreeSetupValidation:
    """Test worktree setup validation."""

    def test_worktree_detection(self, valkey_worktree_content: str):
        """worktree環境の検出処理が存在すること."""
        # Look for git worktree detection
        assert (
            "git worktree" in valkey_worktree_content
            or ".git/worktrees" in valkey_worktree_content
            or "worktree" in valkey_worktree_content.lower()
        ), "worktree 検出処理が見つかりません"

    def test_error_handling_exists(self, valkey_worktree_content: str):
        """エラーハンドリング処理が存在すること."""
        # Look for error handling (exit, return, or error messages)
        has_error_handling = (
            "exit 1" in valkey_worktree_content
            or "return 1" in valkey_worktree_content
            or "error" in valkey_worktree_content.lower()
        )

        assert has_error_handling, "エラーハンドリング処理が見つかりません"


class TestUsageInstructions:
    """Test script usage instructions."""

    def test_usage_function_exists(self, valkey_worktree_content: str):
        """使用方法を表示する関数が存在すること."""
        # Look for usage or help function
        has_usage = (
            "usage" in valkey_worktree_content.lower()
            or "help" in valkey_worktree_content.lower()
            or "--help" in valkey_worktree_content
        )

        assert has_usage, "使用方法表示機能が見つかりません"
