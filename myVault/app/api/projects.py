"""Project management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_service
from app.core.database import get_db
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate

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
    """Register a new project scope."""
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
