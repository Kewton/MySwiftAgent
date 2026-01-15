"""Tests for error message sanitization.

Issue #343 Task 2.2: Test sanitize_error_message() function.

Security feature to prevent prompt injection and information leakage
when passing error messages to LLM.
"""


class TestSanitizeErrorMessage:
    """Test sanitize_error_message() function."""

    def test_function_exists(self) -> None:
        """Test that sanitize_error_message function exists."""
        from aiagent.langgraph.jobGeneratorV2.validators import (
            sanitize_error_message,
        )

        assert callable(sanitize_error_message)

    def test_masks_user_paths(self) -> None:
        """Test that user paths are masked."""
        from aiagent.langgraph.jobGeneratorV2.validators import (
            sanitize_error_message,
        )

        message = "Error at /Users/john/projects/secret/file.py"
        result = sanitize_error_message(message)

        assert "/Users/john" not in result
        assert "[USER_PATH]" in result

    def test_masks_long_tokens(self) -> None:
        """Test that long token-like strings are masked."""
        from aiagent.langgraph.jobGeneratorV2.validators import (
            sanitize_error_message,
        )

        # 32+ character alphanumeric string looks like a token
        token = "a" * 40
        message = f"API token: {token}"
        result = sanitize_error_message(message)

        assert token not in result
        assert "[TOKEN]" in result

    def test_masks_passwords(self) -> None:
        """Test that password values are masked."""
        from aiagent.langgraph.jobGeneratorV2.validators import (
            sanitize_error_message,
        )

        message = "Connection failed: password=secretpassword123"
        result = sanitize_error_message(message)

        assert "secretpassword123" not in result
        assert "[MASKED]" in result

    def test_removes_control_characters(self) -> None:
        """Test that control characters are removed."""
        from aiagent.langgraph.jobGeneratorV2.validators import (
            sanitize_error_message,
        )

        # Include various control characters
        message = "Error\x00with\x1fcontrol\x7fchars"
        result = sanitize_error_message(message)

        # Control characters should be removed
        assert "\x00" not in result
        assert "\x1f" not in result
        assert "\x7f" not in result
        # But text should remain
        assert "Error" in result
        assert "control" in result

    def test_escapes_template_braces(self) -> None:
        """Test that template braces are escaped to prevent LLM confusion."""
        from aiagent.langgraph.jobGeneratorV2.validators import (
            sanitize_error_message,
        )

        message = "Template error: {{variable}} and {{another}}"
        result = sanitize_error_message(message)

        # Double braces should be spaced to prevent template interpretation
        assert "{{" not in result or "{ {" in result
        assert "}}" not in result or "} }" in result

    def test_truncates_long_messages(self) -> None:
        """Test that long messages are truncated."""
        from aiagent.langgraph.jobGeneratorV2.validators import (
            sanitize_error_message,
        )

        # Create a message longer than default max_length (500)
        # Use words with spaces to avoid token pattern matching
        long_message = "This is a long error message. " * 50  # ~1500 chars
        result = sanitize_error_message(long_message)

        # Should be truncated to max_length
        assert len(result) <= 500
        assert result.endswith("...")

    def test_custom_max_length(self) -> None:
        """Test custom max_length parameter."""
        from aiagent.langgraph.jobGeneratorV2.validators import (
            sanitize_error_message,
        )

        # Use regular words to avoid token pattern matching
        message = "Error message content here. " * 10  # ~280 chars
        result = sanitize_error_message(message, max_length=50)

        assert len(result) <= 50
        assert result.endswith("...")

    def test_short_message_not_truncated(self) -> None:
        """Test that short messages are not truncated."""
        from aiagent.langgraph.jobGeneratorV2.validators import (
            sanitize_error_message,
        )

        message = "Short error message"
        result = sanitize_error_message(message)

        assert result == message
        assert not result.endswith("...")

    def test_empty_message(self) -> None:
        """Test handling of empty message."""
        from aiagent.langgraph.jobGeneratorV2.validators import (
            sanitize_error_message,
        )

        result = sanitize_error_message("")
        assert result == ""

    def test_preserves_normal_text(self) -> None:
        """Test that normal error text is preserved."""
        from aiagent.langgraph.jobGeneratorV2.validators import (
            sanitize_error_message,
        )

        message = "Invalid node configuration at nodes.search.agent"
        result = sanitize_error_message(message)

        # Normal error text should be preserved
        assert "Invalid node configuration" in result
        assert "nodes.search.agent" in result


class TestSensitivePatterns:
    """Test SENSITIVE_PATTERNS constant."""

    def test_sensitive_patterns_defined(self) -> None:
        """Test that SENSITIVE_PATTERNS is defined."""
        from aiagent.langgraph.jobGeneratorV2.validators import (
            SENSITIVE_PATTERNS,
        )

        assert SENSITIVE_PATTERNS is not None
        assert isinstance(SENSITIVE_PATTERNS, list)
        assert len(SENSITIVE_PATTERNS) > 0

    def test_sensitive_patterns_format(self) -> None:
        """Test that SENSITIVE_PATTERNS has correct format (regex, replacement)."""
        from aiagent.langgraph.jobGeneratorV2.validators import (
            SENSITIVE_PATTERNS,
        )

        for pattern in SENSITIVE_PATTERNS:
            assert isinstance(pattern, tuple), "Each pattern should be a tuple"
            assert len(pattern) == 2, "Each pattern should have (regex, replacement)"
            regex, replacement = pattern
            assert isinstance(regex, str), "Regex should be a string"
            assert isinstance(replacement, str), "Replacement should be a string"
