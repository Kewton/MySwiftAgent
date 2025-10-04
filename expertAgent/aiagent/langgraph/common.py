import operator
import re
from contextlib import asynccontextmanager
from typing import Annotated, Sequence, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from aiagent.langgraph.util import (
    isChatGPT_o,
    isChatGptAPI,
    isClaude,
    isGemini,
)
from core.config import settings


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


# Make the graph with MCP context
@asynccontextmanager
async def make_graph(
    _mcpmodule: str = "mymcp.stdioall",
    _graphname: str = "Tool Agent",
    _model: str = settings.GRAPH_AGENT_MODEL,
):
    if _model is None:
        _model = settings.GRAPH_AGENT_MODEL

    if isChatGptAPI(_model) or isChatGPT_o(_model):
        model = ChatOpenAI(model=_model)
    elif isGemini(_model):
        # gemini-2.5-flash-preview-04-17
        model = ChatGoogleGenerativeAI(model=_model)
    elif isClaude(_model):
        model = ChatAnthropic(model=_model)
    else:
        model = ChatOllama(
            model=_model,
            base_url=settings.OLLAMA_URL,
        )

    import os
    mcp_env = {
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY", settings.GOOGLE_API_KEY),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", settings.OPENAI_API_KEY),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", settings.ANTHROPIC_API_KEY),
        "SERPER_API_KEY": os.getenv("SERPER_API_KEY", settings.SERPER_API_KEY),
        # ExpertAgent specific settings
        "MAIL_TO": os.getenv("MAIL_TO", settings.MAIL_TO),
        "PODCAST_SCRIPT_DEFAULT_MODEL": os.getenv("PODCAST_SCRIPT_DEFAULT_MODEL", settings.PODCAST_SCRIPT_DEFAULT_MODEL),
        "SPREADSHEET_ID": os.getenv("SPREADSHEET_ID", settings.SPREADSHEET_ID),
        "OLLAMA_URL": os.getenv("OLLAMA_URL", settings.OLLAMA_URL),
        "OLLAMA_DEF_SMALL_MODEL": os.getenv("OLLAMA_DEF_SMALL_MODEL", settings.OLLAMA_DEF_SMALL_MODEL),
        "EXTRACT_KNOWLEDGE_MODEL": os.getenv("EXTRACT_KNOWLEDGE_MODEL", settings.EXTRACT_KNOWLEDGE_MODEL),
        "MLX_LLM_SERVER_URL": os.getenv("MLX_LLM_SERVER_URL", settings.MLX_LLM_SERVER_URL),
        "GOOGLE_APIS_TOKEN_PATH": os.getenv("GOOGLE_APIS_TOKEN_PATH", settings.GOOGLE_APIS_TOKEN_PATH),
        "GOOGLE_APIS_CREDENTIALS_PATH": os.getenv("GOOGLE_APIS_CREDENTIALS_PATH", settings.GOOGLE_APIS_CREDENTIALS_PATH),
    }

    mcp_client = MultiServerMCPClient(
        {
            "my-mcp-tool": {
                "command": "uv",
                "args": ["run", "python", "-m", _mcpmodule],
                "transport": "stdio",
                "env": mcp_env,
            }
        }
    )

    mcp_tools = await mcp_client.get_tools()
    print(f"Available tools: {[tool.name for tool in mcp_tools]}")
    graph = create_react_agent(model, mcp_tools)

    # graph = graph_builder.compile()
    graph.name = _graphname

    yield graph


class ReactAgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]


@asynccontextmanager
async def make_utility_graph(
    _mcpmodule: str = "mymcp.stdioall",
    _graphname: str = "Tool Agent",
    _model: str = settings.GRAPH_AGENT_MODEL,
    _max_iterations: int | None = None,  # ★ 追加
):
    # モデル選択は現状維持
    if _model is None:
        _model = settings.GRAPH_AGENT_MODEL

    if isChatGptAPI(_model) or isChatGPT_o(_model):
        model = ChatOpenAI(model=_model)
    elif isGemini(_model):
        model = ChatGoogleGenerativeAI(model=_model)
    elif isClaude(_model):
        model = ChatAnthropic(model=_model)
    else:
        model = ChatOllama(model=_model, base_url=settings.OLLAMA_URL)

    # MCP クライアント with environment variables
    import os
    mcp_env = {
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY", settings.GOOGLE_API_KEY),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", settings.OPENAI_API_KEY),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", settings.ANTHROPIC_API_KEY),
        "SERPER_API_KEY": os.getenv("SERPER_API_KEY", settings.SERPER_API_KEY),
        # ExpertAgent specific settings
        "MAIL_TO": os.getenv("MAIL_TO", settings.MAIL_TO),
        "PODCAST_SCRIPT_DEFAULT_MODEL": os.getenv("PODCAST_SCRIPT_DEFAULT_MODEL", settings.PODCAST_SCRIPT_DEFAULT_MODEL),
        "SPREADSHEET_ID": os.getenv("SPREADSHEET_ID", settings.SPREADSHEET_ID),
        "OLLAMA_URL": os.getenv("OLLAMA_URL", settings.OLLAMA_URL),
        "OLLAMA_DEF_SMALL_MODEL": os.getenv("OLLAMA_DEF_SMALL_MODEL", settings.OLLAMA_DEF_SMALL_MODEL),
        "EXTRACT_KNOWLEDGE_MODEL": os.getenv("EXTRACT_KNOWLEDGE_MODEL", settings.EXTRACT_KNOWLEDGE_MODEL),
        "MLX_LLM_SERVER_URL": os.getenv("MLX_LLM_SERVER_URL", settings.MLX_LLM_SERVER_URL),
        "GOOGLE_APIS_TOKEN_PATH": os.getenv("GOOGLE_APIS_TOKEN_PATH", settings.GOOGLE_APIS_TOKEN_PATH),
        "GOOGLE_APIS_CREDENTIALS_PATH": os.getenv("GOOGLE_APIS_CREDENTIALS_PATH", settings.GOOGLE_APIS_CREDENTIALS_PATH),
    }

    mcp_client = MultiServerMCPClient(
        {
            "my-mcp-tool": {
                "command": "uv",
                "args": ["run", "python", "-m", _mcpmodule],
                "transport": "stdio",
                "env": mcp_env,
            }
        }
    )

    mcp_tools = await mcp_client.get_tools()
    print(f"Available tools: {[tool.name for tool in mcp_tools]}")

    # ReAct エージェントを生成
    graph = create_react_agent(model, mcp_tools)

    # 最大試行回数を recursion_limit に反映
    if _max_iterations is not None:
        # LangGraph では「1 思考 + 1 ツール実行」を 2 ステップと数えるので、
        # 推奨式  recursion_limit = 2 * max_iterations + 1
        recursion_limit = 2 * _max_iterations + 1
        graph = graph.with_config(recursion_limit=recursion_limit, max_concurrency=2)

    graph.name = _graphname
    yield graph
