from fastapi import Depends

from ..services.job_service import JobService, job_service


def get_job_service() -> JobService:
    """ジョブサービスの依存性注入"""
    return job_service