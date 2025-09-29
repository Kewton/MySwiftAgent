from typing import Any

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class JobExecutionORM(Base):  # type: ignore
    """ジョブ実行履歴テーブル"""

    __tablename__ = "job_executions"

    execution_id = Column(String(36), primary_key=True)
    job_id = Column(String(255), nullable=False, index=True)
    started_at = Column(DateTime, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False, index=True)  # "running", "completed", "failed"
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    http_status_code = Column(Integer, nullable=True)
    response_size = Column(Integer, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換"""
        return {
            "execution_id": self.execution_id,
            "job_id": self.job_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "result": self.result,
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
            "http_status_code": self.http_status_code,
            "response_size": self.response_size,
        }
