"""Extended tests for core.logger module."""

import time

from core.logger import (
    StopWatch,
    declogger,
    edtmessage,
    writedebuglog,
    writeerrorlog,
    writeinfolog,
)


class TestLoggerUtilities:
    """Test logger utility functions."""

    def test_writedebuglog(self):
        """Test writedebuglog function."""
        # Should not raise any errors
        writedebuglog("Debug message")

    def test_writeinfolog(self):
        """Test writeinfolog function."""
        # Should not raise any errors
        writeinfolog("Info message")

    def test_writeerrorlog(self):
        """Test writeerrorlog function."""
        # Should not raise any errors
        writeerrorlog("Error message")

    def test_edtmessage(self):
        """Test edtmessage function."""
        message = edtmessage("Test message")
        # Should contain the message and some context
        assert "Test message" in message
        assert "[" in message
        assert "]" in message


class TestDeclogger:
    """Test declogger decorator."""

    def test_declogger_basic(self):
        """Test declogger decorator on a simple function."""
        @declogger
        def sample_function(x, y):
            return x + y

        result = sample_function(2, 3)
        assert result == 5
        assert sample_function.__name__ == "sample_function"

    def test_declogger_with_kwargs(self):
        """Test declogger decorator with keyword arguments."""
        @declogger
        def sample_function(x, y=10):
            return x * y

        result = sample_function(5, y=3)
        assert result == 15

    def test_declogger_preserves_function_name(self):
        """Test that declogger preserves function name."""
        @declogger
        def my_test_function():
            return "test"

        assert my_test_function.__name__ == "my_test_function"


class TestStopWatch:
    """Test StopWatch class."""

    def test_stopwatch_basic(self):
        """Test basic stopwatch functionality."""
        sw = StopWatch()
        sw.sw_start()
        time.sleep(0.01)  # Sleep for 10ms
        elapsed = sw.sw_stop()
        # Should be at least 10ms
        assert elapsed >= 0.01
        # Should be less than 1 second (generous upper bound)
        assert elapsed < 1.0

    def test_stopwatch_multiple_calls(self):
        """Test multiple stopwatch calls."""
        sw = StopWatch()
        sw.sw_start()
        time.sleep(0.01)
        elapsed1 = sw.sw_stop()

        # Start again
        sw.sw_start()
        time.sleep(0.01)
        elapsed2 = sw.sw_stop()

        assert elapsed1 >= 0.01
        assert elapsed2 >= 0.01
