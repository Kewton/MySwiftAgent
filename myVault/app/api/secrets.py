"""Secret management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import auth_service, get_current_service
from app.core.crypto import crypto_service
from app.core.database import get_db
from app.models.secret import Secret
from app.schemas.secret import (
    SecretCreate,
    SecretListItem,
    SecretResponse,
    SecretUpdate,
)

router = APIRouter(prefix="/api/secrets", tags=["secrets"])


@router.get("", response_model=list[SecretListItem])
async def list_secrets(
    project: str | None = Query(None, description="Filter by project"),
    db: Session = Depends(get_db),
    current_service: str = Depends(get_current_service),
) -> list[Secret]:
    """Enumerate secrets (values redacted)."""
    query = db.query(Secret)

    if project:
        query = query.filter(Secret.project == project)

    secrets = query.all()

    # Filter based on RBAC permissions
    allowed_secrets = []
    for secret in secrets:
        resource = f"secret:{secret.project}:{secret.path}"
        # Check list permission
        if auth_service.check_rbac_permission(current_service, "list", resource):
            allowed_secrets.append(secret)

    return allowed_secrets


@router.post("", response_model=SecretResponse, status_code=status.HTTP_201_CREATED)
async def create_secret(
    secret: SecretCreate,
    db: Session = Depends(get_db),
    current_service: str = Depends(get_current_service),
) -> SecretResponse:
    """Create a new secret."""
    # Check RBAC write permission
    resource = f"secret:{secret.project}:{secret.path}"
    if not auth_service.check_rbac_permission(current_service, "write", resource):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Service '{current_service}' does not have 'write' permission for '{resource}'",
        )

    # Check if secret already exists
    existing = (
        db.query(Secret)
        .filter(Secret.project == secret.project, Secret.path == secret.path)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Secret '{resource}' already exists",
        )

    # Encrypt value
    encrypted_value, iv, tag = crypto_service.encrypt(secret.value)

    # Create secret
    db_secret = Secret(
        project=secret.project,
        path=secret.path,
        encrypted_value=encrypted_value,
        encryption_iv=iv,
        encryption_tag=tag,
        version=1,
        updated_by=current_service,
    )
    db.add(db_secret)
    db.commit()
    db.refresh(db_secret)

    # Return with decrypted value
    return SecretResponse(
        id=db_secret.id,
        project=db_secret.project,
        path=db_secret.path,
        value=secret.value,
        version=db_secret.version,
        updated_at=db_secret.updated_at,
        updated_by=db_secret.updated_by,
    )


@router.get("/{project}/{path:path}", response_model=SecretResponse)
async def get_secret(
    project: str,
    path: str,
    db: Session = Depends(get_db),
    current_service: str = Depends(get_current_service),
) -> SecretResponse:
    """Retrieve a secret value."""
    # Check RBAC read permission
    resource = f"secret:{project}:{path}"
    if not auth_service.check_rbac_permission(current_service, "read", resource):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Service '{current_service}' does not have 'read' permission for '{resource}'",
        )

    # Get secret
    db_secret = (
        db.query(Secret)
        .filter(Secret.project == project, Secret.path == path)
        .first()
    )
    if not db_secret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Secret '{resource}' not found",
        )

    # Decrypt value
    try:
        decrypted_value = crypto_service.decrypt(
            db_secret.encrypted_value,
            db_secret.encryption_iv,
            db_secret.encryption_tag,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to decrypt secret: {e}",
        ) from e

    return SecretResponse(
        id=db_secret.id,
        project=db_secret.project,
        path=db_secret.path,
        value=decrypted_value,
        version=db_secret.version,
        updated_at=db_secret.updated_at,
        updated_by=db_secret.updated_by,
    )


@router.patch("/{project}/{path:path}", response_model=SecretResponse)
async def update_secret(
    project: str,
    path: str,
    secret_update: SecretUpdate,
    db: Session = Depends(get_db),
    current_service: str = Depends(get_current_service),
) -> SecretResponse:
    """Rotate/update a secret."""
    # Check RBAC write permission
    resource = f"secret:{project}:{path}"
    if not auth_service.check_rbac_permission(current_service, "write", resource):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Service '{current_service}' does not have 'write' permission for '{resource}'",
        )

    # Get secret
    db_secret = (
        db.query(Secret)
        .filter(Secret.project == project, Secret.path == path)
        .first()
    )
    if not db_secret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Secret '{resource}' not found",
        )

    # Encrypt new value
    encrypted_value, iv, tag = crypto_service.encrypt(secret_update.value)

    # Update secret
    db_secret.encrypted_value = encrypted_value
    db_secret.encryption_iv = iv
    db_secret.encryption_tag = tag
    db_secret.version += 1
    db_secret.updated_by = current_service

    db.commit()
    db.refresh(db_secret)

    return SecretResponse(
        id=db_secret.id,
        project=db_secret.project,
        path=db_secret.path,
        value=secret_update.value,
        version=db_secret.version,
        updated_at=db_secret.updated_at,
        updated_by=db_secret.updated_by,
    )


@router.delete("/{project}/{path:path}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_secret(
    project: str,
    path: str,
    db: Session = Depends(get_db),
    current_service: str = Depends(get_current_service),
) -> None:
    """Remove a secret."""
    # Check RBAC delete permission
    resource = f"secret:{project}:{path}"
    if not auth_service.check_rbac_permission(current_service, "delete", resource):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Service '{current_service}' does not have 'delete' permission for '{resource}'",
        )

    # Get secret
    db_secret = (
        db.query(Secret)
        .filter(Secret.project == project, Secret.path == path)
        .first()
    )
    if not db_secret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Secret '{resource}' not found",
        )

    # Delete secret
    db.delete(db_secret)
    db.commit()


@router.post("/test", status_code=status.HTTP_200_OK)
async def test_connectivity(
    current_service: str = Depends(get_current_service),
) -> dict[str, str]:
    """Validate connectivity and credentials."""
    return {
        "status": "ok",
        "message": f"Authentication successful for service '{current_service}'",
    }
