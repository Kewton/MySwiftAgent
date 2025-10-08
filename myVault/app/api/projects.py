"""Project management API endpoints."""

import logging

from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_service
from app.core.crypto import crypto_service
from app.core.database import get_db
from app.models.project import Project
from app.models.secret import Secret
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    db: Session = Depends(get_db),
    current_service: str = Depends(get_current_service),
) -> list[Project]:
    """List all registered projects."""
    projects = db.query(Project).all()
    return projects


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_service: str = Depends(get_current_service),
) -> Project:
    """Register a new project scope and auto-generate Google encryption key."""
    # Check if project already exists
    existing = db.query(Project).filter(Project.name == project.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project '{project.name}' already exists",
        )

    # Create new project
    db_project = Project(
        name=project.name,
        description=project.description,
        created_by=current_service,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    # Auto-generate Google credentials encryption key
    try:
        fernet_key = Fernet.generate_key().decode()
        encrypted_value, iv, tag = crypto_service.encrypt(fernet_key)

        encryption_key_secret = Secret(
            project=project.name,
            path="GOOGLE_CREDS_ENCRYPTION_KEY",
            encrypted_value=encrypted_value,
            encryption_iv=iv,
            encryption_tag=tag,
            version=1,
            updated_by="system",
        )
        db.add(encryption_key_secret)
        db.commit()

        logger.info(
            f"✓ Auto-generated GOOGLE_CREDS_ENCRYPTION_KEY for project: {project.name}"
        )
    except Exception as e:
        logger.error(
            f"⚠ Failed to auto-generate encryption key for project {project.name}: {e}"
        )
        # Non-fatal: project is still created

    return db_project


@router.get("/{project_name}", response_model=ProjectResponse)
async def get_project(
    project_name: str,
    db: Session = Depends(get_db),
    current_service: str = Depends(get_current_service),
) -> Project:
    """Get project by name."""
    project = db.query(Project).filter(Project.name == project_name).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_name}' not found",
        )

    return project


@router.patch("/{project_name}", response_model=ProjectResponse)
async def update_project(
    project_name: str,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db),
    current_service: str = Depends(get_current_service),
) -> Project:
    """Update project description."""
    project = db.query(Project).filter(Project.name == project_name).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_name}' not found",
        )

    # Update description
    if project_update.description is not None:
        project.description = project_update.description

    db.commit()
    db.refresh(project)

    return project


@router.delete("/{project_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_name: str,
    db: Session = Depends(get_db),
    current_service: str = Depends(get_current_service),
) -> None:
    """Delete a project."""
    project = db.query(Project).filter(Project.name == project_name).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_name}' not found",
        )

    # Check if project has any secrets
    if project.secrets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete project '{project_name}' with existing secrets. Delete all secrets first.",
        )

    db.delete(project)
    db.commit()


@router.put("/{project_name}/set-default", response_model=ProjectResponse)
async def set_default_project(
    project_name: str,
    db: Session = Depends(get_db),
    current_service: str = Depends(get_current_service),
) -> Project:
    """Set a project as the default project.

    Only one project can be set as default at a time.
    Setting a new default will automatically unset the previous default.
    """
    # Find the target project
    project = db.query(Project).filter(Project.name == project_name).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_name}' not found",
        )

    # Unset all other defaults
    db.query(Project).filter(Project.id != project.id).update({"is_default": False})

    # Set this project as default
    project.is_default = True

    db.commit()
    db.refresh(project)

    return project
