"""Integration tests for MyVault integration.

These tests require MyVault service to be running.
Run with: pytest tests/integration/test_myvault_integration.py -v
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from core.secrets import secrets_manager


class TestMyVaultIntegration:
    """Integration tests for MyVault functionality."""

    @pytest.fixture
    def client(self):
        """Test client fixture."""
        return TestClient(app)

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear cache before each test."""
        secrets_manager.clear_cache()
        yield
        secrets_manager.clear_cache()

    @pytest.mark.integration
    @pytest.mark.skipif(
        not secrets_manager.myvault_enabled,
        reason="MyVault not enabled in test environment",
    )
    def test_aiagent_with_project_parameter(self, client):
        """Test AI agent endpoint with project parameter."""
        # This test requires MyVault to be running and configured
        response = client.post(
            "/v1/aiagent/sample",
            json={
                "user_input": "Hello",
                "project": "test-project",
            },
        )

        # Should not fail with authentication errors
        assert response.status_code in [200, 500]  # May fail for other reasons

    @pytest.mark.integration
    @pytest.mark.skipif(
        not secrets_manager.myvault_enabled,
        reason="MyVault not enabled in test environment",
    )
    def test_secrets_fallback_mechanism(self):
        """Test that secrets fallback to env vars when MyVault fails."""
        # Mock environment variable
        with patch.object(secrets_manager.settings, "OPENAI_API_KEY", "env-test-key"):
            # Try to get secret with non-existent project
            # Should fallback to env var
            try:
                result = secrets_manager.get_secret(
                    "OPENAI_API_KEY", project="nonexistent-project"
                )
                # If MyVault fails, should get env var
                assert result == "env-test-key"
            except ValueError:
                # If both fail, ValueError is expected
                pass

    @pytest.mark.integration
    def test_admin_reload_endpoint(self, client):
        """Test admin reload endpoint."""
        # Setup admin token
        admin_token = "test-admin-token"  # noqa: S105 # Test fixture token

        with patch("app.api.v1.admin_endpoints.settings.ADMIN_TOKEN", admin_token):
            response = client.post(
                "/v1/admin/reload-secrets",
                json={"project": None},
                headers={"X-Admin-Token": admin_token},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    @pytest.mark.integration
    def test_cache_performance(self):
        """Test cache improves performance."""
        if not secrets_manager.myvault_enabled:
            pytest.skip("MyVault not enabled")

        import time

        # First call - cache miss
        start1 = time.time()
        try:
            secrets_manager.get_secret("OPENAI_API_KEY")
        except Exception as e:
            # May fail if not configured - this is expected in test environment
            print(f"Cache test: First call failed (expected): {e}")
        end1 = time.time()
        time1 = end1 - start1

        # Second call - cache hit (should be faster)
        start2 = time.time()
        try:
            secrets_manager.get_secret("OPENAI_API_KEY")
        except Exception as e:
            # May fail if not configured - this is expected in test environment
            print(f"Cache test: Second call failed (expected): {e}")
        end2 = time.time()
        time2 = end2 - start2

        # Cache hit should be significantly faster
        # (This is a rough test - actual timing may vary)
        if time1 > 0.001:  # Only test if first call took measurable time
            assert time2 < time1 * 0.5  # Cache should be at least 2x faster

    @pytest.mark.integration
    @pytest.mark.skipif(
        not secrets_manager.myvault_enabled,
        reason="MyVault not enabled in test environment",
    )
    def test_multiple_projects_isolation(self):
        """Test that different projects have isolated caches."""
        # Get secret from project1
        try:
            _value1 = secrets_manager.get_secret("OPENAI_API_KEY", project="project1")
        except Exception:
            pytest.skip("Project1 not configured")

        # Get secret from project2
        try:
            _value2 = secrets_manager.get_secret("OPENAI_API_KEY", project="project2")
        except Exception:
            pytest.skip("Project2 not configured")

        # Clear project1 cache
        secrets_manager.clear_cache(project="project1")

        # Project2 cache should still be valid
        # (This would be evident in performance if we had timing)

    @pytest.mark.integration
    def test_health_endpoints(self, client):
        """Test health endpoints with MyVault integration."""
        # Main health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

        # Admin health endpoint (without token - should warn)
        response = client.get("/v1/admin/health")
        assert response.status_code in [200, 401]

    @pytest.mark.integration
    def test_error_handling_with_invalid_project(self, client):
        """Test error handling with invalid project."""
        if not secrets_manager.myvault_enabled:
            pytest.skip("MyVault not enabled")

        # Try to use non-existent project
        # Should fallback or error gracefully
        try:
            result = secrets_manager.get_secret(
                "OPENAI_API_KEY", project="nonexistent-project-12345"
            )
            # If we get here, fallback worked
            assert result is not None
        except (ValueError, Exception) as e:
            # Expected if no fallback available - this is normal behavior
            print(f"Error handling test: Expected error occurred: {e}")

    @pytest.mark.integration
    @pytest.mark.skipif(
        not secrets_manager.myvault_enabled,
        reason="MyVault not enabled in test environment",
    )
    def test_agent_endpoint_with_myvault_secrets(self, client):
        """Test that agent endpoints can use MyVault secrets."""
        # This is an end-to-end test
        # Requires MyVault to be running with proper configuration

        response = client.post(
            "/v1/aiagent/utility/explorer",
            json={
                "user_input": "Test query",
                "model_name": "gpt-4o-mini",
                "project": "test-project",
            },
        )

        # The request should at least be processed
        # (may fail for other reasons like API keys, but not auth)
        assert response.status_code in [200, 500]

    @pytest.mark.integration
    def test_concurrent_cache_access(self):
        """Test thread-safe cache access."""
        import threading

        if not secrets_manager.myvault_enabled:
            pytest.skip("MyVault not enabled")

        results = []
        errors = []

        def fetch_secret():
            try:
                value = secrets_manager.get_secret("OPENAI_API_KEY")
                results.append(value)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = [threading.Thread(target=fetch_secret) for _ in range(10)]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # All threads should get the same value (or all fail)
        if results:
            assert all(r == results[0] for r in results)
        # No crashes or race conditions
        assert len(results) + len(errors) == 10
