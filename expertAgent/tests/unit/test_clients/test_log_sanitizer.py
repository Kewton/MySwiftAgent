"""Unit tests for log_sanitizer module.

Issue #385: Tests for capability log sanitization utilities.

These tests verify:
- Task 2.3: Log sanitizer unit tests
- Sensitive key removal (_internal, secret_key, api_key, etc.)
- Nested object handling
- Log summary generation
"""


class TestSanitizeCapabilityForLog:
    """Tests for sanitize_capability_for_log function."""

    def test_sanitize_removes_internal_key(self):
        """Test that _internal key is removed from capability."""
        from aiagent.clients.utils.log_sanitizer import sanitize_capability_for_log

        capability = {
            "name": "fetchAgent",
            "endpoint": "/api/fetch",
            "_internal": {"secret": "hidden"},
        }

        result = sanitize_capability_for_log(capability)

        assert "name" in result
        assert "endpoint" in result
        assert "_internal" not in result

    def test_sanitize_removes_secret_key(self):
        """Test that secret_key is removed from capability."""
        from aiagent.clients.utils.log_sanitizer import sanitize_capability_for_log

        capability = {
            "name": "apiAgent",
            "secret_key": "super-secret-123",
        }

        result = sanitize_capability_for_log(capability)

        assert "name" in result
        assert "secret_key" not in result

    def test_sanitize_removes_api_key(self):
        """Test that api_key is removed from capability."""
        from aiagent.clients.utils.log_sanitizer import sanitize_capability_for_log

        capability = {
            "name": "externalApi",
            "api_key": "key-abc-123",
        }

        result = sanitize_capability_for_log(capability)

        assert "name" in result
        assert "api_key" not in result

    def test_sanitize_removes_token(self):
        """Test that token key is removed from capability."""
        from aiagent.clients.utils.log_sanitizer import sanitize_capability_for_log

        capability = {
            "name": "authAgent",
            "token": "bearer-token-xyz",
        }

        result = sanitize_capability_for_log(capability)

        assert "name" in result
        assert "token" not in result

    def test_sanitize_removes_password(self):
        """Test that password key is removed from capability."""
        from aiagent.clients.utils.log_sanitizer import sanitize_capability_for_log

        capability = {
            "name": "dbAgent",
            "password": "secret-password",
        }

        result = sanitize_capability_for_log(capability)

        assert "name" in result
        assert "password" not in result

    def test_sanitize_removes_credential(self):
        """Test that credential key is removed from capability."""
        from aiagent.clients.utils.log_sanitizer import sanitize_capability_for_log

        capability = {
            "name": "authAgent",
            "credential": {"type": "oauth", "value": "secret"},
        }

        result = sanitize_capability_for_log(capability)

        assert "name" in result
        assert "credential" not in result

    def test_sanitize_removes_auth(self):
        """Test that auth key is removed from capability."""
        from aiagent.clients.utils.log_sanitizer import sanitize_capability_for_log

        capability = {
            "name": "secureAgent",
            "auth": {"bearer": "token-123"},
        }

        result = sanitize_capability_for_log(capability)

        assert "name" in result
        assert "auth" not in result

    def test_sanitize_handles_nested_sensitive_keys(self):
        """Test that nested sensitive keys are handled properly."""
        from aiagent.clients.utils.log_sanitizer import sanitize_capability_for_log

        capability = {
            "name": "complexAgent",
            "config": {
                "endpoint": "/api/v1",
                "secret_key": "nested-secret",
                "settings": {
                    "timeout": 30,
                    "api_key": "deep-nested-key",
                },
            },
        }

        result = sanitize_capability_for_log(capability)

        assert "name" in result
        assert "config" in result
        assert "secret_key" not in result.get("config", {})
        # Nested config should have endpoint
        if "settings" in result.get("config", {}):
            assert "api_key" not in result["config"]["settings"]

    def test_sanitize_preserves_non_sensitive_data(self):
        """Test that non-sensitive data is preserved."""
        from aiagent.clients.utils.log_sanitizer import sanitize_capability_for_log

        capability = {
            "name": "testAgent",
            "endpoint": "/api/test",
            "methods": ["GET", "POST"],
            "metadata": {"version": "1.0", "enabled": True},
        }

        result = sanitize_capability_for_log(capability)

        assert result["name"] == "testAgent"
        assert result["endpoint"] == "/api/test"
        assert result["methods"] == ["GET", "POST"]
        assert result["metadata"]["version"] == "1.0"
        assert result["metadata"]["enabled"] is True

    def test_sanitize_handles_empty_capability(self):
        """Test sanitization of empty capability dict."""
        from aiagent.clients.utils.log_sanitizer import sanitize_capability_for_log

        result = sanitize_capability_for_log({})

        assert result == {}

    def test_sanitize_does_not_modify_original(self):
        """Test that original capability dict is not modified."""
        from aiagent.clients.utils.log_sanitizer import sanitize_capability_for_log

        original = {
            "name": "testAgent",
            "secret_key": "should-remain-in-original",
        }
        original_copy = original.copy()

        sanitize_capability_for_log(original)

        assert original == original_copy


