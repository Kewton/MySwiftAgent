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
        result = execLlmApi(model_name, messages)
        if result is None:
            result = "Error occurred"

        return self.response_builder.build_text_response(
            result=result,
            response_type="exec_myllm",
        )

    async def execute_sample_agent(self, request: ExpertAiAgentRequest):
        test_result = self.handle_test_mode(
            test_mode=request.test_mode,
            test_response=request.test_response,
            endpoint_name="sample",
        )
        if test_result is not None:
            return test_result

        prompt = self._build_prompt(request.user_input)

        max_attempts = 1
        if request.force_json:
            max_attempts = max(1, request.max_retries + 1)

        retry_config = RetryConfig(max_attempts=max_attempts)

        async def _operation() -> tuple[list[Any], Any]:
            from typing import cast

            result = await ainvoke_graphagent(prompt, project=request.project)
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

        chat_history, ai_message = retry_result.value
        chathistory_list = list(chat_history) if chat_history is not None else None

        if ai_message is None:
            raise AgentExecutionError(
                "Sample agent returned no response",
                context={"agent": "sample"},
            )

        attempts = retry_result.attempts if retry_result.attempts > 1 else None

        if request.force_json:
            return self.response_builder.build_json_response(
                raw=ai_message,
                response_type="sample",
                attempts=attempts,
                error_context="aiagent/sample",
                chathistory=chathistory_list,
            )

        return self.response_builder.build_text_response(
            result=str(ai_message),
            response_type="sample",
            chathistory=chathistory_list,
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
                )
                return self.response_builder.build_json_response(
                    raw=parsed_json,
                    response_type="jsonOutput",
                )

            if "explorer" in agent_name:
                ai_result = await exploreragent(
                    prompt,
                    model_name,
                    project=request.project,
                )
                agent_type = "explorer"
            elif "action" in agent_name:
                ai_result = await actionagent(
                    prompt,
                    model_name,
                    project=request.project,
                )
                agent_type = "action"
            elif "playwright" in agent_name:
                ai_result = await playwrightagent(prompt, model_name)
                agent_type = "playwright"
            elif "wikipedia" in agent_name:
                language = request.language or "ja"
                ai_result = await wikipediaagent(prompt, model_name, language)
                agent_type = "wikipedia"
            elif "file_reader" in agent_name or "filereader" in agent_name:
                ai_result = await filereaderagent(
                    prompt,
                    model_name,
                    project=request.project,
                )
                agent_type = "file_reader"
            else:
                return {"message": "No matching agent found."}
        except Exception as exc:  # pragma: no cover - defensive guard
            raise AgentExecutionError(
                "Failed to execute utility agent",
                context={"agent": agent_name},
            ) from exc

        if request.force_json:
            return self.response_builder.build_json_response(
                raw=ai_result,
                response_type=agent_type,
                error_context=f"{agent_type} agent",
            )

        return self.response_builder.build_text_response(
            result=str(ai_result),
            response_type=agent_type,
        )

    def _build_prompt(self, user_input: str) -> str:
        return (
            f"# メタ情報:\n- 現在の時刻は「{datetime.now()}」です。\n\n"
            f"# 指示書\n{user_input}"
        )
