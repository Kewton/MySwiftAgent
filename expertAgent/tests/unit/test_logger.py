"""Tests for core.logger module."""

import logging
import time
from unittest.mock import patch

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

    def test_setup_logging_creates_log_directory(self, tmp_path):
        """Test that setup_logging creates log directory."""
        from unittest.mock import patch

        # Use temporary directory for testing
        log_dir = tmp_path / "test_logs"

        # Patch settings.LOG_DIR directly
        from core.config import settings

        with patch.object(settings, "LOG_DIR", str(log_dir)):
            # Import logger module
            import sys

            if "core.logger" in sys.modules:
                del sys.modules["core.logger"]

            from core import logger as logger_module

            # Reset the flag
            logger_module.logging_setup_done = False

            # Setup logging
            logger_module.setup_logging()

            # Check directory was created
            assert log_dir.exists()
            assert log_dir.is_dir()

    def test_setup_logging_with_existing_directory(self, tmp_path):
        """Test that setup_logging works with existing log directory."""
        from unittest.mock import patch

        # Create directory before setup
        log_dir = tmp_path / "existing_logs"
        log_dir.mkdir()

        # Patch settings.LOG_DIR directly
        from core.config import settings

        with patch.object(settings, "LOG_DIR", str(log_dir)):
            # Import logger module
            import sys

            if "core.logger" in sys.modules:
                del sys.modules["core.logger"]

            from core import logger as logger_module

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

    def test_declogger_logs_messages(self, caplog):
        """Test that declogger logs start and end messages."""
        import logging

        # Set logger level to DEBUG to capture debug messages
        with caplog.at_level(logging.DEBUG, logger="core.logger"):

            @declogger
            def test_function():
                return "result"

            result = test_function()

            # Verify result
            assert result == "result"

            # Verify log messages were generated
            debug_messages = [
                record.message
                for record in caplog.records
                if record.levelname == "DEBUG"
            ]
            assert len(debug_messages) >= 2
            assert any("start" in msg for msg in debug_messages)
            assert any("end" in msg for msg in debug_messages)


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

    def test_writedebuglog(self, caplog):
        """Test writedebuglog function."""
        import logging

        with caplog.at_level(logging.DEBUG, logger="core.logger"):
            writedebuglog("Debug message")

            # Verify log was generated
            assert len(caplog.records) >= 1
            debug_records = [r for r in caplog.records if r.levelname == "DEBUG"]
            assert len(debug_records) >= 1
            assert "Debug message" in debug_records[0].message

    def test_writeinfolog(self, caplog):
        """Test writeinfolog function."""
        import logging

        with caplog.at_level(logging.INFO, logger="core.logger"):
            writeinfolog("Info message")

            # Verify log was generated
            assert len(caplog.records) >= 1
            info_records = [r for r in caplog.records if r.levelname == "INFO"]
            assert len(info_records) >= 1
            assert "Info message" in info_records[0].message

    def test_writeerrorlog(self, caplog):
        """Test writeerrorlog function."""
        import logging

        with caplog.at_level(logging.ERROR, logger="core.logger"):
            writeerrorlog("Error message")

            # Verify log was generated
            assert len(caplog.records) >= 1
            error_records = [r for r in caplog.records if r.levelname == "ERROR"]
            assert len(error_records) >= 1
            assert "Error message" in error_records[0].message


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
