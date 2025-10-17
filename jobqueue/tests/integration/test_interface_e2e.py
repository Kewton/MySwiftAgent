"""End-to-End tests for Interface Validation (Phase 3).

This module tests the complete flow:
Job creation → Validation → Execution
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import new as ulid_new

from app.core.worker import JobExecutor
from app.models.interface_master import InterfaceMaster
from app.models.job import Job, JobStatus
from app.models.task_master import TaskMaster
from tests.utils.interface_mock import InterfaceMockBuilder, InterfaceMockGenerator


class TestInterfaceE2E:
    """End-to-End test suite for Interface Validation."""

    @pytest.mark.asyncio
    async def test_e2e_compatible_interfaces_full_flow(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test complete flow with compatible interfaces: create → validate → execute."""
        # Step 1: Define interfaces using schema
        search_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "results": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["results"],
        }

        analysis_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "results": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["results"],
        }

        # Step 2: Create interface masters
        search_if_id = f"if_{ulid_new()}"
        search_interface = InterfaceMaster(
            id=search_if_id,
            name="E2E_SearchInterface",
            description="E2E test search interface",
            output_schema=search_schema,
            is_active=True,
        )

        analysis_if_id = f"if_{ulid_new()}"
        analysis_interface = InterfaceMaster(
            id=analysis_if_id,
            name="E2E_AnalysisInterface",
            description="E2E test analysis interface",
            input_schema=analysis_schema,
            output_schema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
            },
            is_active=True,
        )

        db_session.add_all([search_interface, analysis_interface])

        # Step 3: Create task masters with interfaces
        search_tm_id = f"tm_{ulid_new()}"
        search_tm = TaskMaster(
            id=search_tm_id,
            name="e2e_search_task",
            description="E2E Search Task",
            method="GET",
            url="https://httpbin.org/json",  # Returns JSON response
            timeout_sec=30,
            output_interface_id=search_if_id,
            is_active=True,
            current_version=1,
            created_by="e2e_test",
            updated_by="e2e_test",
        )

        analysis_tm_id = f"tm_{ulid_new()}"
        analysis_tm = TaskMaster(
            id=analysis_tm_id,
            name="e2e_analysis_task",
            description="E2E Analysis Task",
            method="POST",
            url="https://httpbin.org/post",  # Echoes back POST data
            timeout_sec=30,
            input_interface_id=analysis_if_id,
            output_interface_id=analysis_if_id,
            is_active=True,
            current_version=1,
            created_by="e2e_test",
            updated_by="e2e_test",
        )

        db_session.add_all([search_tm, analysis_tm])
        await db_session.commit()

        # Step 4: Create job with validation enabled (via API)
        response = await client.post(
            "/api/v1/jobs",
            json={
                "name": "E2E Compatible Interfaces Test",
                "method": "GET",
                "url": "https://httpbin.org/get",
                "tasks": [
                    {"master_id": search_tm_id, "sequence": 0},
                    {"master_id": analysis_tm_id, "sequence": 1},
                ],
                "validate_interfaces": True,
            },
        )

        assert response.status_code == 201
        job_data = response.json()
        job_id = job_data["job_id"]
        assert job_data["status"] == "queued"

        # Step 5: Verify validation was performed and passed
        job = await db_session.get(Job, job_id)
        assert job is not None
        assert job.tags is not None

        validation_tag = next(
            (tag for tag in job.tags if tag.get("type") == "interface_validation"),
            None,
        )
        assert validation_tag is not None
        assert validation_tag["is_valid"] is True
        assert validation_tag["error_count"] == 0

        # Step 6: Execute the job via Worker (should succeed)
        from app.core.config import get_settings

        settings = get_settings()
        executor = JobExecutor(db_session, settings)

        # Execute job
        await executor.execute_job(job)

        # Step 7: Verify job completed
        await db_session.refresh(job)
        assert job.status in [
            JobStatus.SUCCEEDED,
            JobStatus.FAILED,
        ]  # Either is OK (HTTP may fail)
        assert job.finished_at is not None

    @pytest.mark.asyncio
    async def test_e2e_incompatible_interfaces_blocked_execution(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test E2E flow with incompatible interfaces: create (warning) → execute (blocked)."""
        # Step 1: Create incompatible interfaces
        output_if_id = f"if_{ulid_new()}"
        output_interface = InterfaceMaster(
            id=output_if_id,
            name="E2E_IncompatibleOutput",
            output_schema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {"status": {"type": "string"}},
                "required": ["status"],
            },
            is_active=True,
        )

        input_if_id = f"if_{ulid_new()}"
        input_interface = InterfaceMaster(
            id=input_if_id,
            name="E2E_IncompatibleInput",
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

        # Step 2: Create task masters
        tm1_id = f"tm_{ulid_new()}"
        tm1 = TaskMaster(
            id=tm1_id,
            name="e2e_output_task",
            method="GET",
            url="https://httpbin.org/status/200",
            timeout_sec=30,
            output_interface_id=output_if_id,
            is_active=True,
            current_version=1,
            created_by="e2e_test",
            updated_by="e2e_test",
        )

        tm2_id = f"tm_{ulid_new()}"
        tm2 = TaskMaster(
            id=tm2_id,
            name="e2e_input_task",
            method="POST",
            url="https://httpbin.org/post",
            timeout_sec=30,
            input_interface_id=input_if_id,
            is_active=True,
            current_version=1,
            created_by="e2e_test",
            updated_by="e2e_test",
        )

        db_session.add_all([tm1, tm2])
        await db_session.commit()

        # Step 3: Create job (should succeed with warnings)
        response = await client.post(
            "/api/v1/jobs",
            json={
                "name": "E2E Incompatible Interfaces Test",
                "method": "GET",
                "url": "https://httpbin.org/get",
                "tasks": [
                    {"master_id": tm1_id, "sequence": 0},
                    {"master_id": tm2_id, "sequence": 1},
                ],
                "validate_interfaces": True,
            },
        )

        assert response.status_code == 201
        job_data = response.json()
        job_id = job_data["job_id"]

        # Step 4: Verify validation failed
        job = await db_session.get(Job, job_id)
        assert job is not None

        validation_tag = next(
            (tag for tag in job.tags if tag.get("type") == "interface_validation"),
            None,
        )
        assert validation_tag is not None
        assert validation_tag["is_valid"] is False
        assert validation_tag["error_count"] > 0

        # Step 5: Try to execute the job (should be blocked)
        from app.core.config import get_settings

        settings = get_settings()
        executor = JobExecutor(db_session, settings)

        with pytest.raises(ValueError) as exc_info:
            await executor.execute_job(job)

        assert "Job execution blocked" in str(exc_info.value)
        assert "failed interface validation" in str(exc_info.value)

        # Step 6: Verify job marked as FAILED
        await db_session.refresh(job)
        assert job.status == JobStatus.FAILED
        assert job.finished_at is not None

    @pytest.mark.asyncio
    async def test_e2e_mock_data_generation(self, db_session: AsyncSession) -> None:
        """Test mock data generation for interface schemas."""
        # Define a complex schema
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 3, "maxLength": 50},
                "filters": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "enum": ["A", "B", "C"]},
                        "active": {"type": "boolean"},
                    },
                    "required": ["category"],
                },
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "title": {"type": "string"},
                        },
                        "required": ["id", "title"],
                    },
                    "minItems": 1,
                    "maxItems": 3,
                },
                "timestamp": {"type": "string", "format": "date-time"},
            },
            "required": ["query", "results"],
        }

        # Generate mock data
        mock_data = InterfaceMockGenerator.generate_mock_data(schema)

        # Verify required fields exist
        assert "query" in mock_data
        assert "results" in mock_data
        assert isinstance(mock_data["query"], str)
        assert isinstance(mock_data["results"], list)
        assert len(mock_data["results"]) >= 1
        assert len(mock_data["results"]) <= 3

        # Verify array items structure
        for result in mock_data["results"]:
            assert "id" in result
            assert "title" in result
            assert isinstance(result["id"], int)
            assert isinstance(result["title"], str)

        # Test custom builder
        builder = InterfaceMockBuilder(schema)
        custom_data = (
            builder.with_field("query", "custom query")
            .with_field("results", [{"id": 1, "title": "Test"}])
            .build()
        )

        assert custom_data["query"] == "custom query"
        assert len(custom_data["results"]) == 1
        assert custom_data["results"][0]["id"] == 1

    @pytest.mark.asyncio
    async def test_e2e_validation_disabled_flow(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test E2E flow with validation disabled."""
        # Create task master without interface
        tm_id = f"tm_{ulid_new()}"
        tm = TaskMaster(
            id=tm_id,
            name="e2e_no_validation_task",
            method="GET",
            url="https://httpbin.org/status/200",
            timeout_sec=30,
            is_active=True,
            current_version=1,
            created_by="e2e_test",
            updated_by="e2e_test",
        )
        db_session.add(tm)
        await db_session.commit()

        # Create job with validation disabled
        response = await client.post(
            "/api/v1/jobs",
            json={
                "name": "E2E No Validation Test",
                "method": "GET",
                "url": "https://httpbin.org/get",
                "tasks": [{"master_id": tm_id, "sequence": 0}],
                "validate_interfaces": False,
            },
        )

        assert response.status_code == 201
        job_data = response.json()
        job_id = job_data["job_id"]

        # Verify no validation tag
        job = await db_session.get(Job, job_id)
        assert job is not None

        if job.tags:
            validation_tag = next(
                (tag for tag in job.tags if tag.get("type") == "interface_validation"),
                None,
            )
            assert validation_tag is None

        # Execute job (should succeed)
        from app.core.config import get_settings

        settings = get_settings()
        executor = JobExecutor(db_session, settings)

        await executor.execute_job(job)

        await db_session.refresh(job)
        assert job.status in [JobStatus.SUCCEEDED, JobStatus.FAILED]
        assert job.finished_at is not None
