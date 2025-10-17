"""Version management service for task masters."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.models.task_master import TaskMaster
from app.models.task_master_version import TaskMasterVersion


class TaskVersionManager:
    """Service for managing task master versions."""

    # Fields that require version increment when changed
    VERSION_CRITICAL_FIELDS = {
        "method",
        "url",
        "headers",
        "body_template",
        "timeout_sec",
    }

    @staticmethod
    async def should_create_new_version(
        db: AsyncSession,
        master: TaskMaster,
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
            for field in TaskVersionManager.VERSION_CRITICAL_FIELDS
        )

        if not has_critical_change:
            return False, "重要フィールドに変更がないため、バージョンアップ不要"

        # Check if any tasks exist for this master
        task_count = await db.scalar(
            select(func.count(Task.id)).where(Task.master_id == master.id)
        )

        if task_count == 0:
            return False, "タスク実行履歴が存在しないため、バージョンアップ不要"

        changed_fields = [
            field
            for field in TaskVersionManager.VERSION_CRITICAL_FIELDS
            if field in update_data and getattr(master, field) != update_data[field]
        ]

        return (
            True,
            f"タスク実行履歴が存在し、{', '.join(changed_fields)} が変更されたため自動バージョンアップ",
        )

    @staticmethod
    async def save_current_version(
        db: AsyncSession,
        master: TaskMaster,
        change_reason: str | None = None,
    ) -> TaskMasterVersion:
        """
        Save current master configuration as a version.
        """
        version_entry = TaskMasterVersion(
            master_id=master.id,
            version=master.current_version,
            name=master.name,
            description=master.description,
            method=master.method,
            url=master.url,
            headers=master.headers,
            body_template=master.body_template,
            timeout_sec=master.timeout_sec,
            created_at=datetime.now(UTC),
            created_by=master.updated_by or master.created_by,
            change_reason=change_reason,
        )

        db.add(version_entry)
        await db.flush()
        return version_entry

    @staticmethod
    async def get_version_history(
        db: AsyncSession,
        master_id: str,
    ) -> list[TaskMasterVersion]:
        """
        Get all version history for a master.
        """
        result = await db.scalars(
            select(TaskMasterVersion)
            .where(TaskMasterVersion.master_id == master_id)
            .order_by(desc(TaskMasterVersion.version))
        )
        return list(result.all())

    @staticmethod
    async def get_version(
        db: AsyncSession,
        master_id: str,
        version: int,
    ) -> TaskMasterVersion | None:
        """
        Get a specific version of a master.
        """
        result = await db.scalar(
            select(TaskMasterVersion).where(
                TaskMasterVersion.master_id == master_id,
                TaskMasterVersion.version == version,
            )
        )
        return result

    @staticmethod
    def compare_versions(
        prev_version: TaskMasterVersion | None,
        current_version: TaskMasterVersion,
    ) -> list[str]:
        """
        Compare two versions and return list of changed fields.
        """
        if prev_version is None:
            return []

        changed_fields = []
        for field in TaskVersionManager.VERSION_CRITICAL_FIELDS:
            prev_value = getattr(prev_version, field)
            curr_value = getattr(current_version, field)
            if prev_value != curr_value:
                changed_fields.append(field)

        return changed_fields
