"""Version management service for job masters."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.models.job_master import JobMaster
from app.models.job_master_version import JobMasterVersion


class VersionManager:
    """Service for managing job master versions."""

    # Fields that require version increment when changed
    VERSION_CRITICAL_FIELDS = {
        "method",
        "url",
        "headers",
        "params",
        "body",
        "timeout_sec",
        "max_attempts",
        "backoff_strategy",
        "backoff_seconds",
        "ttl_seconds",
    }

    @staticmethod
    async def should_create_new_version(
        db: AsyncSession,
        master: JobMaster,
        update_data: dict[str, Any],
    ) -> tuple[bool, str]:
        """
        Determine if a new version should be created.

        Returns:
            (should_version, reason)
        """
        # Check if any critical fields changed
        has_critical_change = any(
            field in update_data and getattr(master, field) != update_data[field]
            for field in VersionManager.VERSION_CRITICAL_FIELDS
        )

        if not has_critical_change:
            return False, "重要フィールドに変更がないため、バージョンアップ不要"

        # Check if any jobs exist for this master
        job_count = await db.scalar(
            select(func.count(Job.id)).where(Job.master_id == master.id)
        )

        if job_count == 0:
            return False, "ジョブ実行履歴が存在しないため、バージョンアップ不要"

        changed_fields = [
            field
            for field in VersionManager.VERSION_CRITICAL_FIELDS
            if field in update_data and getattr(master, field) != update_data[field]
        ]

        return (
            True,
            f"ジョブ実行履歴が存在し、{', '.join(changed_fields)} が変更されたため自動バージョンアップ",
        )

    @staticmethod
    async def save_current_version(
        db: AsyncSession,
        master: JobMaster,
        change_reason: str | None = None,
    ) -> JobMasterVersion:
        """
        Save current master configuration as a version.
        """
        version_entry = JobMasterVersion(
            master_id=master.id,
            version=master.current_version,
            name=master.name,
            method=master.method,
            url=master.url,
            headers=master.headers,
            params=master.params,
            body=master.body,
            timeout_sec=master.timeout_sec,
            max_attempts=master.max_attempts,
            backoff_strategy=master.backoff_strategy.value
            if hasattr(master.backoff_strategy, "value")
            else master.backoff_strategy,
            backoff_seconds=int(master.backoff_seconds),
            ttl_seconds=master.ttl_seconds,
            tags=master.tags,
            created_at=datetime.now(UTC),
            created_by=None,  # TODO: Add authentication
            change_reason=change_reason,
        )

        db.add(version_entry)
        await db.flush()
        return version_entry

    @staticmethod
    async def get_version_history(
        db: AsyncSession,
        master_id: str,
    ) -> list[JobMasterVersion]:
        """
        Get all version history for a master.
        """
        result = await db.scalars(
            select(JobMasterVersion)
            .where(JobMasterVersion.master_id == master_id)
            .order_by(desc(JobMasterVersion.version))
        )
        return list(result.all())

    @staticmethod
    async def get_version(
        db: AsyncSession,
        master_id: str,
        version: int,
    ) -> JobMasterVersion | None:
        """
        Get a specific version of a master.
        """
        result = await db.scalar(
            select(JobMasterVersion).where(
                JobMasterVersion.master_id == master_id,
                JobMasterVersion.version == version,
            )
        )
        return result

    @staticmethod
    def compare_versions(
        prev_version: JobMasterVersion | None,
        current_version: JobMasterVersion,
    ) -> list[str]:
        """
        Compare two versions and return list of changed fields.
        """
        if prev_version is None:
            return []

        changed_fields = []
        for field in VersionManager.VERSION_CRITICAL_FIELDS:
            prev_value = getattr(prev_version, field)
            curr_value = getattr(current_version, field)
            if prev_value != curr_value:
                changed_fields.append(field)

        return changed_fields
