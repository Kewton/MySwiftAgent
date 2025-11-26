"""Chat API endpoints for requirement clarification and job creation.

This module provides chat-based interfaces for creating jobs through
natural language conversation. Supports real-time streaming responses
via Server-Sent Events (SSE).

Endpoints:
- POST /chat/requirement-definition: Stream requirement clarification chat
- POST /chat/create-job: Create job from clarified requirements
- POST /chat/select-candidate: Select a candidate interpretation (Issue #173)
"""

import json
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.schemas.chat import (
    CandidateSelectRequest,
    CandidateSelectResponse,
    CreateJobRequest,
    CreateJobResponse,
    RequirementChatRequest,
    RequirementState,
)
from app.schemas.job_generator import JobGeneratorRequest
from app.services.conversation.candidate_generator import (
    candidate_to_requirement_state_dict,
)
from app.services.conversation.conversation_store import conversation_store
from app.services.conversation.llm_service import stream_requirement_clarification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/requirement-definition")
async def requirement_definition(request: RequirementChatRequest):
    """Stream requirement clarification chat (Server-Sent Events).

    This endpoint enables real-time chat dialogue for clarifying job requirements.
    Uses SSE to stream AI responses as they are generated.

    Args:
        request: Chat request with conversation context

    Returns:
        EventSourceResponse: SSE stream with message and requirement_update events

    Example:
        ```bash
        curl -N -X POST http://localhost:8104/aiagent-api/v1/chat/requirement-definition \\
          -H "Content-Type: application/json" \\
          -d '{
            "conversation_id": "conv_001",
            "user_message": "売上データを分析したい",
            "context": {
              "previous_messages": [],
              "current_requirements": {
                "data_source": null,
                "process_description": null,
                "output_format": null,
                "schedule": null,
                "completeness": 0.0
              }
            }
          }'
        ```

    SSE Events:
        - data: {"type": "message", "data": {"content": "..."}}
        - data: {"type": "requirement_update", "data": {"requirements": {...}}}
        - data: {"type": "requirements_ready", "data": {}}
        - data: {"type": "done"}
    """

    async def event_generator():
        """Generate SSE events for chat stream."""
        try:
            # Save user message to conversation history
            conversation_store.save_message(
                request.conversation_id, "user", request.user_message
            )

            logger.info(
                f"Starting requirement clarification stream: "
                f"conversation_id={request.conversation_id}"
            )

            # Parse current requirements
            current_requirements = RequirementState(
                **request.context.current_requirements
            )

            # Stream LLM responses
            full_response = ""
            async for chunk in stream_requirement_clarification(
                user_message=request.user_message,
                previous_messages=request.context.previous_messages,
                current_requirements=current_requirements,
            ):
                # Accumulate full response for conversation history
                if chunk["type"] == "message":
                    full_response += chunk["data"]["content"]

                # Yield SSE event
                yield {
                    "event": "message",
                    "data": json.dumps(chunk, ensure_ascii=False),
                }

            # Save assistant response to conversation history
            if full_response:
                conversation_store.save_message(
                    request.conversation_id, "assistant", full_response
                )

            # Send done event
            yield {
                "event": "message",
                "data": json.dumps({"type": "done"}, ensure_ascii=False),
            }

            logger.info(
                f"Completed requirement clarification stream: "
                f"conversation_id={request.conversation_id}, "
                f"response_length={len(full_response)}"
            )

        except Exception as e:
            logger.error(
                f"Error in requirement clarification stream: "
                f"conversation_id={request.conversation_id}, error={e}",
                exc_info=True,
            )
            # Send error event
            yield {
                "event": "message",
                "data": json.dumps(
                    {
                        "type": "error",
                        "data": {
                            "message": "エラーが発生しました。もう一度お試しください。"
                        },
                    },
                    ensure_ascii=False,
                ),
            }

    return EventSourceResponse(event_generator())


@router.post("/create-job", response_model=CreateJobResponse)
async def create_job(request: CreateJobRequest, background_tasks: BackgroundTasks):
    """Create job from clarified requirements.

    Converts clarified requirements into a Job Generator request and
    invokes the existing job creation flow.

    Args:
        request: Create job request with conversation ID and requirements

    Returns:
        CreateJobResponse: Job creation result with job_id and status

    Raises:
        HTTPException: If job creation fails

    Example:
        ```bash
        curl -X POST http://localhost:8104/aiagent-api/v1/chat/create-job \\
          -H "Content-Type: application/json" \\
          -d '{
            "conversation_id": "conv_001",
            "requirements": {
              "data_source": "CSVファイル",
              "process_description": "売上データの月別集計",
              "output_format": "Excelレポート",
              "schedule": "毎日朝9時",
              "completeness": 0.95
            }
          }'
        ```

    Response:
        ```json
        {
          "job_id": "job_12345",
          "job_master_id": "jm_12345",
          "status": "success",
          "message": "ジョブを作成しました"
        }
        ```
    """
    try:
        logger.info(
            f"Creating job from requirements: "
            f"conversation_id={request.conversation_id}, "
            f"completeness={request.requirements.completeness:.0%}"
        )

        # Validate requirements completeness
        if request.requirements.completeness < 0.8:
            raise HTTPException(
                status_code=400,
                detail=f"Requirements not sufficiently clarified "
                f"({request.requirements.completeness:.0%} < 80%)",
            )

        # Convert requirements to Job Generator request
        job_generator_request = _convert_requirements_to_job_request(
            request.requirements
        )

        # Call existing Job Generator endpoint
        from app.api.v1.job_generator_endpoints import generate_job_and_tasks

        result = await generate_job_and_tasks(job_generator_request, background_tasks)

        # Extract job IDs from result (JobGeneratorResponse is a Pydantic model)
        job_id = result.job_id
        job_master_id = result.job_master_id

        if not job_id or not job_master_id:
            raise ValueError("Job Generator did not return job IDs")

        logger.info(
            f"Successfully created job: job_id={job_id}, job_master_id={job_master_id}"
        )

        return CreateJobResponse(
            job_id=job_id,
            job_master_id=job_master_id,
            status="success",
            message="ジョブを作成しました",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to create job: "
            f"conversation_id={request.conversation_id}, error={e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"ジョブの作成に失敗しました: {str(e)}"
        ) from e


