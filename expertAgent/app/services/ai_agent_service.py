"""Service objects handling LangGraph based agent execution."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from aiagent.langgraph.sampleagent.graphagent import ainvoke_graphagent
from aiagent.langgraph.utilityaiagents.action_agent import actionagent
from aiagent.langgraph.utilityaiagents.explorer_agent import exploreragent
from aiagent.langgraph.utilityaiagents.file_reader_agent import filereaderagent
from aiagent.langgraph.utilityaiagents.jsonOutput_agent import jsonOutputagent
from aiagent.langgraph.utilityaiagents.playwright_agent import playwrightagent
from aiagent.langgraph.utilityaiagents.wikipedia_agent import wikipediaagent
from app.exceptions import AgentExecutionError
from app.schemas.standardAiAgent import ChatMessage, ExpertAiAgentRequest
from app.services.langfuse_service import langfuse_service
from app.services.response_builder import ResponseBuilder
from mymcp.utils.execllm import execLlmApi

from .base import BaseService
from .retry_policies import RetryConfig

logger = logging.getLogger(__name__)


class AiAgentService(BaseService):
    """High level operations for AI agent endpoints."""

    def __init__(self) -> None:
        super().__init__(logger=logger, response_builder=ResponseBuilder())

    async def execute_myllm(self, request: ExpertAiAgentRequest):
        test_result = self.handle_test_mode(
            test_mode=request.test_mode,
            test_response=request.test_response,
            endpoint_name="mylllm",
        )
        if test_result is not None:
            return test_result

        messages: list[ChatMessage] = []
        if request.system_imput is not None:
            messages.append(
                ChatMessage(role="system", content=request.system_imput),
            )
        messages.append(ChatMessage(role="user", content=request.user_input))

        model_name = request.model_name or "gpt-4o-mini"

        # Langfuse トレーシング（直接API呼び出し用）
        trace_id = None
        if langfuse_service._is_enabled() and langfuse_service._client:
            try:
                # Langfuse v3: トレースIDを生成
                trace_id = langfuse_service._client.create_trace_id()

                # ジェネレーションを開始
                # Note: Langfuse SDK v3のAPI仕様により、trace_idの渡し方が変更される可能性あり
                langfuse_service._client.start_as_current_generation(  # type: ignore[call-arg]
                    trace_id=trace_id,
                    name="llm_call",
                    model=model_name,
                    input=[msg.model_dump() for msg in messages],
                    metadata={
                        "endpoint": "exec_myllm",
                        "user_id": request.user_id,
                        "session_id": request.session_id,
                    },
                )

                # LLM API呼び出し
                result = execLlmApi(model_name, messages)

                # 結果を記録
                langfuse_service._client.update_current_generation(
                    output=result if result else "Error occurred",
                    level="ERROR" if not result else None,
                )

                langfuse_service.flush()

            except Exception as e:
                self.logger.error(f"Langfuse tracing failed: {e}")
                # トレーシング失敗時もLLM呼び出しは実行
                result = execLlmApi(model_name, messages)
        else:
            # Langfuse無効時は通常のLLM呼び出し
            result = execLlmApi(model_name, messages)

        if result is None:
            result = "Error occurred"

        return self.response_builder.build_text_response(
            result=result,
            response_type="exec_myllm",
            trace_id=trace_id,
        )

    async def execute_sample_agent(self, request: ExpertAiAgentRequest):
        test_result = self.handle_test_mode(
            test_mode=request.test_mode,
            test_response=request.test_response,
            endpoint_name="sample",
        )
        if test_result is not None:
            return test_result

        # Langfuse CallbackHandler生成
        langfuse_handler = langfuse_service.get_callback_handler(
            trace_name="sample_agent",
            user_id=request.user_id,
            session_id=request.session_id,
            tags=["sample", "graph_agent"],
            metadata={
                "model": request.model_name or "default",
                "force_json": request.force_json,
                "project": request.project,
            },
        )

        prompt = self._build_prompt(request.user_input)

        max_attempts = 1
        if request.force_json:
            max_attempts = max(1, request.max_retries + 1)

        retry_config = RetryConfig(max_attempts=max_attempts)

        # CallbackHandlerをconfigに追加
        langchain_config = {}
        if langfuse_handler:
            langchain_config["callbacks"] = [langfuse_handler]

        async def _operation() -> tuple[list[Any], Any]:
            from typing import cast

            # LangGraphエージェント呼び出しにconfigを渡す
            # 注: ainvoke_graphagentがconfigをサポートしている必要がある
            result = await ainvoke_graphagent(
                prompt,
                project=request.project,
                config=langchain_config if langchain_config else None,
            )
            return cast(tuple[list[Any], Any], result)

        try:
            retry_result = await retry_config.run_async(
                _operation,
                logger=self.logger,
            )
        except Exception as exc:
            raise AgentExecutionError(
                "Failed to execute sample agent",
                context={"agent": "sample"},
            ) from exc
        finally:
            # トレースをフラッシュ
            if langfuse_handler:
                langfuse_service.flush()

        chat_history, ai_message = retry_result.value
        chathistory_list = list(chat_history) if chat_history is not None else None

        if ai_message is None:
            raise AgentExecutionError(
                "Sample agent returned no response",
                context={"agent": "sample"},
            )

        attempts = retry_result.attempts if retry_result.attempts > 1 else None

        # trace_idを取得（Langfuse CallbackHandlerから）
        trace_id = None
        if langfuse_handler and hasattr(langfuse_handler, "last_trace_id"):
            trace_id = langfuse_handler.last_trace_id

        if request.force_json:
            return self.response_builder.build_json_response(
                raw=ai_message,
                response_type="sample",
                attempts=attempts,
                error_context="aiagent/sample",
                chathistory=chathistory_list,
                trace_id=trace_id,
            )

        return self.response_builder.build_text_response(
            result=str(ai_message),
            response_type="sample",
            chathistory=chathistory_list,
            trace_id=trace_id,
        )

    async def execute_utility_agent(
        self,
        agent_name: str,
        request: ExpertAiAgentRequest,
    ):
        test_result = self.handle_test_mode(
            test_mode=request.test_mode,
            test_response=request.test_response,
            endpoint_name=agent_name,
        )
        if test_result is not None:
            return test_result

        # Langfuse CallbackHandler生成
        langfuse_handler = langfuse_service.get_callback_handler(
            trace_name=f"utility_agent_{agent_name}",
            user_id=request.user_id,
            session_id=request.session_id,
            tags=["utility", agent_name],
            metadata={
                "model": request.model_name or "gpt-4o-mini",
                "force_json": request.force_json,
                "project": request.project,
                "agent_name": agent_name,
            },
        )

        # CallbackHandlerをconfigに追加
        langchain_config = {}
        if langfuse_handler:
            langchain_config["callbacks"] = [langfuse_handler]

        prompt = self._build_prompt(request.user_input)
        model_name = request.model_name or "gpt-4o-mini"

        agent_type = "generic"
        ai_result: str | Any

        try:
            if "jsonoutput" in agent_name:
                parsed_json = await jsonOutputagent(
                    prompt,
                    model_name,
                    project=request.project,
                    config=langchain_config if langchain_config else None,
                )
                # trace_idを取得
                trace_id = None
                if langfuse_handler and hasattr(langfuse_handler, "last_trace_id"):
                    trace_id = langfuse_handler.last_trace_id

                return self.response_builder.build_json_response(
                    raw=parsed_json,
                    response_type="jsonOutput",
                    trace_id=trace_id,
                )

            if "explorer" in agent_name:
                ai_result = await exploreragent(
                    prompt,
                    model_name,
                    project=request.project,
                    config=langchain_config if langchain_config else None,
                )
                agent_type = "explorer"
            elif "action" in agent_name:
                ai_result = await actionagent(
                    prompt,
                    model_name,
                    project=request.project,
                    config=langchain_config if langchain_config else None,
                )
                agent_type = "action"
            elif "playwright" in agent_name:
                ai_result = await playwrightagent(
                    prompt,
                    model_name,
                    config=langchain_config if langchain_config else None,
                )
                agent_type = "playwright"
            elif "wikipedia" in agent_name:
                language = request.language or "ja"
                ai_result = await wikipediaagent(
                    prompt,
                    model_name,
                    language,
                    config=langchain_config if langchain_config else None,
                )
                agent_type = "wikipedia"
            elif "file_reader" in agent_name or "filereader" in agent_name:
                ai_result = await filereaderagent(
                    prompt,
                    model_name,
                    project=request.project,
                    config=langchain_config if langchain_config else None,
                )
                agent_type = "file_reader"
            else:
                return {"message": "No matching agent found."}
        except Exception as exc:  # pragma: no cover - defensive guard
            raise AgentExecutionError(
                "Failed to execute utility agent",
                context={"agent": agent_name},
            ) from exc
        finally:
            # トレースをフラッシュ
            if langfuse_handler:
                langfuse_service.flush()

        # trace_idを取得
        trace_id = None
        if langfuse_handler and hasattr(langfuse_handler, "last_trace_id"):
            trace_id = langfuse_handler.last_trace_id

        if request.force_json:
            return self.response_builder.build_json_response(
                raw=ai_result,
                response_type=agent_type,
                error_context=f"{agent_type} agent",
                trace_id=trace_id,
            )

        return self.response_builder.build_text_response(
            result=str(ai_result),
            response_type=agent_type,
            trace_id=trace_id,
        )

    def _build_prompt(self, user_input: str) -> str:
        return (
            f"# メタ情報:\n- 現在の時刻は「{datetime.now()}」です。\n\n"
            f"# 指示書\n{user_input}"
        )
