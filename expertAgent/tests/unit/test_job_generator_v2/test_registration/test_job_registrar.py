"""Unit tests for JobRegistrarSubWorkflow.

Issue #342 Phase D.3: Tests for job registration sub-workflow.
"""

import pytest

from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
from aiagent.langgraph.jobGeneratorV2.protocols import WorkflowError


class TestJobRegistrarSubWorkflowExists:
    """Test that JobRegistrarSubWorkflow exists and is importable."""

    def test_job_registrar_importable(self):
        """JobRegistrarSubWorkflow should be importable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.job_registrar import (
            JobRegistrarSubWorkflow,
        )

        assert JobRegistrarSubWorkflow is not None

    def test_job_registrar_has_register_job_method(self):
        """JobRegistrarSubWorkflow should have register_job method."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.job_registrar import (
            JobRegistrarSubWorkflow,
        )

        registrar = JobRegistrarSubWorkflow()
        assert hasattr(registrar, "register_job")
        assert callable(registrar.register_job)

    def test_job_registration_result_importable(self):
        """JobRegistrationResult should be importable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.job_registrar import (
            JobRegistrationResult,
        )

        assert JobRegistrationResult is not None


class TestJobRegistrarDataclasses:
    """Test dataclasses defined in job_registrar."""

    def test_job_body_parameter_creation(self):
        """JobBodyParameter should be creatable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.job_registrar import (
            JobBodyParameter,
        )

        param = JobBodyParameter(
            name="query",
            value="test query",
            description="Search query",
        )
        assert param.name == "query"
        assert param.value == "test query"
        assert param.description == "Search query"

    def test_job_body_parameter_default_description(self):
        """JobBodyParameter should have default description."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.job_registrar import (
            JobBodyParameter,
        )

        param = JobBodyParameter(name="query", value="test")
        assert param.description == ""

    def test_job_registration_result_creation(self):
        """JobRegistrationResult should be creatable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.job_registrar import (
            JobRegistrationResult,
        )

        result = JobRegistrationResult(
            job_id="job_123",
            job_name="Test Job",
            status="registered",
            workflow_task_count=3,
            body_parameters=["query", "max_results"],
        )
        assert result.job_id == "job_123"
        assert result.job_name == "Test Job"
        assert result.status == "registered"
        assert result.workflow_task_count == 3
        assert "query" in result.body_parameters

    def test_job_registration_result_defaults(self):
        """JobRegistrationResult should have sensible defaults."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.job_registrar import (
            JobRegistrationResult,
        )

        result = JobRegistrationResult(
            job_id="job_123",
            job_name="Test Job",
        )
        assert result.status == "registered"
        assert result.workflow_task_count == 0
        assert result.body_parameters == []


class TestJobRegistrarRegisterJob:
    """Test JobRegistrarSubWorkflow.register_job() method."""

    @pytest.fixture
    def sample_job_master(self):
        """Create sample JobMasterInfo for testing."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            JobMasterInfo,
        )

        return JobMasterInfo(
            id="jm_test-job-123",
            name="Job: Search and summarize emails",
            method="POST",
            url="http://localhost:8005/api/v1/myagent",
            timeout_sec=300,
        )

    @pytest.fixture
    def mock_context(self) -> ExecutionContext:
        """Create mock execution context."""
        return ExecutionContext(
            job_id="test-job-123",
            user_requirement="Search and summarize emails",
            max_phase_retries=3,
            max_total_retries=5,
        )

    @pytest.mark.asyncio
    async def test_register_job_returns_result(
        self,
        sample_job_master,
        mock_context: ExecutionContext,
    ):
        """register_job should return JobRegistrationResult."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.job_registrar import (
            JobRegistrarSubWorkflow,
            JobRegistrationResult,
        )

        registrar = JobRegistrarSubWorkflow()
        result = await registrar.register_job(
            job_master=sample_job_master,
            body_parameters=None,
            context=mock_context,
        )

        assert isinstance(result, JobRegistrationResult)
        assert result.job_id is not None
        assert "test-job-123" in result.job_id

    @pytest.mark.asyncio
    async def test_register_job_with_parameters(
        self,
        sample_job_master,
        mock_context: ExecutionContext,
    ):
        """register_job should handle body parameters."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.job_registrar import (
            JobBodyParameter,
            JobRegistrarSubWorkflow,
        )

        registrar = JobRegistrarSubWorkflow()
        params = [
            JobBodyParameter(name="query", value="test query"),
            JobBodyParameter(name="max_results", value=10),
        ]

        result = await registrar.register_job(
            job_master=sample_job_master,
            body_parameters=params,
            context=mock_context,
        )

        assert "query" in result.body_parameters
        assert "max_results" in result.body_parameters

    @pytest.mark.asyncio
    async def test_register_job_missing_id_raises_error(
        self,
        mock_context: ExecutionContext,
    ):
        """register_job should raise error for missing job master ID."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.job_registrar import (
            JobRegistrarSubWorkflow,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            JobMasterInfo,
        )

        registrar = JobRegistrarSubWorkflow()
        invalid_job_master = JobMasterInfo(
            id="",  # Empty ID
            name="Test Job",
            method="POST",
            url="http://localhost:8005",
            timeout_sec=300,
        )

        with pytest.raises(WorkflowError) as exc_info:
            await registrar.register_job(
                job_master=invalid_job_master,
                body_parameters=None,
                context=mock_context,
            )

        assert "JobMaster ID is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_register_job_missing_url_raises_error(
        self,
        mock_context: ExecutionContext,
    ):
        """register_job should raise error for missing job master URL."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.job_registrar import (
            JobRegistrarSubWorkflow,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            JobMasterInfo,
        )

        registrar = JobRegistrarSubWorkflow()
        invalid_job_master = JobMasterInfo(
            id="jm_123",
            name="Test Job",
            method="POST",
            url="",  # Empty URL
            timeout_sec=300,
        )

        with pytest.raises(WorkflowError) as exc_info:
            await registrar.register_job(
                job_master=invalid_job_master,
                body_parameters=None,
                context=mock_context,
            )

        assert "JobMaster URL is required" in str(exc_info.value)