def _convert_requirements_to_job_request(
    requirements: RequirementState,
) -> JobGeneratorRequest:
    """Convert RequirementState to Job Generator request format.

    Args:
        requirements: Clarified requirement state

    Returns:
        JobGeneratorRequest object

    Example:
        >>> reqs = RequirementState(
        ...     data_source="CSV",
        ...     process_description="売上分析",
        ...     output_format="Excel",
        ...     schedule="毎日"
        ... )
        >>> req = _convert_requirements_to_job_request(reqs)
        >>> print("## データソース" in req.user_requirement)
        True
    """
    # Format requirements as natural language
    user_requirement = f"""
## データソース
{requirements.data_source or "未指定"}

## 処理内容
{requirements.process_description or "未指定"}

## 出力形式
{requirements.output_format or "未指定"}

## スケジュール
{requirements.schedule or "オンデマンド"}

---

上記の要件に基づいてジョブを作成してください。
利用可能なすべての機能（Google Drive, Gmail, GraphAI等）を使用可能です。
"""

    return JobGeneratorRequest(user_requirement=user_requirement.strip())


# ============================================================================
# Multi-Candidate Selection Feature (Issue #173)
# ============================================================================


@router.post("/select-candidate", response_model=CandidateSelectResponse)
async def select_candidate(request: CandidateSelectRequest):
    """Select a candidate interpretation.

    After receiving candidate options via SSE candidate_selection event,
    users call this endpoint to select their preferred interpretation.
    The selected candidate's requirements are used for subsequent dialogue.

    Args:
        request: Selection request with conversation ID and selected candidate ID

    Returns:
        CandidateSelectResponse: Updated requirement state from selected candidate

    Raises:
        HTTPException: If selection fails or candidate not found

    Example:
        ```bash
        curl -X POST http://localhost:8104/aiagent-api/v1/chat/select-candidate \\
          -H "Content-Type: application/json" \\
          -d '{
            "conversation_id": "conv_001",
            "selected_candidate_id": "A"
          }'
        ```

    Response:
        ```json
        {
          "conversation_id": "conv_001",
          "selected_candidate_id": "A",
          "requirements": {
            "data_source": "CSVファイル",
            "process_description": "売上データの月別集計",
            "output_format": "Excelレポート",
            "schedule": "オンデマンド",
            "completeness": 0.75
          },
          "message": "候補Aを選択しました。追加の詳細を確認させてください。"
        }
        ```
    """
    try:
        logger.info(
            f"Selecting candidate: "
            f"conversation_id={request.conversation_id}, "
            f"selected_candidate_id={request.selected_candidate_id}"
        )

        # Get stored candidates for this conversation
        stored_candidates = conversation_store.get_candidates(request.conversation_id)

        if not stored_candidates:
            raise HTTPException(
                status_code=404,
                detail=f"No candidates found for conversation: {request.conversation_id}",
            )

        # Find selected candidate
        selected_candidate = None
        for candidate in stored_candidates:
            if candidate.candidate_id == request.selected_candidate_id:
                selected_candidate = candidate
                break

        if not selected_candidate:
            raise HTTPException(
                status_code=400,
                detail=f"Candidate '{request.selected_candidate_id}' not found. "
                f"Available: {[c.candidate_id for c in stored_candidates]}",
            )

        # Convert candidate to requirement state
        requirements_dict = candidate_to_requirement_state_dict(selected_candidate)
        requirements = RequirementState(**requirements_dict)

        # Save selection to conversation store
        conversation_store.save_selected_candidate(
            request.conversation_id, request.selected_candidate_id
        )

        # Generate confirmation message
        message = f"候補{request.selected_candidate_id}（{selected_candidate.title}）を選択しました。追加の詳細を確認させてください。"

        logger.info(
            f"Candidate selected successfully: "
            f"conversation_id={request.conversation_id}, "
            f"candidate={request.selected_candidate_id}, "
            f"completeness={requirements.completeness:.0%}"
        )

        return CandidateSelectResponse(
            conversation_id=request.conversation_id,
            selected_candidate_id=request.selected_candidate_id,
            requirements=requirements,
            message=message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to select candidate: "
            f"conversation_id={request.conversation_id}, error={e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"候補の選択に失敗しました: {str(e)}"
        ) from e
