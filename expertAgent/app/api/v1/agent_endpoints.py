import logging
import re
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from aiagent.langgraph.sampleagent.graphagent import ainvoke_graphagent
from aiagent.langgraph.utilityaiagents.action_agent import actionagent
from aiagent.langgraph.utilityaiagents.explorer_agent import exploreragent
from aiagent.langgraph.utilityaiagents.file_reader_agent import filereaderagent
from aiagent.langgraph.utilityaiagents.jsonOutput_agent import jsonOutputagent
from aiagent.langgraph.utilityaiagents.playwright_agent import playwrightagent
from aiagent.langgraph.utilityaiagents.wikipedia_agent import wikipediaagent
from app.schemas.standardAiAgent import (
    ChatMessage,
    ExpertAiAgentRequest,
    ExpertAiAgentResponse,
    ExpertAiAgentResponseJson,
)
from app.utils.json_converter import force_to_json_response, to_parse_json
from core.test_mode_handler import handle_test_mode
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

    # Test mode check using common handler
    test_result = handle_test_mode(request.test_mode, request.test_response, "mylllm")
    if test_result is not None:
        return test_result

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
    description="LangGraphのAIエージェントを実行します。force_json=Trueの場合、レスポンスを必ずJSON形式に変換し、失敗時は最大max_retries回までリトライします。",
)
async def aiagent_graph(request: ExpertAiAgentRequest):
    """
    LangGraph AIエージェントを実行

    force_json=True の場合:
    - レスポンスを必ず JSON 形式に変換
    - JSON 変換失敗時は最大 max_retries 回までリトライ
    - 最終的に変換できない場合は force_to_json_response で強制変換
    """
    max_retries = request.max_retries if request.force_json else 0
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Attempt {attempt + 1}/{max_retries + 1} for aiagent/sample")

            # Test mode check using common handler
            test_result = handle_test_mode(
                request.test_mode, request.test_response, "sample"
            )
            if test_result is not None:
                return test_result

            # メイン処理
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

            # force_json が True の場合、レスポンスを JSON 変換
            if request.force_json:
                try:
                    # aiMessage が既に JSON 形式か確認
                    if isinstance(aiMessage, (dict, list)):
                        result = aiMessage
                    else:
                        # 文字列の場合は JSON に変換
                        result = to_parse_json(str(aiMessage))

                    logger.info(
                        f"Successfully converted to JSON on attempt {attempt + 1}"
                    )

                    return ExpertAiAgentResponseJson(
                        result=result,
                        type="sample",
                        chathistory=chat_history,
                        attempts=attempt + 1 if attempt > 0 else None,
                    )

                except ValueError as json_err:
                    logger.warning(
                        f"JSON conversion failed on attempt {attempt + 1}: {json_err}"
                    )
                    last_error = json_err

                    # 最終試行の場合、強制的に JSON に変換
                    if attempt == max_retries:
                        logger.error("Max retries reached, forcing JSON conversion")
                        forced_result = force_to_json_response(
                            str(aiMessage),
                            error_context=f"aiagent/sample after {max_retries + 1} attempts",
                            error_detail=str(json_err),
                        )
                        return JSONResponse(status_code=200, content=forced_result)
                    else:
                        # リトライ
                        logger.info(
                            f"Retrying... (attempt {attempt + 2}/{max_retries + 1})"
                        )
                        continue
            else:
                # force_json が False の場合は通常処理
                _response = {
                    "result": aiMessage,
                    "type": "sample",
                    "chathistory": chat_history,
                }
                return ExpertAiAgentResponse(**_response)

        except Exception as e:
            last_error = e
            logger.error(
                f"Error on attempt {attempt + 1}/{max_retries + 1}: {e}", exc_info=True
            )

            # 最終試行の場合
            if attempt == max_retries:
                if request.force_json:
                    # force_json が True の場合は JSON エラーレスポンス
                    return JSONResponse(
                        status_code=500,
                        content={
                            "result": f"Error occurred after {max_retries + 1} attempts: {str(e)}",
                            "type": "error",
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "attempts": max_retries + 1,
                            "is_json_guaranteed": True,
                        },
                    )
                else:
                    # 通常のエラーハンドリング
                    import traceback

                    print(f"An unexpected error occurred: {e}")
                    print("Full traceback:")
                    traceback.print_exc()
                    raise HTTPException(
                        status_code=500,
                        detail="An internal server error occurred in the agent.",
                    ) from e
            else:
                # リトライ
                logger.info(
                    f"Retrying due to error... (attempt {attempt + 2}/{max_retries + 1})"
                )
                continue

    # ここには到達しないはずだが、念のため
    raise HTTPException(
        status_code=500, detail=f"Unexpected error after retries: {last_error}"
    )


