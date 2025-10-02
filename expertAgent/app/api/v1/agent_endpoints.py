import re
from datetime import datetime

from fastapi import APIRouter, HTTPException

from aiagent.langgraph.sampleagent.graphagent import ainvoke_graphagent
from aiagent.langgraph.utilityaiagents.action_agent import actionagent
from aiagent.langgraph.utilityaiagents.explorer_agent import exploreragent
from aiagent.langgraph.utilityaiagents.jsonOutput_agent import jsonOutputagent
from app.schemas.standardAiAgent import (
    ChatMessage,
    ExpertAiAgentRequest,
    ExpertAiAgentResponse,
    ExpertAiAgentResponseJson,
)
from mymcp.utils.chatollama import chatOllama


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
    _messages: list[ChatMessage] = []
    if request.system_imput is not None:
        _messages.append(ChatMessage(role="system", content=request.system_imput))
    _messages.append(ChatMessage(role="user", content=request.user_input))

    print(f"request.user_input:{_messages}")

    model_name = request.model_name if request.model_name is not None else "gpt-4o-mini"
    result = chatOllama(_messages, model_name)
    cleaned_result = remove_think_tags(result)

    print(f"result: {cleaned_result}")

    return ExpertAiAgentResponse(
        result=cleaned_result,
        text=cleaned_result,
        type="exec_myllm"
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
        chat_history, aiMessage = await ainvoke_graphagent(_input)
        _response = {"result": aiMessage, "type": "sample", "chathistory": chat_history}
        return ExpertAiAgentResponse(**_response)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
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

        model_name = request.model_name if request.model_name is not None else "gpt-4o-mini"

        if "jsonoutput" in agent_name:
            print(f"request.user_input:{_input}")
            parsed_json = await jsonOutputagent(_input, model_name)
            return ExpertAiAgentResponseJson(result=parsed_json, type="jsonOutput")
        elif "explorer" in agent_name:
            print(f"request.user_input:{_input}")
            result = await exploreragent(_input, model_name)
            return ExpertAiAgentResponse(result=remove_think_tags(result), type="explorer")
        elif "action" in agent_name:
            print(f"request.user_input:{_input}")
            result = await actionagent(_input, model_name)
            return ExpertAiAgentResponse(result=remove_think_tags(result), type="action")
        return {"message": "No matching agent found."}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(
            status_code=500, detail="An internal server error occurred in the agent."
        ) from e
