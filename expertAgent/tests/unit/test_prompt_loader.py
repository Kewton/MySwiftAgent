"""Unit tests for PromptLoader with YAML support and hot-reload.

Tests cover:
- YAML file loading with default.yaml fallback
- Multiple YAML files per prompt name
- Version specification
- Hot-reload functionality
- Cache management
- Error handling
"""

import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.services.prompt_loader import PromptLoader, PromptNotFoundError


class TestPromptLoaderBasics:
    """Test basic prompt loading functionality."""

    def test_load_default_yaml(self, tmp_path: Path) -> None:
        """Test loading default.yaml when no version is specified."""
        # Arrange: Create directory structure
        prompt_dir = tmp_path / "test_prompt"
        prompt_dir.mkdir()
        default_file = prompt_dir / "default.yaml"
        default_file.write_text(
            yaml.dump({"system_prompt": "Default prompt", "version": "1.0"}),
            encoding="utf-8",
        )

        loader = PromptLoader(base_dir=tmp_path)

        # Act
        result = loader.load_prompt("test_prompt")

        # Assert
        assert result["system_prompt"] == "Default prompt"
        assert result["version"] == "1.0"

    def test_load_specific_version(self, tmp_path: Path) -> None:
        """Test loading a specific YAML file version."""
        # Arrange
        prompt_dir = tmp_path / "test_prompt"
        prompt_dir.mkdir()

        # Create default and v2
        default_file = prompt_dir / "default.yaml"
        default_file.write_text(
            yaml.dump({"system_prompt": "Default", "version": "1.0"}),
            encoding="utf-8",
        )

        v2_file = prompt_dir / "v2.yaml"
        v2_file.write_text(
            yaml.dump({"system_prompt": "Version 2", "version": "2.0"}),
            encoding="utf-8",
        )

        loader = PromptLoader(base_dir=tmp_path)

        # Act
        result = loader.load_prompt("test_prompt", version="v2")

        # Assert
        assert result["system_prompt"] == "Version 2"
        assert result["version"] == "2.0"

    def test_prompt_not_found_error(self, tmp_path: Path) -> None:
        """Test error when prompt directory doesn't exist."""
        loader = PromptLoader(base_dir=tmp_path)

        with pytest.raises(PromptNotFoundError) as exc_info:
            loader.load_prompt("nonexistent_prompt")

        assert "nonexistent_prompt" in str(exc_info.value)

    def test_default_yaml_not_found_error(self, tmp_path: Path) -> None:
        """Test error when default.yaml doesn't exist and no version specified."""
        # Arrange: Create directory without default.yaml
        prompt_dir = tmp_path / "test_prompt"
        prompt_dir.mkdir()

        loader = PromptLoader(base_dir=tmp_path)

        # Act & Assert
        with pytest.raises(PromptNotFoundError) as exc_info:
            loader.load_prompt("test_prompt")

        assert "default.yaml" in str(exc_info.value)

    def test_specific_version_not_found_error(self, tmp_path: Path) -> None:
        """Test error when specific version YAML doesn't exist."""
        # Arrange
        prompt_dir = tmp_path / "test_prompt"
        prompt_dir.mkdir()

        default_file = prompt_dir / "default.yaml"
        default_file.write_text(
            yaml.dump({"system_prompt": "Default"}), encoding="utf-8"
        )

        loader = PromptLoader(base_dir=tmp_path)

        # Act & Assert
        with pytest.raises(PromptNotFoundError) as exc_info:
            loader.load_prompt("test_prompt", version="v99")

        assert "v99.yaml" in str(exc_info.value)


