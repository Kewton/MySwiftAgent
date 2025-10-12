import logging
import re
from datetime import datetime

from fastapi import APIRouter, HTTPException

from aiagent.langgraph.sampleagent.graphagent import ainvoke_graphagent
from aiagent.langgraph.utilityaiagents.action_agent import actionagent
from aiagent.langgraph.utilityaiagents.explorer_agent import exploreragent
from aiagent.langgraph.utilityaiagents.jsonOutput_agent import jsonOutputagent
from aiagent.langgraph.utilityaiagents.playwright_agent import playwrightagent
from aiagent.langgraph.utilityaiagents.wikipedia_agent import wikipediaagent
from app.schemas.standardAiAgent import (
    ChatMessage,
    ExpertAiAgentRequest,
    ExpertAiAgentResponse,
    ExpertAiAgentResponseJson,
)
from mymcp.utils.chatollama import chatOllama

logger = logging.getLogger(__name__)


def remove_think_tags(text: str) -> str:
    """
    文字列から <think>...</think> タグとその内容を削除します。

    Args:
        text:処理対象の文字列。

    Returns:
        <think> タグが削除された文字列。
    """
    # <think> から </think> までを非貪欲マッチで捉え、
    # re.DOTALL フラグによりタグ内に改行が含まれていてもマッチさせます。
    pattern = r"<think>.*?</think>"
    cleaned_text = re.sub(pattern, "", text, flags=re.DOTALL)
    print(f"cleaned_text:{cleaned_text}")
    return cleaned_text


router = APIRouter()


@router.get(
    "/",
    summary="Hello World",
    description="Hello Worldです。疎通確認に使用してください。",
)
def home_hello_world():
    return {"message": "Hello World"}


@router.post("/mylllm", summary="", description="")
def exec_myllm(request: ExpertAiAgentRequest):
    logger.info("exec_myllm called")
    logger.info(f"Request data: {request}")

    _messages: list[ChatMessage] = []
    if request.system_imput is not None:
        _messages.append(ChatMessage(role="system", content=request.system_imput))
    _messages.append(ChatMessage(role="user", content=request.user_input))

    print(f"request.user_input:{_messages}")
    logger.info(f"Messages for LLM: {_messages}")

    model_name = request.model_name if request.model_name is not None else "gpt-4o-mini"
    # Convert ChatMessage objects to dictionaries for JSON serialization
    messages_dict = [msg.model_dump() for msg in _messages]
    result = chatOllama(messages_dict, model_name)
    cleaned_result = remove_think_tags(result)

    print(f"result: {cleaned_result}")
    logger.info(f"LLM result: {cleaned_result}")

    return ExpertAiAgentResponse(
        result=cleaned_result, text=cleaned_result, type="exec_myllm"
    )


@router.post(
    "/aiagent/sample",
    summary="LangGraphのAIエージェントを実行します",
    description="LangGraphのAIエージェントを実行します",
)
async def aiagent_graph(request: ExpertAiAgentRequest):
    try:
        _input = f"""
        # メタ情報:
        - 現在の時刻は「{datetime.now()}」です。

        # 指示書
        {request.user_input}
        """
        print(f"request.user_input:{_input}")
        chat_history, aiMessage = await ainvoke_graphagent(
            _input, project=request.project
        )
        _response = {"result": aiMessage, "type": "sample", "chathistory": chat_history}
        return ExpertAiAgentResponse(**_response)
    except Exception as e:
        import traceback

        print(f"An unexpected error occurred: {e}")
        print("Full traceback:")
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail="An internal server error occurred in the agent."
        ) from e


@router.post(
    "/aiagent/utility/{agent_name}",
    summary="LangGraphのAIエージェントを実行します",
    description="LangGraphのAIエージェントを実行します",
)
async def myaiagents(request: ExpertAiAgentRequest, agent_name: str):
    try:
        _input = f"""
        # メタ情報:
        - 現在の時刻は「{datetime.now()}」です。

        # 指示書
        {request.user_input}
        """

        model_name = (
            request.model_name if request.model_name is not None else "gpt-4o-mini"
        )

        if "jsonoutput" in agent_name:
            print(f"request.user_input:{_input}")
            parsed_json = await jsonOutputagent(
                _input, model_name, project=request.project
            )
            return ExpertAiAgentResponseJson(result=parsed_json, type="jsonOutput")
        elif "explorer" in agent_name:
            print(f"request.user_input:{_input}")
            result = await exploreragent(_input, model_name, project=request.project)
            return ExpertAiAgentResponse(
                result=remove_think_tags(result), type="explorer"
            )
        elif "action" in agent_name:
            print(f"request.user_input:{_input}")
            result = await actionagent(_input, model_name, project=request.project)
            return ExpertAiAgentResponse(
                result=remove_think_tags(result), type="action"
            )
        elif "playwright" in agent_name:
            print(f"request.user_input:{_input}")
            result = await playwrightagent(_input, model_name)
            return ExpertAiAgentResponse(
                result=remove_think_tags(result), type="playwright"
            )
        elif "wikipedia" in agent_name:
            print(f"request.user_input:{_input}")
            # Extract language parameter if provided, default to Japanese
            language = (
                request.language
                if hasattr(request, "language") and request.language
                else "ja"
            )
            result = await wikipediaagent(_input, model_name, language)
            return ExpertAiAgentResponse(
                result=remove_think_tags(result), type="wikipedia"
            )
        return {"message": "No matching agent found."}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(
            status_code=500, detail="An internal server error occurred in the agent."
        ) from e
