import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.exceptions import ServiceError
from app.schemas.standardAiAgent import ExpertAiAgentRequest
from app.services.ai_agent_service import AiAgentService
from app.services.response_builder import ResponseBuilder

logger = logging.getLogger(__name__)


router = APIRouter(tags=["aiagent"])
_agent_service = AiAgentService()
_response_builder = ResponseBuilder()


def get_agent_service() -> AiAgentService:
    """Return the shared AiAgentService instance used by the endpoints."""

    return _agent_service


def remove_think_tags(text: str) -> str:
    """Backward compatible wrapper that strips <think> tags."""

    return _response_builder.remove_think_tags(text)


def _handle_service_error(error: ServiceError) -> None:
    """Translate service exceptions into HTTP responses."""

    logger.exception("Service error raised by agent endpoint: %s", error)
    detail: dict[str, Any] = {"message": str(error)}
    if getattr(error, "context", None):
        detail["context"] = error.context
    raise HTTPException(status_code=500, detail=detail)


@router.get(
    "/",
    summary="Hello World",
    description="Hello Worldです。疎通確認に使用してください。",
)
async def home_hello_world() -> dict[str, str]:
    """Simple health-style endpoint for connectivity checks."""

    return {"message": "Hello World"}


@router.post(
    "/mylllm",
    summary="General purpose LLM execution",
    description=("Gemini/GPT/Ollama のモデルを呼び出すシンプルなエンドポイントです。"),
)
async def exec_myllm(
    request: ExpertAiAgentRequest,
    service: AiAgentService = Depends(get_agent_service),
):
    """Execute the generic LLM flow via the service layer."""

    try:
        return await service.execute_myllm(request)
    except ServiceError as error:
        _handle_service_error(error)


@router.post(
    "/aiagent/sample",
    summary="LangGraph のサンプルエージェント実行",
    description="force_json=True の場合は JSON 変換とリトライを行います。",
)
async def aiagent_graph(
    request: ExpertAiAgentRequest,
    service: AiAgentService = Depends(get_agent_service),
):
    """Execute the sample LangGraph agent with optional JSON handling."""

    try:
        return await service.execute_sample_agent(request)
    except ServiceError as error:
        _handle_service_error(error)


@router.post(
    "/aiagent/utility/{agent_name}",
    summary="Utility LangGraph エージェント実行",
    description=(
        "Explorer / Action / Playwright / Wikipedia など用途別エージェントを呼び出します。"
    ),
)
async def myaiagents(
    request: ExpertAiAgentRequest,
    agent_name: str,
    service: AiAgentService = Depends(get_agent_service),
):
    """Execute one of the utility LangGraph agents."""

    try:
        return await service.execute_utility_agent(
            agent_name=agent_name,
            request=request,
        )
    except ServiceError as error:
        _handle_service_error(error)
