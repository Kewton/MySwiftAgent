"""Prompts Management API endpoints.

Issue #191: Prompts Management API Implementation
FastAPI router for prompt template management.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.prompts import PromptListResponse, PromptTemplate
from app.services.prompt_management import PromptManagementService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["prompts"], prefix="/prompts")

# Shared service instance
_prompt_management_service = PromptManagementService()


def get_prompt_management_service() -> PromptManagementService:
    """Return the shared PromptManagementService instance."""
    return _prompt_management_service


@router.get(
    "",
    response_model=PromptListResponse,
    summary="List all prompts",
    description="""
Get a list of all available prompt templates.

Returns all prompt templates with their versions, metadata, and content.
The response includes:
- items: List of prompt templates
- total: Total count of prompts

Each prompt template contains:
- id: Unique identifier (directory name)
- name: Display name
- description: Prompt description
- category: Category (e.g., agent type)
- current_version: Currently active version number
- versions: List of all available versions with content
- created_at: Creation timestamp
- updated_at: Last modification timestamp
""",
)
async def list_prompts(
    service: PromptManagementService = Depends(get_prompt_management_service),
) -> PromptListResponse:
    """Get all available prompt templates.

    Returns:
        PromptListResponse: List of all prompts with total count.
    """
    try:
        result = service.get_prompts()
        logger.info(f"Listed {result.total} prompts")
        return result
    except Exception as e:
        logger.exception("Error listing prompts")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list prompts: {str(e)}",
        ) from e


@router.get(
    "/{prompt_id}",
    response_model=PromptTemplate,
    summary="Get prompt by ID",
    description="""
Get a specific prompt template by its ID.

The prompt ID corresponds to the directory name in the prompts folder
(e.g., "requirement_clarification", "workflow_generation").

Returns the complete prompt template including:
- All available versions
- Full content for each version
- Metadata (description, category, timestamps)

Raises 404 if the prompt is not found.
""",
    responses={
        404: {
            "description": "Prompt not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Prompt not found: nonexistent_prompt"}
                }
            },
        }
    },
)
async def get_prompt(
    prompt_id: str,
    service: PromptManagementService = Depends(get_prompt_management_service),
) -> PromptTemplate:
    """Get a specific prompt template by ID.

    Args:
        prompt_id: The prompt identifier (directory name)
        service: PromptManagementService dependency

    Returns:
        PromptTemplate: The requested prompt template.

    Raises:
        HTTPException: 404 if prompt not found.
    """
    try:
        result = service.get_prompt(prompt_id)

        if result is None:
            logger.info(f"Prompt not found: {prompt_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt not found: {prompt_id}",
            )

        logger.info(f"Retrieved prompt: {prompt_id}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting prompt {prompt_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get prompt: {str(e)}",
        ) from e
