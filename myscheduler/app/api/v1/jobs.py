from fastapi import APIRouter, Depends, HTTPException

from ...repositories.execution_repository import execution_repository
from ...schemas.job import (
    JobCreateRequest,
    JobDetail,
    JobListResponse,
    JobResponse,
)
from ...services.job_service import JobService
from ..deps import get_job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/", response_model=JobResponse)
@router.post("", response_model=JobResponse)  # 末尾スラッシュなしのバージョンも追加
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
@router.get("", response_model=JobListResponse)  # 末尾スラッシュなしのバージョンも追加
async def list_jobs(
    job_service: JobService = Depends(get_job_service),
) -> JobListResponse:
    """ジョブ一覧を取得"""
    try:
        jobs = await job_service.list_jobs()
        return JobListResponse(jobs=jobs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{job_id}", response_model=JobDetail)
async def get_job(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
) -> JobDetail:
    """ジョブ詳細を取得"""
    try:
        return await job_service.get_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
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


@router.post("/{job_id}/trigger", response_model=JobResponse)
async def trigger_job(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    """ジョブを即座に実行"""
    try:
        return await job_service.trigger_job(job_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found") from e


@router.get("/{job_id}/executions")
async def get_job_executions(
    job_id: str,
    limit: int = 50,
):
    """ジョブの実行履歴を取得"""
    try:
        executions = execution_repository.get_executions_by_job_id(job_id, limit)
        return {
            "job_id": job_id,
            "executions": executions,
            "count": len(executions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get executions for job {job_id}") from e


@router.get("/executions/recent")
async def get_recent_executions(limit: int = 100):
    """最近の実行履歴を取得"""
    try:
        executions = execution_repository.get_recent_executions(limit)
        return {
            "executions": executions,
            "count": len(executions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get recent executions") from e