@router.post(
    "/aiagent/utility/{agent_name}",
    summary="LangGraphのAIエージェントを実行します",
    description="LangGraphのAIエージェントを実行します。force_json=Trueの場合、レスポンスを必ずJSON形式に変換し、失敗時は最大max_retries回までリトライします。",
)
async def myaiagents(request: ExpertAiAgentRequest, agent_name: str):
    """
    Utility AIエージェントを実行

    force_json=True の場合:
    - レスポンスを必ず JSON 形式に変換
    - JSON 変換失敗時は最大 max_retries 回までリトライ
    - 最終的に変換できない場合は force_to_json_response で強制変換

    対応エージェント:
    - jsonoutput: JSON出力専用エージェント（常にJSON返却）
    - explorer: ウェブ探索エージェント
    - action: アクション実行エージェント
    - playwright: ブラウザ自動化エージェント
    - wikipedia: Wikipedia検索エージェント
    - file_reader: ファイル読み込みエージェント
    """
    max_retries = request.max_retries if request.force_json else 0
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            logger.info(
                f"Attempt {attempt + 1}/{max_retries + 1} for aiagent/utility/{agent_name}"
            )

            # Test mode check using common handler
            test_result = handle_test_mode(
                request.test_mode, request.test_response, agent_name
            )
            if test_result is not None:
                return test_result

            _input = f"""
            # メタ情報:
            - 現在の時刻は「{datetime.now()}」です。

            # 指示書
            {request.user_input}
            """

            model_name = (
                request.model_name if request.model_name is not None else "gpt-4o-mini"
            )

            # jsonoutput エージェント（常にJSON返却）
            if "jsonoutput" in agent_name:
                print(f"request.user_input:{_input}")
                parsed_json = await jsonOutputagent(
                    _input, model_name, project=request.project
                )
                # jsonoutput エージェントは既に JSON を返すのでそのまま返却
                return ExpertAiAgentResponseJson(
                    result=parsed_json,
                    type="jsonOutput",
                    attempts=attempt + 1 if attempt > 0 else None,
                )

            # その他のエージェント
            result_str: str = ""
            agent_type: str = ""

            if "explorer" in agent_name:
                print(f"request.user_input:{_input}")
                result_str = await exploreragent(
                    _input, model_name, project=request.project
                )
                agent_type = "explorer"
            elif "action" in agent_name:
                print(f"request.user_input:{_input}")
                result_str = await actionagent(
                    _input, model_name, project=request.project
                )
                agent_type = "action"
            elif "playwright" in agent_name:
                print(f"request.user_input:{_input}")
                result_str = await playwrightagent(_input, model_name)
                agent_type = "playwright"
            elif "wikipedia" in agent_name:
                print(f"request.user_input:{_input}")
                # Extract language parameter if provided, default to Japanese
                language = request.language if request.language else "ja"
                result_str = await wikipediaagent(_input, model_name, language)
                agent_type = "wikipedia"
            elif "file_reader" in agent_name or "filereader" in agent_name:
                print(f"request.user_input:{_input}")
                result_str = await filereaderagent(
                    _input, model_name, project=request.project
                )
                agent_type = "file_reader"
            else:
                return {"message": "No matching agent found."}

            # <think> タグを削除
            result_cleaned = remove_think_tags(result_str)

            # force_json 処理
            if request.force_json:
                try:
                    # JSON 変換を試みる
                    json_result = to_parse_json(result_cleaned)
                    logger.info(
                        f"Successfully converted {agent_type} to JSON on attempt {attempt + 1}"
                    )
                    return ExpertAiAgentResponseJson(
                        result=json_result,
                        type=agent_type,
                        attempts=attempt + 1 if attempt > 0 else None,
                    )
                except ValueError as json_err:
                    logger.warning(
                        f"JSON conversion failed for {agent_type} on attempt {attempt + 1}: {json_err}"
                    )
                    last_error = json_err

                    # 最終試行の場合、強制的に JSON に変換
                    if attempt == max_retries:
                        logger.error("Max retries reached, forcing JSON conversion")
                        forced_result = force_to_json_response(
                            result_cleaned,
                            error_context=f"{agent_type} agent after {max_retries + 1} attempts",
                            error_detail=str(json_err),
                        )
                        return JSONResponse(status_code=200, content=forced_result)
                    else:
                        # リトライ
                        logger.info(
                            f"Retrying... (attempt {attempt + 2}/{max_retries + 1})"
                        )
                        continue
            else:
                # force_json が False の場合は通常処理
                return ExpertAiAgentResponse(result=result_cleaned, type=agent_type)

        except Exception as e:
            last_error = e
            logger.error(
                f"Error on attempt {attempt + 1}/{max_retries + 1}: {e}", exc_info=True
            )

            # 最終試行の場合
            if attempt == max_retries:
                if request.force_json:
                    # force_json が True の場合は JSON エラーレスポンス
                    return JSONResponse(
                        status_code=500,
                        content={
                            "result": f"Error occurred after {max_retries + 1} attempts: {str(e)}",
                            "type": "error",
                            "agent_name": agent_name,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "attempts": max_retries + 1,
                            "is_json_guaranteed": True,
                        },
                    )
                else:
                    # 通常のエラーハンドリング
                    print(f"An unexpected error occurred: {e}")
                    raise HTTPException(
                        status_code=500,
                        detail="An internal server error occurred in the agent.",
                    ) from e
            else:
                # リトライ
                logger.info(
                    f"Retrying due to error... (attempt {attempt + 2}/{max_retries + 1})"
                )
                continue

    # ここには到達しないはずだが、念のため
    raise HTTPException(
        status_code=500, detail=f"Unexpected error after retries: {last_error}"
    )