class TestPromptLoaderCache:
    """Test caching functionality."""

    def test_cache_hit(self, tmp_path: Path) -> None:
        """Test that prompts are cached and reused."""
        # Arrange
        prompt_dir = tmp_path / "test_prompt"
        prompt_dir.mkdir()

        default_file = prompt_dir / "default.yaml"
        default_file.write_text(
            yaml.dump({"system_prompt": "Original"}), encoding="utf-8"
        )

        loader = PromptLoader(base_dir=tmp_path, enable_cache=True)

        # Act: Load twice
        result1 = loader.load_prompt("test_prompt")

        # Modify file (should not affect cached result)
        default_file.write_text(
            yaml.dump({"system_prompt": "Modified"}), encoding="utf-8"
        )

        result2 = loader.load_prompt("test_prompt")

        # Assert: Should return cached value
        assert result1["system_prompt"] == "Original"
        assert result2["system_prompt"] == "Original"

    def test_cache_disabled(self, tmp_path: Path) -> None:
        """Test that cache can be disabled."""
        # Arrange
        prompt_dir = tmp_path / "test_prompt"
        prompt_dir.mkdir()

        default_file = prompt_dir / "default.yaml"
        default_file.write_text(
            yaml.dump({"system_prompt": "Original"}), encoding="utf-8"
        )

        loader = PromptLoader(base_dir=tmp_path, enable_cache=False)

        # Act: Load, modify, load again
        result1 = loader.load_prompt("test_prompt")

        default_file.write_text(
            yaml.dump({"system_prompt": "Modified"}), encoding="utf-8"
        )

        result2 = loader.load_prompt("test_prompt")

        # Assert: Should return new value
        assert result1["system_prompt"] == "Original"
        assert result2["system_prompt"] == "Modified"

    def test_clear_cache(self, tmp_path: Path) -> None:
        """Test manual cache clearing."""
        # Arrange
        prompt_dir = tmp_path / "test_prompt"
        prompt_dir.mkdir()

        default_file = prompt_dir / "default.yaml"
        default_file.write_text(
            yaml.dump({"system_prompt": "Original"}), encoding="utf-8"
        )

        loader = PromptLoader(base_dir=tmp_path, enable_cache=True)

        # Act
        result1 = loader.load_prompt("test_prompt")

        default_file.write_text(
            yaml.dump({"system_prompt": "Modified"}), encoding="utf-8"
        )

        loader.clear_cache()
        result2 = loader.load_prompt("test_prompt")

        # Assert: Should return new value after cache clear
        assert result1["system_prompt"] == "Original"
        assert result2["system_prompt"] == "Modified"


class TestPromptLoaderMultipleVersions:
    """Test managing multiple YAML versions."""

    def test_list_available_versions(self, tmp_path: Path) -> None:
        """Test listing all available YAML versions for a prompt."""
        # Arrange
        prompt_dir = tmp_path / "test_prompt"
        prompt_dir.mkdir()

        # Create multiple versions
        (prompt_dir / "default.yaml").touch()
        (prompt_dir / "v2.yaml").touch()
        (prompt_dir / "experimental.yaml").touch()
        (prompt_dir / "README.md").touch()  # Non-YAML file

        loader = PromptLoader(base_dir=tmp_path)

        # Act
        versions = loader.list_versions("test_prompt")

        # Assert
        assert set(versions) == {"default", "v2", "experimental"}

    def test_version_switching(self, tmp_path: Path) -> None:
        """Test switching between different versions."""
        # Arrange
        prompt_dir = tmp_path / "test_prompt"
        prompt_dir.mkdir()

        (prompt_dir / "default.yaml").write_text(
            yaml.dump({"name": "default"}), encoding="utf-8"
        )
        (prompt_dir / "v2.yaml").write_text(
            yaml.dump({"name": "v2"}), encoding="utf-8"
        )
        (prompt_dir / "experimental.yaml").write_text(
            yaml.dump({"name": "experimental"}), encoding="utf-8"
        )

        loader = PromptLoader(base_dir=tmp_path)

        # Act & Assert
        assert loader.load_prompt("test_prompt")["name"] == "default"
        assert loader.load_prompt("test_prompt", version="v2")["name"] == "v2"
        assert (
            loader.load_prompt("test_prompt", version="experimental")["name"]
            == "experimental"
        )


class TestPromptLoaderPerformance:
    """Test performance requirements."""

    def test_load_time_under_100ms(self, tmp_path: Path) -> None:
        """Test that prompt loading completes within 100ms."""
        import time

        # Arrange
        prompt_dir = tmp_path / "test_prompt"
        prompt_dir.mkdir()

        # Create a moderately sized YAML file
        data = {
            "system_prompt": "A" * 1000,
            "user_prompt_template": "B" * 1000,
            "metadata": {"key": "value"},
        }
        (prompt_dir / "default.yaml").write_text(
            yaml.dump(data), encoding="utf-8"
        )

        loader = PromptLoader(base_dir=tmp_path)

        # Act
        start = time.time()
        loader.load_prompt("test_prompt")
        elapsed = (time.time() - start) * 1000  # Convert to ms

        # Assert: Must complete within 100ms
        assert elapsed < 100, f"Loading took {elapsed:.2f}ms, expected < 100ms"
