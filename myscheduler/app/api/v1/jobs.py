from fastapi import APIRouter, Depends, HTTPException

from ...schemas.job import (
    JobCreateRequest,
    JobListResponse,
    JobResponse,
)
from ...services.job_service import JobService
from ..deps import get_job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/", response_model=JobResponse)
async def create_job(
    job_request: JobCreateRequest,
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    """ジョブを作成"""
    try:
        return await job_service.create_job(job_request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    job_service: JobService = Depends(get_job_service),
) -> JobListResponse:
    """ジョブ一覧を取得"""
    try:
        jobs = await job_service.list_jobs()
        return JobListResponse(jobs=jobs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{job_id}", response_model=JobResponse)
async def delete_job(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    """ジョブを削除"""
    try:
        return await job_service.delete_job(job_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found") from e


@router.post("/{job_id}/pause", response_model=JobResponse)
async def pause_job(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    """ジョブを一時停止"""
    try:
        return await job_service.pause_job(job_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found") from e


@router.post("/{job_id}/resume", response_model=JobResponse)
async def resume_job(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    """ジョブを再開"""
    try:
        return await job_service.resume_job(job_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found") from e
