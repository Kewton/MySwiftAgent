"""Unit tests for Prompts API schemas.

Issue #191: Prompts Management API Implementation
Tests for Pydantic schemas used in the prompts API endpoints.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.prompts import (
    PromptListResponse,
    PromptTemplate,
    PromptVersion,
)


class TestPromptVersionSchema:
    """Test PromptVersion schema validation."""

    def test_valid_prompt_version(self) -> None:
        """Test creating a valid PromptVersion."""
        version = PromptVersion(
            id="v1",
            version=1,
            content="Test prompt content",
            description="Test description",
            created_at=datetime.now(),
            is_active=True,
        )
        assert version.id == "v1"
        assert version.version == 1
        assert version.content == "Test prompt content"
        assert version.is_active is True

    def test_prompt_version_with_minimal_fields(self) -> None:
        """Test PromptVersion with only required fields."""
        version = PromptVersion(
            id="default",
            version=1,
            content="Minimal content",
        )
        assert version.id == "default"
        assert version.description is None
        assert version.is_active is True  # Default value

    def test_prompt_version_validation_errors(self) -> None:
        """Test PromptVersion validation errors."""
        with pytest.raises(ValidationError):
            PromptVersion(
                id="",  # Empty id should be allowed
                version=-1,  # Negative version should fail
                content="",
            )


class TestPromptTemplateSchema:
    """Test PromptTemplate schema validation."""

    def test_valid_prompt_template(self) -> None:
        """Test creating a valid PromptTemplate."""
        version = PromptVersion(
            id="default",
            version=1,
            content="System prompt content",
            description="Default version",
            created_at=datetime.now(),
            is_active=True,
        )
        template = PromptTemplate(
            id="requirement_clarification",
            name="Requirement Clarification",
            description="System prompt for requirement clarification",
            category="system",
            current_version=1,
            versions=[version],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert template.id == "requirement_clarification"
        assert template.name == "Requirement Clarification"
        assert len(template.versions) == 1
        assert template.current_version == 1

    def test_prompt_template_with_multiple_versions(self) -> None:
        """Test PromptTemplate with multiple versions."""
        versions = [
            PromptVersion(id="default", version=1, content="V1 content"),
            PromptVersion(id="v2", version=2, content="V2 content", is_active=False),
        ]
        template = PromptTemplate(
            id="workflow_generation",
            name="Workflow Generation",
            description="Generate GraphAI workflows",
            category="workflow",
            current_version=2,
            versions=versions,
        )
        assert len(template.versions) == 2
        assert template.current_version == 2

    def test_prompt_template_minimal(self) -> None:
        """Test PromptTemplate with minimal fields."""
        template = PromptTemplate(
            id="test_prompt",
            name="Test Prompt",
            current_version=1,
            versions=[],
        )
        assert template.id == "test_prompt"
        assert template.description is None
        assert template.category is None


class TestPromptListResponseSchema:
    """Test PromptListResponse schema validation."""

    def test_valid_prompt_list_response(self) -> None:
        """Test creating a valid PromptListResponse."""
        template = PromptTemplate(
            id="test_prompt",
            name="Test Prompt",
            current_version=1,
            versions=[],
        )
        response = PromptListResponse(
            items=[template],
            total=1,
        )
        assert len(response.items) == 1
        assert response.total == 1

    def test_empty_prompt_list_response(self) -> None:
        """Test PromptListResponse with empty list."""
        response = PromptListResponse(
            items=[],
            total=0,
        )
        assert len(response.items) == 0
        assert response.total == 0

    def test_prompt_list_response_with_multiple_items(self) -> None:
        """Test PromptListResponse with multiple templates."""
        templates = [
            PromptTemplate(id=f"prompt_{i}", name=f"Prompt {i}", current_version=1, versions=[])
            for i in range(5)
        ]
        response = PromptListResponse(
            items=templates,
            total=5,
        )
        assert len(response.items) == 5
        assert response.total == 5


class TestSchemaJsonSerialization:
    """Test JSON serialization of schemas."""

    def test_prompt_version_json(self) -> None:
        """Test PromptVersion JSON serialization."""
        version = PromptVersion(
            id="default",
            version=1,
            content="Test content",
            created_at=datetime(2025, 1, 15, 10, 0, 0),
            is_active=True,
        )
        json_data = version.model_dump_json()
        assert "default" in json_data
        assert "Test content" in json_data

    def test_prompt_template_json(self) -> None:
        """Test PromptTemplate JSON serialization."""
        template = PromptTemplate(
            id="test",
            name="Test",
            current_version=1,
            versions=[],
            created_at=datetime(2025, 1, 15, 10, 0, 0),
            updated_at=datetime(2025, 1, 15, 10, 0, 0),
        )
        json_data = template.model_dump_json()
        assert "test" in json_data

    def test_prompt_list_response_json(self) -> None:
        """Test PromptListResponse JSON serialization."""
        response = PromptListResponse(
            items=[],
            total=0,
        )
        json_data = response.model_dump_json()
        assert "items" in json_data
        assert "total" in json_data
