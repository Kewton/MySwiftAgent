"""Integration tests for Job Interface Validation API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import new as ulid_new

from app.models.interface_master import InterfaceMaster
from app.models.job import Job, JobStatus
from app.models.task import Task, TaskStatus
from app.models.task_master import TaskMaster


class TestJobInterfaceValidation:
    """Test suite for Job Interface Validation API endpoints."""

    @pytest.mark.asyncio
    async def test_validate_compatible_interfaces(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test validation succeeds with compatible interfaces."""
        # Create interfaces
        search_interface_id = f"if_{ulid_new()}"
        search_interface = InterfaceMaster(
            id=search_interface_id,
            name="SearchResultInterface",
            description="Search results",
            input_schema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            output_schema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {
                    "search_results": {
                        "type": "array",
                        "items": {"type": "object"},
                    },
                    "query": {"type": "string"},
                },
                "required": ["search_results"],
            },
            is_active=True,
        )

        analysis_interface_id = f"if_{ulid_new()}"
        analysis_interface = InterfaceMaster(
            id=analysis_interface_id,
            name="AnalysisInterface",
            description="Analysis input/output",
            input_schema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {
                    "search_results": {
                        "type": "array",
                        "items": {"type": "object"},
                    }
                },
                "required": ["search_results"],
            },
            output_schema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
            },
            is_active=True,
        )

        db_session.add_all([search_interface, analysis_interface])

        # Create task masters
        search_master_id = f"tm_{ulid_new()}"
        search_master = TaskMaster(
            id=search_master_id,
            name="test_search",
            description="Search task",
            method="GET",
            url="https://api.example.com/search",
            timeout_sec=30,
            output_interface_id=search_interface_id,
            is_active=True,
            current_version=1,
            created_by="test",
            updated_by="test",
        )

        analyzer_master_id = f"tm_{ulid_new()}"
        analyzer_master = TaskMaster(
            id=analyzer_master_id,
            name="test_analyzer",
            description="Analysis task",
            method="POST",
            url="https://api.example.com/analyze",
            timeout_sec=30,
            input_interface_id=analysis_interface_id,
            output_interface_id=analysis_interface_id,
            is_active=True,
            current_version=1,
            created_by="test",
            updated_by="test",
        )

        db_session.add_all([search_master, analyzer_master])

        # Create job with tasks
        job_id = f"j_{ulid_new()}"
        job = Job(
            id=job_id,
            name="Compatible Interface Test",
            status=JobStatus.QUEUED,
            method="GET",
            url="https://api.example.com/test",
            timeout_sec=30,
        )
        db_session.add(job)

        task1_id = f"t_{ulid_new()}"
        task1 = Task(
            id=task1_id,
            job_id=job_id,
            master_id=search_master_id,
            order=0,
            status=TaskStatus.QUEUED,
        )

        task2_id = f"t_{ulid_new()}"
        task2 = Task(
            id=task2_id,
            job_id=job_id,
            master_id=analyzer_master_id,
            order=1,
            status=TaskStatus.QUEUED,
        )

        db_session.add_all([task1, task2])
        await db_session.commit()

        # Validate interfaces
        response = await client.post(f"/api/v1/jobs/{job_id}/validate-interfaces")
        assert response.status_code == 200
        data = response.json()

        assert data["is_valid"] is True
        assert len(data["errors"]) == 0
        assert len(data["task_interfaces"]) == 2
        assert len(data["compatibility_checks"]) == 1

        # Check task interfaces
        assert data["task_interfaces"][0]["task_order"] == 0
        assert data["task_interfaces"][0]["task_master_name"] == "test_search"
        assert data["task_interfaces"][0]["output_interface"] == "SearchResultInterface"

        assert data["task_interfaces"][1]["task_order"] == 1
        assert data["task_interfaces"][1]["task_master_name"] == "test_analyzer"
        assert data["task_interfaces"][1]["input_interface"] == "AnalysisInterface"

        # Check compatibility check
        compat_check = data["compatibility_checks"][0]
        assert compat_check["task_a_order"] == 0
        assert compat_check["task_b_order"] == 1
        assert compat_check["is_compatible"] is True
        assert len(compat_check["missing_properties"]) == 0

    @pytest.mark.asyncio
    async def test_validate_incompatible_interfaces(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test validation fails with incompatible interfaces."""
        # Create interfaces with incompatible schemas
        output_interface_id = f"if_{ulid_new()}"
        output_interface = InterfaceMaster(
            id=output_interface_id,
            name="OutputInterface",
            description="Output without required properties",
            output_schema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            },
            is_active=True,
        )

        input_interface_id = f"if_{ulid_new()}"
        input_interface = InterfaceMaster(
            id=input_interface_id,
            name="InputInterface",
            description="Input requiring missing properties",
            input_schema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {
                    "data": {"type": "object"},
                    "metadata": {"type": "object"},
                },
                "required": ["data", "metadata"],
            },
            is_active=True,
        )

        db_session.add_all([output_interface, input_interface])

        # Create task masters
        task1_master_id = f"tm_{ulid_new()}"
        task1_master = TaskMaster(
            id=task1_master_id,
            name="task1",
            method="GET",
            url="https://api.example.com/task1",
            timeout_sec=30,
            output_interface_id=output_interface_id,
            is_active=True,
            current_version=1,
            created_by="test",
            updated_by="test",
        )

        task2_master_id = f"tm_{ulid_new()}"
        task2_master = TaskMaster(
            id=task2_master_id,
            name="task2",
            method="POST",
            url="https://api.example.com/task2",
            timeout_sec=30,
            input_interface_id=input_interface_id,
            is_active=True,
            current_version=1,
            created_by="test",
            updated_by="test",
        )

        db_session.add_all([task1_master, task2_master])

        # Create job with tasks
        job_id = f"j_{ulid_new()}"
        job = Job(
            id=job_id,
            name="Incompatible Interface Test",
            status=JobStatus.QUEUED,
            method="GET",
            url="https://api.example.com/test",
            timeout_sec=30,
        )
        db_session.add(job)

        task1_id = f"t_{ulid_new()}"
        task1 = Task(
            id=task1_id,
            job_id=job_id,
            master_id=task1_master_id,
            order=0,
            status=TaskStatus.QUEUED,
        )

        task2_id = f"t_{ulid_new()}"
        task2 = Task(
            id=task2_id,
            job_id=job_id,
            master_id=task2_master_id,
            order=1,
            status=TaskStatus.QUEUED,
        )

        db_session.add_all([task1, task2])
        await db_session.commit()

        # Validate interfaces
        response = await client.post(f"/api/v1/jobs/{job_id}/validate-interfaces")
        assert response.status_code == 200
        data = response.json()

        assert data["is_valid"] is False
        assert len(data["errors"]) > 0

        # Check that errors mention missing properties
        error_text = " ".join(data["errors"])
        assert "data" in error_text
        assert "metadata" in error_text

        # Check compatibility check result
        compat_check = data["compatibility_checks"][0]
        assert compat_check["is_compatible"] is False
        assert len(compat_check["missing_properties"]) == 2

    @pytest.mark.asyncio
    async def test_validate_missing_interfaces(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test validation with tasks that have no interface definitions."""
        # Create task masters without interfaces
        task1_master_id = f"tm_{ulid_new()}"
        task1_master = TaskMaster(
            id=task1_master_id,
            name="task_no_interface_1",
            method="GET",
            url="https://api.example.com/task1",
            timeout_sec=30,
            is_active=True,
            current_version=1,
            created_by="test",
            updated_by="test",
        )

        task2_master_id = f"tm_{ulid_new()}"
        task2_master = TaskMaster(
            id=task2_master_id,
            name="task_no_interface_2",
            method="POST",
            url="https://api.example.com/task2",
            timeout_sec=30,
            is_active=True,
            current_version=1,
            created_by="test",
            updated_by="test",
        )

        db_session.add_all([task1_master, task2_master])

        # Create job with tasks
        job_id = f"j_{ulid_new()}"
        job = Job(
            id=job_id,
            name="Missing Interface Test",
            status=JobStatus.QUEUED,
            method="GET",
            url="https://api.example.com/test",
            timeout_sec=30,
        )
        db_session.add(job)

        task1_id = f"t_{ulid_new()}"
        task1 = Task(
            id=task1_id,
            job_id=job_id,
            master_id=task1_master_id,
            order=0,
            status=TaskStatus.QUEUED,
        )

        task2_id = f"t_{ulid_new()}"
        task2 = Task(
            id=task2_id,
            job_id=job_id,
            master_id=task2_master_id,
            order=1,
            status=TaskStatus.QUEUED,
        )

        db_session.add_all([task1, task2])
        await db_session.commit()

        # Validate interfaces
        response = await client.post(f"/api/v1/jobs/{job_id}/validate-interfaces")
        assert response.status_code == 200
        data = response.json()

        # Should return warnings but validation itself succeeds
        # (no interfaces means no incompatibility can be detected)
        assert len(data["warnings"]) > 0

        # Check compatibility check result (should be None/unknown)
        compat_check = data["compatibility_checks"][0]
        assert compat_check["is_compatible"] is None

    @pytest.mark.asyncio
    async def test_validate_single_task_job(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test validation with single-task job (no compatibility check needed)."""
        # Create task master
        task_master_id = f"tm_{ulid_new()}"
        task_master = TaskMaster(
            id=task_master_id,
            name="single_task",
            method="GET",
            url="https://api.example.com/task",
            timeout_sec=30,
            is_active=True,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        db_session.add(task_master)

        # Create job with single task
        job_id = f"j_{ulid_new()}"
        job = Job(
            id=job_id,
            name="Single Task Test",
            status=JobStatus.QUEUED,
            method="GET",
            url="https://api.example.com/test",
            timeout_sec=30,
        )
        db_session.add(job)

        task_id = f"t_{ulid_new()}"
        task = Task(
            id=task_id,
            job_id=job_id,
            master_id=task_master_id,
            order=0,
            status=TaskStatus.QUEUED,
        )
        db_session.add(task)
        await db_session.commit()

        # Validate interfaces
        response = await client.post(f"/api/v1/jobs/{job_id}/validate-interfaces")
        assert response.status_code == 200
        data = response.json()

        # Should have warning about single task
        assert len(data["warnings"]) > 0
        assert any("only one task" in w for w in data["warnings"])
        assert len(data["compatibility_checks"]) == 0

    @pytest.mark.asyncio
    async def test_validate_nonexistent_job(self, client: AsyncClient) -> None:
        """Test validation with non-existent job."""
        response = await client.post("/api/v1/jobs/j_nonexistent/validate-interfaces")
        assert response.status_code == 200
        data = response.json()

        assert data["is_valid"] is False
        assert len(data["errors"]) > 0
        assert any("not found" in e for e in data["errors"])

    @pytest.mark.asyncio
    async def test_validate_type_mismatch(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test validation detects type mismatches between interfaces."""
        # Create interfaces with type mismatch
        output_interface_id = f"if_{ulid_new()}"
        output_interface = InterfaceMaster(
            id=output_interface_id,
            name="StringOutputInterface",
            output_schema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
            is_active=True,
        )

        input_interface_id = f"if_{ulid_new()}"
        input_interface = InterfaceMaster(
            id=input_interface_id,
            name="NumberInputInterface",
            input_schema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {"value": {"type": "number"}},
                "required": ["value"],
            },
            is_active=True,
        )

        db_session.add_all([output_interface, input_interface])

        # Create task masters
        task1_master_id = f"tm_{ulid_new()}"
        task1_master = TaskMaster(
            id=task1_master_id,
            name="string_output_task",
            method="GET",
            url="https://api.example.com/task1",
            timeout_sec=30,
            output_interface_id=output_interface_id,
            is_active=True,
            current_version=1,
            created_by="test",
            updated_by="test",
        )

        task2_master_id = f"tm_{ulid_new()}"
        task2_master = TaskMaster(
            id=task2_master_id,
            name="number_input_task",
            method="POST",
            url="https://api.example.com/task2",
            timeout_sec=30,
            input_interface_id=input_interface_id,
            is_active=True,
            current_version=1,
            created_by="test",
            updated_by="test",
        )

        db_session.add_all([task1_master, task2_master])

        # Create job
        job_id = f"j_{ulid_new()}"
        job = Job(
            id=job_id,
            name="Type Mismatch Test",
            status=JobStatus.QUEUED,
            method="GET",
            url="https://api.example.com/test",
            timeout_sec=30,
        )
        db_session.add(job)

        task1_id = f"t_{ulid_new()}"
        task1 = Task(
            id=task1_id,
            job_id=job_id,
            master_id=task1_master_id,
            order=0,
            status=TaskStatus.QUEUED,
        )

        task2_id = f"t_{ulid_new()}"
        task2 = Task(
            id=task2_id,
            job_id=job_id,
            master_id=task2_master_id,
            order=1,
            status=TaskStatus.QUEUED,
        )

        db_session.add_all([task1, task2])
        await db_session.commit()

        # Validate interfaces
        response = await client.post(f"/api/v1/jobs/{job_id}/validate-interfaces")
        assert response.status_code == 200
        data = response.json()

        assert data["is_valid"] is False
        assert len(data["errors"]) > 0

        # Check that errors mention type mismatch
        error_text = " ".join(data["errors"])
        assert "type mismatch" in error_text.lower()
        assert "value" in error_text