class TestSanitizeCapabilitiesForLog:
    """Tests for sanitize_capabilities_for_log function."""

    def test_sanitize_multiple_capabilities(self):
        """Test sanitization of multiple capabilities."""
        from aiagent.clients.utils.log_sanitizer import sanitize_capabilities_for_log

        capabilities = [
            {"name": "agent1", "api_key": "key1"},
            {"name": "agent2", "secret_key": "secret2"},
            {"name": "agent3", "token": "token3"},
        ]

        result = sanitize_capabilities_for_log(capabilities)

        assert len(result) == 3
        assert all("name" in c for c in result)
        assert all("api_key" not in c for c in result)
        assert all("secret_key" not in c for c in result)
        assert all("token" not in c for c in result)

    def test_sanitize_empty_capabilities_list(self):
        """Test sanitization of empty capabilities list."""
        from aiagent.clients.utils.log_sanitizer import sanitize_capabilities_for_log

        result = sanitize_capabilities_for_log([])

        assert result == []

    def test_sanitize_does_not_modify_original_list(self):
        """Test that original list is not modified."""
        from aiagent.clients.utils.log_sanitizer import sanitize_capabilities_for_log

        original = [{"name": "agent1", "api_key": "key1"}]

        sanitize_capabilities_for_log(original)

        # Original list should not be modified
        assert original[0]["api_key"] == "key1"


class TestCreateCapabilityLogSummary:
    """Tests for create_capability_log_summary function."""

    def test_create_summary_with_capabilities(self):
        """Test log summary generation with capabilities."""
        from aiagent.clients.utils.log_sanitizer import create_capability_log_summary

        capabilities = [
            {"name": "fetchAgent", "endpoint": "/api/fetch"},
            {"name": "searchAgent", "endpoint": "/api/search"},
            {"name": "emailAgent", "endpoint": "/api/email"},
        ]

        result = create_capability_log_summary(capabilities)

        assert "3 capabilities" in result.lower() or "3" in result
        assert "fetchAgent" in result or "fetch" in result.lower()

    def test_create_summary_includes_count(self):
        """Test that summary includes capability count."""
        from aiagent.clients.utils.log_sanitizer import create_capability_log_summary

        capabilities = [
            {"name": "agent1"},
            {"name": "agent2"},
        ]

        result = create_capability_log_summary(capabilities)

        assert "2" in result

    def test_create_summary_lists_capability_names(self):
        """Test that summary lists capability names."""
        from aiagent.clients.utils.log_sanitizer import create_capability_log_summary

        capabilities = [
            {"name": "fetchAgent"},
            {"name": "searchAgent"},
        ]

        result = create_capability_log_summary(capabilities)

        assert "fetchAgent" in result
        assert "searchAgent" in result

    def test_empty_capabilities_summary(self):
        """Test log summary for empty capabilities list."""
        from aiagent.clients.utils.log_sanitizer import create_capability_log_summary

        result = create_capability_log_summary([])

        assert "0" in result or "no" in result.lower() or "empty" in result.lower()

    def test_summary_handles_missing_name(self):
        """Test summary handles capabilities without name field."""
        from aiagent.clients.utils.log_sanitizer import create_capability_log_summary

        capabilities = [
            {"endpoint": "/api/test"},  # No name
            {"name": "namedAgent"},
        ]

        result = create_capability_log_summary(capabilities)

        # Should not crash and should include count
        assert "2" in result
        assert "namedAgent" in result

    def test_summary_does_not_include_sensitive_data(self):
        """Test that summary does not include sensitive data."""
        from aiagent.clients.utils.log_sanitizer import create_capability_log_summary

        capabilities = [
            {"name": "agent1", "api_key": "secret-key-123"},
            {"name": "agent2", "token": "bearer-token-abc"},
        ]

        result = create_capability_log_summary(capabilities)

        assert "secret-key-123" not in result
        assert "bearer-token-abc" not in result


class TestSensitiveKeys:
    """Tests for SENSITIVE_KEYS constant."""

    def test_sensitive_keys_is_frozenset(self):
        """Test that SENSITIVE_KEYS is a frozenset."""
        from aiagent.clients.utils.log_sanitizer import SENSITIVE_KEYS

        assert isinstance(SENSITIVE_KEYS, frozenset)

    def test_sensitive_keys_contains_required_keys(self):
        """Test that SENSITIVE_KEYS contains all required sensitive keys."""
        from aiagent.clients.utils.log_sanitizer import SENSITIVE_KEYS

        required_keys = {
            "_internal",
            "secret_key",
            "api_key",
            "token",
            "password",
            "credential",
            "auth",
        }

        assert required_keys.issubset(SENSITIVE_KEYS)
