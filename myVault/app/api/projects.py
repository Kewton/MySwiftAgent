"""Project management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_service
from app.core.database import get_db
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectResponse

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
