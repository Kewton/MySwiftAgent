"""Unit tests for FileWatcher hot-reload functionality.

Tests cover:
- File modification detection
- Cache invalidation on file change
- Directory watching
- Multiple file changes
"""

import asyncio
from pathlib import Path

import pytest
import yaml

from app.services.file_watcher import FileWatcher
from app.services.prompt_loader import PromptLoader


class TestFileWatcher:
    """Test hot-reload functionality."""

    @pytest.mark.asyncio
    async def test_file_change_detection(self, tmp_path: Path) -> None:
        """Test that file changes are detected."""
        # Arrange
        prompt_dir = tmp_path / "test_prompt"
        prompt_dir.mkdir()

        default_file = prompt_dir / "default.yaml"
        default_file.write_text(yaml.dump({"value": "original"}), encoding="utf-8")

        loader = PromptLoader(base_dir=tmp_path, enable_cache=True)
        watcher = FileWatcher(base_dir=tmp_path, prompt_loader=loader)

        # Load initial prompt (cached)
        initial = loader.load_prompt("test_prompt")
        assert initial["value"] == "original"

        # Act: Start watcher
        await watcher.start()

        # Modify file
        await asyncio.sleep(0.1)  # Ensure watcher is ready
        default_file.write_text(yaml.dump({"value": "modified"}), encoding="utf-8")

        # Wait for file system event to propagate
        await asyncio.sleep(0.5)

        # Assert: Cache should be invalidated, new value loaded
        updated = loader.load_prompt("test_prompt")
        assert updated["value"] == "modified"

        # Cleanup
        await watcher.stop()

    @pytest.mark.asyncio
    async def test_multiple_file_changes(self, tmp_path: Path) -> None:
        """Test handling multiple file changes."""
        # Arrange
        prompt_dir = tmp_path / "test_prompt"
        prompt_dir.mkdir()

        default_file = prompt_dir / "default.yaml"
        v2_file = prompt_dir / "v2.yaml"

        default_file.write_text(yaml.dump({"version": "default_v1"}), encoding="utf-8")
        v2_file.write_text(yaml.dump({"version": "v2_v1"}), encoding="utf-8")

        loader = PromptLoader(base_dir=tmp_path, enable_cache=True)
        watcher = FileWatcher(base_dir=tmp_path, prompt_loader=loader)

        # Load both versions
        loader.load_prompt("test_prompt")
        loader.load_prompt("test_prompt", version="v2")

        # Act: Start watcher and modify both files
        await watcher.start()
        await asyncio.sleep(0.1)

        default_file.write_text(yaml.dump({"version": "default_v2"}), encoding="utf-8")
        v2_file.write_text(yaml.dump({"version": "v2_v2"}), encoding="utf-8")

        await asyncio.sleep(0.5)

        # Assert: Both should be updated
        assert loader.load_prompt("test_prompt")["version"] == "default_v2"
        assert loader.load_prompt("test_prompt", version="v2")["version"] == "v2_v2"

        # Cleanup
        await watcher.stop()

    @pytest.mark.asyncio
    async def test_watcher_can_be_started_and_stopped(self, tmp_path: Path) -> None:
        """Test that watcher can be started and stopped cleanly."""
        # Arrange
        loader = PromptLoader(base_dir=tmp_path, enable_cache=True)
        watcher = FileWatcher(base_dir=tmp_path, prompt_loader=loader)

        # Act & Assert
        await watcher.start()
        assert watcher.is_running()

        await watcher.stop()
        assert not watcher.is_running()

    @pytest.mark.asyncio
    async def test_new_file_detection(self, tmp_path: Path) -> None:
        """Test detection when a new YAML file is added."""
        # Arrange
        prompt_dir = tmp_path / "test_prompt"
        prompt_dir.mkdir()

        default_file = prompt_dir / "default.yaml"
        default_file.write_text(yaml.dump({"content": "default"}), encoding="utf-8")

        loader = PromptLoader(base_dir=tmp_path, enable_cache=True)
        watcher = FileWatcher(base_dir=tmp_path, prompt_loader=loader)

        await watcher.start()
        await asyncio.sleep(0.1)

        # Act: Add new version file
        new_file = prompt_dir / "v3.yaml"
        new_file.write_text(yaml.dump({"content": "v3"}), encoding="utf-8")

        await asyncio.sleep(0.5)

        # Assert: New version should be loadable
        result = loader.load_prompt("test_prompt", version="v3")
        assert result["content"] == "v3"

        # Cleanup
        await watcher.stop()


