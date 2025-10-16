"""API v1 router."""

from fastapi import APIRouter

from app.api.v1.job_master_versions import router as job_master_versions_router
from app.api.v1.job_masters import router as job_masters_router
from app.api.v1.jobs import router as jobs_router

api_router = APIRouter()

api_router.include_router(jobs_router, tags=["jobs"])
api_router.include_router(job_masters_router, tags=["job-masters"])
api_router.include_router(job_master_versions_router, tags=["job-master-versions"])
