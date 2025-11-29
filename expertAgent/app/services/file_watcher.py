"""File watcher for hot-reload functionality.

Monitors prompt YAML files for changes and invalidates cache.
Implements Observer pattern for reacting to file system events.
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

# Constants
YAML_FILE_EXTENSION = ".yaml"


class PromptFileHandler(FileSystemEventHandler):
    """Handle file system events for prompt files.

    This class implements the Observer pattern's concrete observer,
    reacting to file system events by invalidating cached prompts.
    """

    def __init__(self, prompt_loader: PromptLoader) -> None:
        """Initialize the handler.

        Args:
            prompt_loader: PromptLoader instance to invalidate cache
        """
        self.prompt_loader = prompt_loader
        super().__init__()
        logger.debug("PromptFileHandler initialized")

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events.

        Args:
            event: File system event
        """
        self._process_file_event(event, "modified")

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events.

        Args:
            event: File system event
        """
        self._process_file_event(event, "created")

    def _process_file_event(self, event: FileSystemEvent, event_type: str) -> None:
        """Process file system events for YAML files.

        Args:
            event: File system event
            event_type: Type of event (modified, created, etc.)
        """
        if event.is_directory:
            logger.debug("Ignoring directory event: %s", event.src_path)
            return

        file_path = Path(str(event.src_path))

        # Only process .yaml files
        if file_path.suffix != YAML_FILE_EXTENSION:
            logger.debug("Ignoring non-YAML file: %s", file_path)
            return

        # Extract prompt name and version
        prompt_name = file_path.parent.name
        version = file_path.stem

        logger.info(
            f"Detected {event_type}: {prompt_name}/{version}{YAML_FILE_EXTENSION}"
        )

        # Invalidate cache for this specific version
        self._invalidate_cache(prompt_name, version)

    def _invalidate_cache(self, prompt_name: str, version: str) -> None:
        """Invalidate cache for a specific prompt version.

        Args:
            prompt_name: Name of the prompt
            version: Version name
        """
        if self.prompt_loader._cache is not None:
            cache_key = self.prompt_loader._cache.make_key(prompt_name, version)
            self.prompt_loader._cache.invalidate(cache_key)
            logger.info(f"Cache invalidated: {cache_key}")
        else:
            logger.debug("Cache not available for invalidation (caching disabled)")


class FileWatcher:
    """Watch prompt files for changes and invalidate cache.

    This class implements the Observer pattern's subject, monitoring the file system
    for changes to prompt YAML files and triggering cache invalidation.
    """

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
        logger.debug(f"FileWatcher initialized for directory: {self.base_dir}")

    async def start(self) -> None:
        """Start watching for file changes.

        This method starts the file system observer to monitor changes
        in the prompt directory tree.

        Note: If the watcher is already running, this method logs a warning
        and returns without starting a new observer.
        """
        if self._observer is not None:
            logger.warning("FileWatcher already running - skipping start")
            return

        try:
            self._observer = Observer()
            self._observer.schedule(
                self._handler,
                str(self.base_dir),
                recursive=True,
            )
            self._observer.start()
            logger.info(f"FileWatcher started for {self.base_dir}")
        except Exception as e:
            logger.error(f"Failed to start FileWatcher: {e}")
            self._observer = None
            raise

    async def stop(self) -> None:
        """Stop watching for file changes.

        This method stops the file system observer and waits for it to
        cleanly shut down.

        Note: If the watcher is not running, this method logs a warning
        and returns without error.
        """
        if self._observer is None:
            logger.warning("FileWatcher not running - skipping stop")
            return

        try:
            self._observer.stop()
            self._observer.join(timeout=5.0)
            self._observer = None
            logger.info("FileWatcher stopped successfully")
        except Exception as e:
            logger.error(f"Error while stopping FileWatcher: {e}")
            self._observer = None
            raise

    def is_running(self) -> bool:
        """Check if watcher is running.

        Returns:
            True if running, False otherwise
        """
        is_alive = self._observer is not None and self._observer.is_alive()
        logger.debug(f"FileWatcher is_running: {is_alive}")
        return is_alive
