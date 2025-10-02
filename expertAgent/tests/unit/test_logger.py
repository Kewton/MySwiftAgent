"""Tests for core.logger module."""

import logging

from core.logger import getlogger, setup_logging


class TestLogger:
    """Test logger functionality."""

    def test_getlogger_returns_logger(self):
        """Test that getlogger returns a Logger instance."""
        logger = getlogger()
        assert isinstance(logger, logging.Logger)

    def test_getlogger_returns_logger_with_module_name(self):
        """Test that getlogger returns logger with module name."""
        logger = getlogger()
        # Logger name should be the module name where getlogger is defined
        assert logger.name == "core.logger"

    def test_setup_logging_creates_log_directory(self, monkeypatch, tmp_path):
        """Test that setup_logging creates log directory."""
        # Use temporary directory for testing
        log_dir = tmp_path / "test_logs"
        monkeypatch.setenv("LOG_DIR", str(log_dir))

        # Re-import to pick up new env var
        from importlib import reload

        import core.config

        reload(core.config)
        from core import logger as logger_module

        reload(logger_module)

        # Reset the flag
        logger_module.logging_setup_done = False

        # Setup logging
        logger_module.setup_logging()

        # Check directory was created
        assert log_dir.exists()
        assert log_dir.is_dir()

    def test_setup_logging_idempotent(self):
        """Test that setup_logging can be called multiple times safely."""
        # This should not raise any errors
        setup_logging()
        setup_logging()
        setup_logging()

    def test_logger_can_log_messages(self):
        """Test that logger can log messages."""
        logger = getlogger()

        # These should not raise errors
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
