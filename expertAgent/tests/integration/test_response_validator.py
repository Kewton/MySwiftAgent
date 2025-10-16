"""Integration tests for ResponseValidatorMiddleware."""

import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

from app.middleware.response_validator import ResponseValidatorMiddleware


@pytest.fixture
def app_with_middleware():
    """Create test FastAPI app with ResponseValidatorMiddleware."""
    app = FastAPI()

    # Add middleware with force_json_paths
    app.add_middleware(
        ResponseValidatorMiddleware, force_json_paths=["/v1/aiagent", "/v1/utility"]
    )

    @app.get("/v1/aiagent/test")
    def test_aiagent():
        """Test endpoint that should be forced to JSON."""
        return Response(content="Plain text response", media_type="text/plain")

    @app.get("/v1/aiagent/json")
    def test_aiagent_json():
        """Test endpoint that returns JSON."""
        return {"result": "JSON response"}

    @app.get("/v1/aiagent/html")
    def test_aiagent_html():
        """Test endpoint that returns HTML."""
        return Response(
            content="<html><body>HTML</body></html>", media_type="text/html"
        )

    @app.get("/v1/utility/test")
    def test_utility():
        """Test utility endpoint."""
        return Response(content="Utility text", media_type="text/plain")

    @app.get("/other/endpoint")
    def test_other():
        """Test endpoint not in force_json_paths."""
        return Response(content="Plain text", media_type="text/plain")

    @app.get("/v1/aiagent/invalid_utf8")
    def test_invalid_utf8():
        """Test endpoint with invalid UTF-8."""
        return Response(content=b"\x80\x81\x82", media_type="application/octet-stream")

    return app


class TestResponseValidatorMiddleware:
    """Test ResponseValidatorMiddleware."""

    def test_plain_text_converted_to_json(self, app_with_middleware):
        """Test that plain text is converted to JSON."""
        client = TestClient(app_with_middleware)
        response = client.get("/v1/aiagent/test")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert data["detail"] == "Non-JSON response was converted to JSON"
        assert data["original_content_type"] == "text/plain; charset=utf-8"
        assert "Plain text response" in data["original_content"]
        assert data["is_json_guaranteed"] is True
        assert data["middleware_layer"] == "response_validator"

    def test_json_response_unchanged(self, app_with_middleware):
        """Test that JSON response is not modified."""
        client = TestClient(app_with_middleware)
        response = client.get("/v1/aiagent/json")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert data["result"] == "JSON response"

    def test_html_converted_to_json(self, app_with_middleware):
        """Test that HTML is converted to JSON."""
        client = TestClient(app_with_middleware)
        response = client.get("/v1/aiagent/html")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert data["detail"] == "Non-JSON response was converted to JSON"
        assert data["original_content_type"] == "text/html; charset=utf-8"
        assert "<html><body>HTML</body></html>" in data["original_content"]

    def test_utility_endpoint_converted(self, app_with_middleware):
        """Test that utility endpoint text is converted to JSON."""
        client = TestClient(app_with_middleware)
        response = client.get("/v1/utility/test")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert data["detail"] == "Non-JSON response was converted to JSON"
        assert "Utility text" in data["original_content"]

    def test_non_force_json_path_unchanged(self, app_with_middleware):
        """Test that paths not in force_json_paths are unchanged."""
        client = TestClient(app_with_middleware)
        response = client.get("/other/endpoint")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        assert response.text == "Plain text"

    def test_invalid_utf8_handled(self, app_with_middleware):
        """Test that invalid UTF-8 is handled gracefully."""
        client = TestClient(app_with_middleware)
        response = client.get("/v1/aiagent/invalid_utf8")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert data["detail"] == "Non-JSON response was converted to JSON"
        assert data["original_content_type"] == "application/octet-stream"
        # Content should be replaced with replacement characters
        assert "original_content" in data


class TestResponseValidatorNoForcePaths:
    """Test ResponseValidatorMiddleware without force_json_paths."""

    def test_no_force_json_paths(self):
        """Test middleware with empty force_json_paths."""
        app = FastAPI()
        app.add_middleware(ResponseValidatorMiddleware, force_json_paths=[])

        @app.get("/test")
        def test_endpoint():
            return Response(content="Plain text", media_type="text/plain")

        client = TestClient(app)
        response = client.get("/test")

        # Should not be converted because force_json_paths is empty
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        assert response.text == "Plain text"