class TestJobRegistrarBuildJobBody:
    """Test job body building logic."""

    def test_build_job_body_with_parameters(self):
        """Should build job body from parameters."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.job_registrar import (
            JobBodyParameter,
            JobRegistrarSubWorkflow,
        )

        registrar = JobRegistrarSubWorkflow()
        params = [
            JobBodyParameter(name="query", value="test query"),
            JobBodyParameter(name="max_results", value=10),
        ]

        body = registrar._build_job_body(params)

        assert body is not None
        assert body["query"] == "test query"
        assert body["max_results"] == 10

    def test_build_job_body_empty_parameters(self):
        """Should return None for empty parameters."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.job_registrar import (
            JobRegistrarSubWorkflow,
        )

        registrar = JobRegistrarSubWorkflow()
        body = registrar._build_job_body([])

        assert body is None

    def test_build_job_body_none_parameters(self):
        """Should return None for None parameters."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.job_registrar import (
            JobRegistrarSubWorkflow,
        )

        registrar = JobRegistrarSubWorkflow()
        body = registrar._build_job_body(None)

        assert body is None

    def test_build_job_body_skips_empty_names(self):
        """Should skip parameters with empty names."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.job_registrar import (
            JobBodyParameter,
            JobRegistrarSubWorkflow,
        )

        registrar = JobRegistrarSubWorkflow()
        params = [
            JobBodyParameter(name="", value="should skip"),
            JobBodyParameter(name="valid", value="included"),
        ]

        body = registrar._build_job_body(params)

        assert body is not None
        assert "" not in body
        assert body["valid"] == "included"


class TestBuildJobBodyParameters:
    """Test helper function for building JobBodyParameter list."""

    def test_build_from_dicts(self):
        """Should convert dicts to JobBodyParameter list."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.job_registrar import (
            JobBodyParameter,
            build_job_body_parameters,
        )

        raw_params = [
            {"name": "query", "value": "test", "description": "Search query"},
            {"name": "max_results", "value": 10},
        ]

        params = build_job_body_parameters(raw_params)

        assert len(params) == 2
        assert all(isinstance(p, JobBodyParameter) for p in params)
        assert params[0].name == "query"
        assert params[0].value == "test"
        assert params[0].description == "Search query"

    def test_build_from_empty_list(self):
        """Should return empty list for empty input."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.job_registrar import (
            build_job_body_parameters,
        )

        params = build_job_body_parameters([])

        assert params == []

    def test_build_skips_missing_names(self):
        """Should skip entries without names."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.job_registrar import (
            build_job_body_parameters,
        )

        raw_params = [
            {"value": "no name"},
            {"name": "valid", "value": "included"},
        ]

        params = build_job_body_parameters(raw_params)

        assert len(params) == 1
        assert params[0].name == "valid"


class TestJobRegistrarInitialization:
    """Test JobRegistrarSubWorkflow initialization."""

    def test_default_initialization(self):
        """Should initialize with default values."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.job_registrar import (
            JobRegistrarSubWorkflow,
        )

        registrar = JobRegistrarSubWorkflow()
        assert registrar._default_priority == 5

    def test_custom_initialization(self):
        """Should initialize with custom values."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.job_registrar import (
            JobRegistrarSubWorkflow,
        )

        registrar = JobRegistrarSubWorkflow(default_priority=3)
        assert registrar._default_priority == 3
