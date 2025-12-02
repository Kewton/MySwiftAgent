"""Integration tests for API endpoints."""

from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "myVault"}


def test_root_endpoint(client: TestClient) -> None:
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "myVault" in data["message"]


def test_authentication_required(client: TestClient) -> None:
    """Test that authentication is required for API endpoints."""
    response = client.get("/api/projects")
    assert response.status_code == 401


def test_test_connectivity(client: TestClient, auth_headers: dict[str, str]) -> None:
    """Test connectivity endpoint."""
    response = client.post("/api/secrets/test", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "test-service" in data["message"]


def test_create_project(client: TestClient, auth_headers: dict[str, str]) -> None:
    """Test project creation."""
    response = client.post(
        "/api/projects",
        json={"name": "test-project", "description": "Test description"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test-project"
    assert data["description"] == "Test description"
    assert data["created_by"] == "test-service"


def test_list_projects(client: TestClient, auth_headers: dict[str, str]) -> None:
    """Test listing projects."""
    # Create a project first
    client.post(
        "/api/projects",
        json={"name": "project1", "description": "Description 1"},
        headers=auth_headers,
    )

    # List projects
    response = client.get("/api/projects", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(p["name"] == "project1" for p in data)


def test_create_secret(client: TestClient, auth_headers: dict[str, str]) -> None:
    """Test secret creation."""
    response = client.post(
        "/api/secrets",
        json={
            "project": "test",
            "path": "dev/api-key",
            "value": "my-secret-value-123",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["project"] == "test"
    assert data["path"] == "dev/api-key"
    assert data["value"] == "my-secret-value-123"
    assert data["version"] == 1
    assert data["updated_by"] == "test-service"


def test_get_secret(client: TestClient, auth_headers: dict[str, str]) -> None:
    """Test retrieving a secret."""
    # Create secret
    client.post(
        "/api/secrets",
        json={"project": "test", "path": "prod/db-password", "value": "secret123"},
        headers=auth_headers,
    )

    # Get secret
    response = client.get("/api/secrets/test/prod/db-password", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == "secret123"


def test_update_secret(client: TestClient, auth_headers: dict[str, str]) -> None:
    """Test updating a secret."""
    # Create secret
    client.post(
        "/api/secrets",
        json={"project": "test", "path": "staging/token", "value": "old-token"},
        headers=auth_headers,
    )

    # Update secret
    response = client.patch(
        "/api/secrets/test/staging/token",
        json={"value": "new-token-456"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == "new-token-456"
    assert data["version"] == 2  # Version incremented


def test_delete_secret(client: TestClient, auth_headers: dict[str, str]) -> None:
    """Test deleting a secret."""
    # Create secret
    client.post(
        "/api/secrets",
        json={"project": "test", "path": "temp/data", "value": "temporary"},
        headers=auth_headers,
    )

    # Delete secret
    response = client.delete("/api/secrets/test/temp/data", headers=auth_headers)
    assert response.status_code == 204

    # Verify deleted
    response = client.get("/api/secrets/test/temp/data", headers=auth_headers)
    assert response.status_code == 404


def test_access_control(client: TestClient) -> None:
    """Test that prefix-based access control works."""
    # test-service has access to "project:test/" and "common/"
    headers_test = {"X-Service": "test-service", "X-Token": "test-token-123"}

    # Create secret under allowed prefix
    response = client.post(
        "/api/secrets",
        json={"project": "test", "path": "dev/key", "value": "allowed"},
        headers=headers_test,
    )
    assert response.status_code == 201

    # Try to create secret under disallowed prefix
    response = client.post(
        "/api/secrets",
        json={"project": "other", "path": "dev/key", "value": "forbidden"},
        headers=headers_test,
    )
    assert response.status_code == 403
