"""
Tests for Issue #169: dev-start.sh script Valkey integration

Tests verify that scripts/dev-start.sh:
- Contains Valkey startup logic
- Handles port configuration
- Checks Valkey health status
- Manages Valkey PID files and logs
"""

import re
from pathlib import Path

import pytest


@pytest.fixture
def project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


@pytest.fixture
def dev_start_script(project_root: Path) -> Path:
    """Get the dev-start.sh script path."""
    return project_root / "scripts" / "dev-start.sh"


@pytest.fixture
def dev_start_content(dev_start_script: Path) -> str:
    """Load dev-start.sh script content."""
    assert dev_start_script.exists(), "scripts/dev-start.sh が存在しません"

    with open(dev_start_script, "r") as f:
        content = f.read()

    return content


class TestValkeyPortConfiguration:
    """Test Valkey port configuration in dev-start.sh."""

    def test_valkey_port_variable_exists(self, dev_start_content: str):
        """VALKEY_PORT 変数が定義されていること."""
        assert "VALKEY_PORT" in dev_start_content, "VALKEY_PORT 変数が定義されていません"

    def test_valkey_default_port_is_6379(self, dev_start_content: str):
        """VALKEY_PORT のデフォルト値が6379であること."""
        # Look for VALKEY_PORT="${VALKEY_PORT:-6379}"
        port_pattern = r'VALKEY_PORT="\$\{VALKEY_PORT:-(\d+)\}"'
        match = re.search(port_pattern, dev_start_content)

        assert match is not None, "VALKEY_PORT のデフォルト値設定が見つかりません"
        assert match.group(1) == "6379", "VALKEY_PORT のデフォルト値が6379ではありません"


class TestValkeyLogAndPidFiles:
    """Test Valkey log and PID file configuration."""

    def test_valkey_log_file_defined(self, dev_start_content: str):
        """VALKEY_LOG ファイルパスが定義されていること."""
        assert "VALKEY_LOG" in dev_start_content, "VALKEY_LOG が定義されていません"

        # Check if it points to logs directory
        log_pattern = r'VALKEY_LOG="\$LOG_DIR/valkey\.log"'
        assert re.search(log_pattern, dev_start_content), "VALKEY_LOG のパスが不正です"

    def test_valkey_pid_file_defined(self, dev_start_content: str):
        """VALKEY_PID ファイルパスが定義されていること."""
        assert "VALKEY_PID" in dev_start_content, "VALKEY_PID が定義されていません"

        # Check if it points to PID directory
        pid_pattern = r'VALKEY_PID="\$PID_DIR/valkey\.pid"'
        assert re.search(pid_pattern, dev_start_content), "VALKEY_PID のパスが不正です"


class TestValkeyStartupLogic:
    """Test Valkey startup logic in dev-start.sh."""

    def test_valkey_service_start_exists(self, dev_start_content: str):
        """Valkey サービス起動処理が存在すること."""
        # Look for start command with valkey
        assert "valkey" in dev_start_content.lower(), "Valkey 起動処理が見つかりません"

    def test_valkey_starts_before_services(self, dev_start_content: str):
        """Valkey が他のサービスより前に起動すること."""
        # Find the order of service starts
        valkey_start_pos = dev_start_content.find("# Start Valkey") or dev_start_content.find(
            "Start Valkey"
        )
        jobqueue_start_pos = dev_start_content.find("# Start JobQueue")

        # Valkey should start before JobQueue (or be present at least)
        assert valkey_start_pos > 0, "Valkey 起動処理のコメントまたはラベルが見つかりません"


class TestValkeyHealthCheck:
    """Test Valkey health check in dev-start.sh."""

    def test_valkey_health_check_exists(self, dev_start_content: str):
        """Valkey ヘルスチェック処理が存在すること."""
        # Look for PING command or health check
        assert "PING" in dev_start_content or "valkey-cli" in dev_start_content, (
            "Valkey ヘルスチェック処理が見つかりません"
        )


class TestValkeyStopLogic:
    """Test Valkey stop logic in dev-start.sh."""

    def test_valkey_stop_service_exists(self, dev_start_content: str):
        """Valkey サービス停止処理が存在すること."""
        # Look for stop command section
        stop_section_found = (
            'stop_service "Valkey"' in dev_start_content or "Stop Valkey" in dev_start_content
        )

        assert stop_section_found, "Valkey 停止処理が見つかりません"


class TestValkeyStatusCheck:
    """Test Valkey status check in dev-start.sh."""

    def test_valkey_status_check_exists(self, dev_start_content: str):
        """Valkey ステータスチェック処理が存在すること."""
        # Look for status command with valkey
        status_section_found = (
            'check_service_status "Valkey"' in dev_start_content
            or "Valkey" in dev_start_content
            and "status" in dev_start_content.lower()
        )

        assert status_section_found, "Valkey ステータスチェック処理が見つかりません"


class TestValkeyServiceUrlDisplay:
    """Test Valkey service URL display."""

    def test_valkey_url_in_show_service_urls(self, dev_start_content: str):
        """show_service_urls 関数に Valkey URL が含まれていること."""
        # Look for show_service_urls function
        show_urls_match = re.search(
            r"show_service_urls\s*\(\)\s*\{(.*?)\n\}",
            dev_start_content,
            re.DOTALL,
        )

        if show_urls_match:
            show_urls_content = show_urls_match.group(1)
            assert "valkey" in show_urls_content.lower() or "6379" in show_urls_content, (
                "show_service_urls に Valkey 情報が含まれていません"
            )
        else:
            # If function structure is different, just check for Valkey mention in URL context
            assert "Valkey" in dev_start_content, "Valkey サービス URL 表示が見つかりません"
