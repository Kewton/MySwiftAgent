"""Integration tests for Secrets API endpoints."""

from fastapi.testclient import TestClient


def test_list_secrets_empty(client: TestClient, auth_headers: dict[str, str]) -> None:
    """Test listing secrets when database is empty."""
    response = client.get("/api/secrets", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_secrets_with_project_filter(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Test listing secrets filtered by project."""
    # Create secrets in test project (test-service has permission)
    client.post(
        "/api/secrets",
        json={"project": "test", "path": "key1", "value": "value1"},
        headers=auth_headers,
    )
    client.post(
        "/api/secrets",
        json={"project": "test", "path": "key2", "value": "value2"},
        headers=auth_headers,
    )

    # List secrets for test project only
    response = client.get("/api/secrets?project=test", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert all(s["project"] == "test" for s in data)


def test_create_secret_duplicate(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Test creating a duplicate secret returns 409 Conflict."""
    # Create secret
    client.post(
        "/api/secrets",
        json={"project": "test", "path": "duplicate/key", "value": "value1"},
        headers=auth_headers,
    )

    # Try to create duplicate
    response = client.post(
        "/api/secrets",
        json={"project": "test", "path": "duplicate/key", "value": "value2"},
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_get_secret_not_found(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Test getting a non-existent secret returns 404."""
    response = client.get("/api/secrets/test/non-existent/key", headers=auth_headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_update_secret_not_found(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Test updating a non-existent secret returns 404."""
    response = client.patch(
        "/api/secrets/test/non-existent/key",
        json={"value": "new-value"},
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_delete_secret_not_found(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Test deleting a non-existent secret returns 404."""
    response = client.delete(
        "/api/secrets/test/non-existent/key", headers=auth_headers
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_secret_encryption_roundtrip(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Test that secret values are properly encrypted and decrypted."""
    secret_value = "my-super-secret-password-12345"

    # Create secret
    response = client.post(
        "/api/secrets",
        json={"project": "test", "path": "crypto/test", "value": secret_value},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["value"] == secret_value

    # Get secret and verify decryption
    response = client.get("/api/secrets/test/crypto/test", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["value"] == secret_value


def test_secret_version_increment(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Test that secret version increments on update."""
    # Create secret
    response = client.post(
        "/api/secrets",
        json={"project": "test", "path": "version/test", "value": "v1"},
        headers=auth_headers,
    )
    assert response.json()["version"] == 1

    # Update secret multiple times
    response = client.patch(
        "/api/secrets/test/version/test",
        json={"value": "v2"},
        headers=auth_headers,
    )
    assert response.json()["version"] == 2

    response = client.patch(
        "/api/secrets/test/version/test",
        json={"value": "v3"},
        headers=auth_headers,
    )
    assert response.json()["version"] == 3


def test_secret_list_redacted_values(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Test that list endpoint does not return secret values."""
    # Create secret with sensitive value
    client.post(
        "/api/secrets",
        json={"project": "test", "path": "sensitive/api-key", "value": "secret-key"},
        headers=auth_headers,
    )

    # List secrets
    response = client.get("/api/secrets?project=test", headers=auth_headers)
    assert response.status_code == 200
    secrets = response.json()

    # Verify values are not in the response (SecretListItem schema excludes value)
    for secret in secrets:
        assert "value" not in secret
        assert "project" in secret
        assert "path" in secret


def test_secret_updated_by_tracking(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Test that secret tracks who created/updated it."""
    # Create secret
    response = client.post(
        "/api/secrets",
        json={"project": "test", "path": "tracking/test", "value": "initial"},
        headers=auth_headers,
    )
    assert response.json()["updated_by"] == "test-service"

    # Update secret
    response = client.patch(
        "/api/secrets/test/tracking/test",
        json={"value": "updated"},
        headers=auth_headers,
    )
    assert response.json()["updated_by"] == "test-service"


def test_secret_path_with_slashes(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Test that secret paths with multiple slashes work correctly."""
    # Create secret with nested path
    response = client.post(
        "/api/secrets",
        json={
            "project": "test",
            "path": "env/dev/database/password",
            "value": "db-pass-123",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201

    # Get secret with nested path
    response = client.get(
        "/api/secrets/test/env/dev/database/password", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["value"] == "db-pass-123"


def test_rbac_permission_denied(client: TestClient) -> None:
    """Test that RBAC denies access to unauthorized resources."""
    # test-service has access to "project:test/" but not "project:other/"
    test_headers = {"X-Service": "test-service", "X-Token": "test-token-123"}

    # Try to create secret in unauthorized project
    response = client.post(
        "/api/secrets",
        json={"project": "other", "path": "unauthorized/key", "value": "value"},
        headers=test_headers,
    )
    assert response.status_code == 403
    assert "does not have 'write' permission" in response.json()["detail"]


def test_rbac_read_permission_denied(client: TestClient) -> None:
    """Test that RBAC denies read access to unauthorized resources."""
    test_headers = {"X-Service": "test-service", "X-Token": "test-token-123"}
    other_headers = {"X-Service": "other-service", "X-Token": "other-token-456"}

    # Create secret with test-service
    client.post(
        "/api/secrets",
        json={"project": "test", "path": "private/key", "value": "secret"},
        headers=test_headers,
    )

    # Try to read with test-service (should work)
    response = client.get("/api/secrets/test/private/key", headers=test_headers)
    assert response.status_code == 200

    # Try to read with other-service (should fail)
    response = client.get("/api/secrets/test/private/key", headers=other_headers)
    assert response.status_code == 403
    assert "does not have 'read' permission" in response.json()["detail"]


def test_rbac_delete_permission_denied(client: TestClient) -> None:
    """Test that RBAC denies delete access to unauthorized resources."""
    test_headers = {"X-Service": "test-service", "X-Token": "test-token-123"}
    other_headers = {"X-Service": "other-service", "X-Token": "other-token-456"}

    # Create secret with test-service
    client.post(
        "/api/secrets",
        json={"project": "test", "path": "protected/key", "value": "secret"},
        headers=test_headers,
    )

    # Try to delete with other-service (should fail)
    response = client.delete("/api/secrets/test/protected/key", headers=other_headers)
    assert response.status_code == 403
    assert "does not have 'delete' permission" in response.json()["detail"]
