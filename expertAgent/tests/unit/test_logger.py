"""Tests for core.logger module."""

import logging
import time
from unittest.mock import MagicMock, patch

from core.logger import (
    StopWatch,
    declogger,
    edtmessage,
    getlogger,
    setfileConfig,
    setup_logging,
    writedebuglog,
    writeerrorlog,
    writeinfolog,
)


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

    def test_setup_logging_with_existing_directory(self, monkeypatch, tmp_path):
        """Test that setup_logging works with existing log directory."""
        # Create directory before setup
        log_dir = tmp_path / "existing_logs"
        log_dir.mkdir()
        monkeypatch.setenv("LOG_DIR", str(log_dir))

        # Re-import to pick up new env var
        from importlib import reload

        import core.config

        reload(core.config)
        from core import logger as logger_module

        reload(logger_module)

        # Reset the flag
        logger_module.logging_setup_done = False

        # Setup logging with existing directory
        logger_module.setup_logging()

        # Check directory still exists
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

    @patch("logging.config.fileConfig")
    def test_setfileConfig(self, mock_fileConfig):
        """Test setfileConfig function."""
        test_path = "/path/to/config.ini"
        setfileConfig(test_path)
        mock_fileConfig.assert_called_once_with(fname=test_path)


class TestDeclogger:
    """Test declogger decorator."""

    def test_declogger_decorator(self):
        """Test that declogger decorator wraps function correctly."""
        @declogger
        def test_function(x, y):
            return x + y

        result = test_function(2, 3)
        assert result == 5
        assert test_function.__name__ == "test_function"

    def test_declogger_with_kwargs(self):
        """Test declogger with keyword arguments."""
        @declogger
        def test_function(x, y=10):
            return x * y

        result = test_function(5, y=3)
        assert result == 15

    @patch("core.logger.getlogger")
    def test_declogger_logs_messages(self, mock_getlogger):
        """Test that declogger logs start and end messages."""
        mock_logger = MagicMock()
        mock_getlogger.return_value = mock_logger

        @declogger
        def test_function():
            return "result"

        result = test_function()
        assert result == "result"
        assert mock_logger.debug.call_count >= 2


class TestEdtmessage:
    """Test edtmessage function."""

    def test_edtmessage_formats_message(self):
        """Test that edtmessage formats message with context."""
        message = edtmessage("Test message")
        # Should contain the message
        assert "Test message" in message
        # Should contain module/file info
        assert "[" in message
        assert "]" in message

    def test_edtmessage_with_different_types(self):
        """Test edtmessage with different message types."""
        # String message
        msg1 = edtmessage("string message")
        assert "string message" in msg1

        # Number message
        msg2 = edtmessage(42)
        assert "42" in msg2

        # Dict message
        msg3 = edtmessage({"key": "value"})
        assert "key" in msg3


class TestWriteLogs:
    """Test write log functions."""

    @patch("core.logger.getlogger")
    def test_writedebuglog(self, mock_getlogger):
        """Test writedebuglog function."""
        mock_logger = MagicMock()
        mock_getlogger.return_value = mock_logger

        writedebuglog("Debug message")
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args[0][0]
        assert "Debug message" in call_args

    @patch("core.logger.getlogger")
    def test_writeinfolog(self, mock_getlogger):
        """Test writeinfolog function."""
        mock_logger = MagicMock()
        mock_getlogger.return_value = mock_logger

        writeinfolog("Info message")
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "Info message" in call_args

    @patch("core.logger.getlogger")
    def test_writeerrorlog(self, mock_getlogger):
        """Test writeerrorlog function."""
        mock_logger = MagicMock()
        mock_getlogger.return_value = mock_logger

        writeerrorlog("Error message")
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0][0]
        assert "Error message" in call_args


class TestStopWatch:
    """Test StopWatch class."""

    def test_stopwatch_measures_time(self):
        """Test that StopWatch measures elapsed time."""
        sw = StopWatch()
        sw.sw_start()
        time.sleep(0.1)  # Sleep for 100ms
        elapsed = sw.sw_stop()

        # Should be at least 0.1 seconds
        assert elapsed >= 0.1
        # Should be less than 0.2 seconds (with some margin)
        assert elapsed < 0.2

    def test_stopwatch_multiple_measurements(self):
        """Test multiple measurements with same StopWatch."""
        sw = StopWatch()

        # First measurement
        sw.sw_start()
        time.sleep(0.05)
        elapsed1 = sw.sw_stop()
        assert elapsed1 >= 0.05

        # Second measurement (should reset)
        sw.sw_start()
        time.sleep(0.05)
        elapsed2 = sw.sw_stop()
        assert elapsed2 >= 0.05

    def test_stopwatch_zero_elapsed_time(self):
        """Test StopWatch with near-zero elapsed time."""
        sw = StopWatch()
        sw.sw_start()
        elapsed = sw.sw_stop()

        # Should be very close to 0
        assert elapsed >= 0
        assert elapsed < 0.01
