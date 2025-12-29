"""Integration tests for TaskMaster template validation API."""

import pytest
from fastapi import status
from httpx import AsyncClient


class TestTaskMasterTemplateValidation:
    """Integration tests for template validation in TaskMaster API."""

    @pytest.mark.asyncio
    async def test_create_task_master_without_template(
        self, client: AsyncClient, db_session
    ) -> None:
        """TaskMaster created without template has no validation result."""
        response = await client.post(
            "/api/v1/task-masters",
            json={
                "name": "no_template_task",
                "method": "POST",
                "url": "https://api.example.com/test",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["template_validation"] is None

    @pytest.mark.asyncio
    async def test_create_task_master_with_static_template(
        self, client: AsyncClient, db_session
    ) -> None:
        """TaskMaster with static template (no variables) validates successfully."""
        response = await client.post(
            "/api/v1/task-masters",
            json={
                "name": "static_template_task",
                "method": "POST",
                "url": "https://api.example.com/test",
                "body_template": {"static_field": "static_value", "number": 42},
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["template_validation"] is not None
        assert data["template_validation"]["is_valid"] is True
        assert data["template_validation"]["warnings"] == []
        assert data["template_validation"]["extracted_variables"] == []

    @pytest.mark.asyncio
    async def test_create_task_master_with_job_body_variable(
        self, client: AsyncClient, db_session
    ) -> None:
        """TaskMaster with job.body variable generates warning."""
        response = await client.post(
            "/api/v1/task-masters",
            json={
                "name": "job_body_task",
                "method": "POST",
                "url": "https://api.example.com/test",
                "body_template": {"user_input": "{{job.body.query}}"},
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        validation = data["template_validation"]
        assert validation is not None
        assert validation["is_valid"] is True  # Warning, not error
        assert "{{job.body.query}}" in validation["extracted_variables"]
        assert len(validation["warnings"]) == 1
        assert validation["warnings"][0]["severity"] == "warning"
        assert "job.body.query" in validation["warnings"][0]["message"]

    @pytest.mark.asyncio
    async def test_create_task_master_with_task_reference(
        self, client: AsyncClient, db_session
    ) -> None:
        """TaskMaster with task reference variable extracts variable."""
        response = await client.post(
            "/api/v1/task-masters",
            json={
                "name": "task_ref_task",
                "method": "POST",
                "url": "https://api.example.com/test",
                "body_template": {"prev_result": "{{tasks[0].output_data.result}}"},
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        validation = data["template_validation"]
        assert validation is not None
        assert validation["is_valid"] is True
        assert "{{tasks[0].output_data.result}}" in validation["extracted_variables"]

    @pytest.mark.asyncio
    async def test_create_task_master_with_multiple_variables(
        self, client: AsyncClient, db_session
    ) -> None:
        """TaskMaster with multiple variable types extracts all."""
        response = await client.post(
            "/api/v1/task-masters",
            json={
                "name": "multi_var_task",
                "method": "POST",
                "url": "https://api.example.com/test",
                "body_template": {
                    "job_input": "{{job.body.query}}",
                    "prev_result": "{{tasks[0].output_data.result}}",
                    "current_input": "{{task.input_data.param}}",
                },
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        validation = data["template_validation"]
        assert validation is not None
        assert validation["is_valid"] is True
        assert len(validation["extracted_variables"]) == 3
        assert "{{job.body.query}}" in validation["extracted_variables"]
        assert "{{tasks[0].output_data.result}}" in validation["extracted_variables"]
        assert "{{task.input_data.param}}" in validation["extracted_variables"]

    @pytest.mark.asyncio
    async def test_update_task_master_with_template(
        self, client: AsyncClient, db_session
    ) -> None:
        """Updating TaskMaster with template returns validation result."""
        # First create a task master
        create_response = await client.post(
            "/api/v1/task-masters",
            json={
                "name": "update_test_task",
                "method": "POST",
                "url": "https://api.example.com/test",
            },
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        master_id = create_response.json()["id"]

        # Update with body_template
        update_response = await client.put(
            f"/api/v1/task-masters/{master_id}",
            json={
                "body_template": {"user_input": "{{job.body.email}}"},
            },
        )
        assert update_response.status_code == status.HTTP_200_OK
        data = update_response.json()

        validation = data["template_validation"]
        assert validation is not None
        assert validation["is_valid"] is True
        assert "{{job.body.email}}" in validation["extracted_variables"]

    @pytest.mark.asyncio
    async def test_create_task_master_with_large_task_index_warning(
        self, client: AsyncClient, db_session
    ) -> None:
        """TaskMaster with unusually large task index generates warning."""
        response = await client.post(
            "/api/v1/task-masters",
            json={
                "name": "large_index_task",
                "method": "POST",
                "url": "https://api.example.com/test",
                "body_template": {"prev": "{{tasks[150].output_data.result}}"},
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        validation = data["template_validation"]
        assert validation is not None
        assert validation["is_valid"] is True
        assert "{{tasks[150].output_data.result}}" in validation["extracted_variables"]
        # Check for large index warning
        assert any(
            "150" in w["message"] and "large" in w["message"].lower()
            for w in validation["warnings"]
        )

    @pytest.mark.asyncio
    async def test_create_task_master_with_nested_template(
        self, client: AsyncClient, db_session
    ) -> None:
        """TaskMaster with nested template structure extracts all variables."""
        response = await client.post(
            "/api/v1/task-masters",
            json={
                "name": "nested_template_task",
                "method": "POST",
                "url": "https://api.example.com/test",
                "body_template": {
                    "outer": {"inner": {"value": "{{job.body.nested_value}}"}},
                    "list_field": ["{{job.body.item1}}", "{{job.body.item2}}"],
                },
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        validation = data["template_validation"]
        assert validation is not None
        assert validation["is_valid"] is True
        assert "{{job.body.nested_value}}" in validation["extracted_variables"]
        assert "{{job.body.item1}}" in validation["extracted_variables"]
        assert "{{job.body.item2}}" in validation["extracted_variables"]


class TestTaskMasterTemplateValidationErrors:
    """Integration tests for template validation error cases."""

    @pytest.mark.asyncio
    async def test_oversized_template_rejected(
        self, client: AsyncClient, db_session
    ) -> None:
        """Template exceeding size limit is rejected."""
        # Create a template larger than 64KB
        large_value = "x" * (65 * 1024)
        response = await client.post(
            "/api/v1/task-masters",
            json={
                "name": "oversized_template_task",
                "method": "POST",
                "url": "https://api.example.com/test",
                "body_template": {"large_field": large_value},
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        validation = data["template_validation"]
        assert validation is not None
        assert validation["is_valid"] is False
        assert any(
            w["severity"] == "error" and "size" in w["message"].lower()
            for w in validation["warnings"]
        )

    @pytest.mark.asyncio
    async def test_too_many_variables_rejected(
        self, client: AsyncClient, db_session
    ) -> None:
        """Template with too many variables is rejected."""
        # Create template with > 100 variables
        body_template = {
            f"field_{i}": f"{{{{job.body.field_{i}}}}}" for i in range(101)
        }
        response = await client.post(
            "/api/v1/task-masters",
            json={
                "name": "too_many_vars_task",
                "method": "POST",
                "url": "https://api.example.com/test",
                "body_template": body_template,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        validation = data["template_validation"]
        assert validation is not None
        assert validation["is_valid"] is False
        assert any(
            w["severity"] == "error" and "too many" in w["message"].lower()
            for w in validation["warnings"]
        )
