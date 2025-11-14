"""
Tests for Issue #169: Docker Compose Valkey service configuration

Tests verify that docker-compose.yml correctly defines Valkey service with:
- Proper image specification
- Port mapping
- Volume mounts for data persistence
- Health check configuration
- Network configuration
"""

import os
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


@pytest.fixture
def docker_compose_file(project_root: Path) -> Path:
    """Get the docker-compose.yml file path."""
    return project_root / "docker-compose.yml"


@pytest.fixture
def docker_compose_config(docker_compose_file: Path) -> dict:
    """Load and parse docker-compose.yml."""
    assert docker_compose_file.exists(), "docker-compose.yml が存在しません"

    with open(docker_compose_file, "r") as f:
        config = yaml.safe_load(f)

    return config


class TestValkeyServiceDefinition:
    """Test Valkey service definition in docker-compose.yml."""

    def test_valkey_service_exists(self, docker_compose_config: dict):
        """Valkey service が定義されていること."""
        assert "services" in docker_compose_config, "services が定義されていません"
        assert (
            "valkey" in docker_compose_config["services"]
        ), "valkey service が定義されていません"

    def test_valkey_image_specification(self, docker_compose_config: dict):
        """Valkey イメージが正しく指定されていること."""
        valkey_service = docker_compose_config["services"]["valkey"]
        assert "image" in valkey_service, "Valkey image が指定されていません"
        assert "valkey/valkey" in valkey_service["image"], "Valkey イメージが不正です"

    def test_valkey_container_name(self, docker_compose_config: dict):
        """Valkey コンテナ名が設定されていること."""
        valkey_service = docker_compose_config["services"]["valkey"]
        assert (
            "container_name" in valkey_service
        ), "Valkey container_name が設定されていません"
        assert valkey_service["container_name"] == "myswiftagent-valkey"


class TestValkeyPortConfiguration:
    """Test Valkey port configuration."""

    def test_valkey_port_mapping(self, docker_compose_config: dict):
        """Valkey ポートマッピングが設定されていること."""
        valkey_service = docker_compose_config["services"]["valkey"]
        assert "ports" in valkey_service, "Valkey ports が設定されていません"
        assert len(valkey_service["ports"]) > 0, "Valkey ポートマッピングがありません"

    def test_valkey_default_port(self, docker_compose_config: dict):
        """Valkey がデフォルトポート6379でマッピングされていること."""
        valkey_service = docker_compose_config["services"]["valkey"]
        ports = valkey_service["ports"]

        # Format can be "6379:6379" or similar
        port_found = False
        for port_mapping in ports:
            if "6379" in str(port_mapping):
                port_found = True
                break

        assert port_found, "Valkey デフォルトポート6379がマッピングされていません"


class TestValkeyVolumeConfiguration:
    """Test Valkey volume configuration for data persistence."""

    def test_valkey_volume_mount(self, docker_compose_config: dict):
        """Valkey データボリュームがマウントされていること."""
        valkey_service = docker_compose_config["services"]["valkey"]
        assert "volumes" in valkey_service, "Valkey volumes が設定されていません"
        assert len(valkey_service["volumes"]) > 0, "Valkey ボリュームマウントがありません"

    def test_valkey_data_volume_path(self, docker_compose_config: dict):
        """Valkey データボリュームが /data にマウントされていること."""
        valkey_service = docker_compose_config["services"]["valkey"]
        volumes = valkey_service["volumes"]

        # Check if any volume maps to /data
        data_volume_found = False
        for volume in volumes:
            if isinstance(volume, str) and ":/data" in volume:
                data_volume_found = True
                # Verify it uses valkey directory
                assert (
                    "./valkey/data" in volume or "valkey-data" in volume
                ), "Valkey データディレクトリパスが不正です"
                break

        assert data_volume_found, "Valkey /data ボリュームがマウントされていません"

    def test_valkey_config_volume_mount(self, docker_compose_config: dict):
        """Valkey 設定ファイルがマウントされていること."""
        valkey_service = docker_compose_config["services"]["valkey"]
        volumes = valkey_service["volumes"]

        # Check if config file is mounted
        config_volume_found = False
        for volume in volumes:
            if isinstance(volume, str) and (
                "valkey.conf" in volume or "/usr/local/etc/valkey" in volume
            ):
                config_volume_found = True
                break

        assert (
            config_volume_found
        ), "Valkey 設定ファイルボリュームがマウントされていません"


class TestValkeyHealthCheck:
    """Test Valkey health check configuration."""

    def test_valkey_healthcheck_exists(self, docker_compose_config: dict):
        """Valkey ヘルスチェックが定義されていること."""
        valkey_service = docker_compose_config["services"]["valkey"]
        assert (
            "healthcheck" in valkey_service
        ), "Valkey healthcheck が定義されていません"

    def test_valkey_healthcheck_test(self, docker_compose_config: dict):
        """Valkey ヘルスチェックコマンドが正しく設定されていること."""
        valkey_service = docker_compose_config["services"]["valkey"]
        healthcheck = valkey_service["healthcheck"]

        assert "test" in healthcheck, "Valkey healthcheck test が設定されていません"

        test_cmd = healthcheck["test"]
        # Should use valkey-cli PING
        assert any(
            "valkey-cli" in str(cmd) or "PING" in str(cmd) for cmd in test_cmd
        ), "Valkey ヘルスチェックコマンドが不正です"

    def test_valkey_healthcheck_interval(self, docker_compose_config: dict):
        """Valkey ヘルスチェック間隔が設定されていること."""
        valkey_service = docker_compose_config["services"]["valkey"]
        healthcheck = valkey_service["healthcheck"]

        assert (
            "interval" in healthcheck
        ), "Valkey healthcheck interval が設定されていません"


class TestValkeyNetworkConfiguration:
    """Test Valkey network configuration."""

    def test_valkey_network_exists(self, docker_compose_config: dict):
        """Valkey が myswiftagent ネットワークに接続されていること."""
        valkey_service = docker_compose_config["services"]["valkey"]
        assert "networks" in valkey_service, "Valkey networks が設定されていません"
        assert (
            "myswiftagent" in valkey_service["networks"]
        ), "Valkey が myswiftagent ネットワークに接続されていません"


class TestValkeyEnvironmentConfiguration:
    """Test Valkey environment configuration."""

    def test_valkey_restart_policy(self, docker_compose_config: dict):
        """Valkey が自動再起動設定されていること."""
        valkey_service = docker_compose_config["services"]["valkey"]
        assert "restart" in valkey_service, "Valkey restart が設定されていません"
        assert valkey_service["restart"] in [
            "always",
            "unless-stopped",
        ], "Valkey restart ポリシーが不正です"