class TestFileWatcherErrorHandling:
    """Test error handling in FileWatcher."""

    @pytest.mark.asyncio
    async def test_invalid_yaml_does_not_crash(self, tmp_path: Path) -> None:
        """Test that invalid YAML doesn't crash the watcher."""
        # Arrange
        prompt_dir = tmp_path / "test_prompt"
        prompt_dir.mkdir()

        default_file = prompt_dir / "default.yaml"
        default_file.write_text(yaml.dump({"content": "valid"}), encoding="utf-8")

        loader = PromptLoader(base_dir=tmp_path, enable_cache=True)
        watcher = FileWatcher(base_dir=tmp_path, prompt_loader=loader)

        await watcher.start()
        await asyncio.sleep(0.1)

        # Act: Write invalid YAML
        default_file.write_text("invalid: yaml: content: [", encoding="utf-8")
        await asyncio.sleep(0.5)

        # Assert: Watcher should still be running
        assert watcher.is_running()

        # Cleanup
        await watcher.stop()

    @pytest.mark.asyncio
    async def test_double_start_warning(self, tmp_path: Path) -> None:
        """Test warning when starting an already running watcher."""
        # Arrange
        loader = PromptLoader(base_dir=tmp_path, enable_cache=True)
        watcher = FileWatcher(base_dir=tmp_path, prompt_loader=loader)

        # Act
        await watcher.start()
        await watcher.start()  # Second start should log warning

        # Assert: Should still be running
        assert watcher.is_running()

        # Cleanup
        await watcher.stop()

    @pytest.mark.asyncio
    async def test_double_stop_warning(self, tmp_path: Path) -> None:
        """Test warning when stopping an already stopped watcher."""
        # Arrange
        loader = PromptLoader(base_dir=tmp_path, enable_cache=True)
        watcher = FileWatcher(base_dir=tmp_path, prompt_loader=loader)

        # Act
        await watcher.start()
        await watcher.stop()
        await watcher.stop()  # Second stop should log warning

        # Assert: Should not be running
        assert not watcher.is_running()

    @pytest.mark.asyncio
    async def test_non_yaml_file_ignored(self, tmp_path: Path) -> None:
        """Test that non-YAML files are ignored by the watcher."""
        # Arrange
        prompt_dir = tmp_path / "test_prompt"
        prompt_dir.mkdir()

        loader = PromptLoader(base_dir=tmp_path, enable_cache=True)
        watcher = FileWatcher(base_dir=tmp_path, prompt_loader=loader)

        await watcher.start()
        await asyncio.sleep(0.1)

        # Act: Create non-YAML file
        txt_file = prompt_dir / "readme.txt"
        txt_file.write_text("This is not a YAML file", encoding="utf-8")
        await asyncio.sleep(0.5)

        # Assert: Watcher should still be running (no crash)
        assert watcher.is_running()

        # Cleanup
        await watcher.stop()

    @pytest.mark.asyncio
    async def test_cache_disabled_no_invalidation(self, tmp_path: Path) -> None:
        """Test that watcher doesn't crash when cache is disabled."""
        # Arrange
        prompt_dir = tmp_path / "test_prompt"
        prompt_dir.mkdir()

        default_file = prompt_dir / "default.yaml"
        default_file.write_text(yaml.dump({"content": "original"}), encoding="utf-8")

        loader = PromptLoader(base_dir=tmp_path, enable_cache=False)
        watcher = FileWatcher(base_dir=tmp_path, prompt_loader=loader)

        await watcher.start()
        await asyncio.sleep(0.1)

        # Act: Modify file (should not crash even though cache is None)
        default_file.write_text(yaml.dump({"content": "modified"}), encoding="utf-8")
        await asyncio.sleep(0.5)

        # Assert: Watcher should still be running
        assert watcher.is_running()

        # Cleanup
        await watcher.stop()

    @pytest.mark.asyncio
    async def test_watcher_start_exception_handling(self, tmp_path: Path) -> None:
        """Test exception handling when starting watcher fails."""
        # Arrange
        loader = PromptLoader(base_dir=tmp_path, enable_cache=True)
        # Use a non-existent directory to trigger an error
        watcher = FileWatcher(base_dir=tmp_path / "nonexistent", prompt_loader=loader)

        # Act & Assert: Should handle the error gracefully
        try:
            await watcher.start()
            # If it succeeds (watchdog creates the directory), stop it
            if watcher.is_running():
                await watcher.stop()
        except Exception:
            # Expected if directory doesn't exist and can't be created
            pass
