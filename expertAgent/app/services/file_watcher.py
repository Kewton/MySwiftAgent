"""File watcher for hot-reload functionality.

Monitors prompt YAML files for changes and invalidates cache.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

if TYPE_CHECKING:
    from watchdog.observers.api import BaseObserver

from app.services.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)


class PromptFileHandler(FileSystemEventHandler):
    """Handle file system events for prompt files."""

    def __init__(self, prompt_loader: PromptLoader) -> None:
        """Initialize the handler.

        Args:
            prompt_loader: PromptLoader instance to invalidate cache
        """
        self.prompt_loader = prompt_loader
        super().__init__()

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events.

        Args:
            event: File system event
        """
        if event.is_directory:
            return

        file_path = Path(str(event.src_path))

        # Only process .yaml files
        if file_path.suffix != ".yaml":
            return

        # Extract prompt name and version
        prompt_name = file_path.parent.name
        version = file_path.stem

        logger.info(f"Detected change: {prompt_name}/{version}.yaml")

        # Invalidate cache for this specific version
        if self.prompt_loader._cache is not None:
            cache_key = self.prompt_loader._cache.make_key(prompt_name, version)
            self.prompt_loader._cache.invalidate(cache_key)
            logger.info(f"Cache invalidated: {cache_key}")

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events.

        Args:
            event: File system event
        """
        # Same as on_modified for our purposes
        self.on_modified(event)


class FileWatcher:
    """Watch prompt files for changes and invalidate cache."""

    def __init__(
        self,
        base_dir: Path,
        prompt_loader: PromptLoader,
    ) -> None:
        """Initialize the file watcher.

        Args:
            base_dir: Base directory to watch
            prompt_loader: PromptLoader instance
        """
        self.base_dir = Path(base_dir)
        self.prompt_loader = prompt_loader
        self._observer: Optional["BaseObserver"] = None
        self._handler = PromptFileHandler(prompt_loader)

    async def start(self) -> None:
        """Start watching for file changes."""
        if self._observer is not None:
            logger.warning("FileWatcher already running")
            return

        self._observer = Observer()
        self._observer.schedule(
            self._handler,
            str(self.base_dir),
            recursive=True,
        )
        self._observer.start()
        logger.info(f"FileWatcher started for {self.base_dir}")

    async def stop(self) -> None:
        """Stop watching for file changes."""
        if self._observer is None:
            logger.warning("FileWatcher not running")
            return

        self._observer.stop()
        self._observer.join()
        self._observer = None
        logger.info("FileWatcher stopped")

    def is_running(self) -> bool:
        """Check if watcher is running.

        Returns:
            True if running, False otherwise
        """
        return self._observer is not None and self._observer.is_alive()
