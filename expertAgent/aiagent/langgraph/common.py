import logging
import operator
import re
from contextlib import asynccontextmanager
from typing import Annotated, Sequence, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage
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
from core.secrets import secrets_manager

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


# Make the graph with MCP context
@asynccontextmanager
async def make_graph(
    _mcpmodule: str = "mymcp.stdioall",
    _graphname: str = "Tool Agent",
    _model: str = settings.GRAPH_AGENT_MODEL,
    project: str | None = None,
):
    if _model is None:
        _model = settings.GRAPH_AGENT_MODEL

    if isChatGptAPI(_model) or isChatGPT_o(_model):
        model = ChatOpenAI(model=_model)
    elif isGemini(_model):
        # Lazy import to avoid loading Google credentials at module import time
        from langchain_google_genai import ChatGoogleGenerativeAI

        # Get API key from secrets_manager for Gemini
        try:
            google_api_key_for_model = secrets_manager.get_secret(
                "GOOGLE_API_KEY", project=project
            )
        except ValueError as e:
            raise ValueError(
                f"Failed to initialize Gemini model '{_model}': {e}. "
                f"Please ensure GOOGLE_API_KEY is set in MyVault for project: {project or 'default'}"
            ) from e
        model = ChatGoogleGenerativeAI(
            model=_model, google_api_key=google_api_key_for_model
        )
    elif isClaude(_model):
        model = ChatAnthropic(model=_model)
    else:
        model = ChatOllama(
            model=_model,
            base_url=settings.OLLAMA_URL,
        )

    # Get secrets from SecretsManager (MyVault priority)
    try:
        google_api_key = secrets_manager.get_secret("GOOGLE_API_KEY", project=project)
        print(
            f"[DEBUG make_graph] Retrieved GOOGLE_API_KEY: {google_api_key[:10]}..."
            if google_api_key
            else "[DEBUG make_graph] GOOGLE_API_KEY is empty"
        )
    except ValueError:
        google_api_key = ""
        print(
            "[DEBUG make_graph] Failed to retrieve GOOGLE_API_KEY - using empty string"
        )

    try:
        openai_api_key = secrets_manager.get_secret("OPENAI_API_KEY", project=project)
    except ValueError:
        openai_api_key = ""

    try:
        anthropic_api_key = secrets_manager.get_secret(
            "ANTHROPIC_API_KEY", project=project
        )
    except ValueError:
        anthropic_api_key = ""

    try:
        serper_api_key = secrets_manager.get_secret("SERPER_API_KEY", project=project)
    except ValueError:
        serper_api_key = ""

    try:
        mail_to = secrets_manager.get_secret("MAIL_TO", project=project)
    except ValueError:
        mail_to = ""

    try:
        podcast_model = secrets_manager.get_secret(
            "PODCAST_SCRIPT_DEFAULT_MODEL", project=project
        )
    except ValueError:
        podcast_model = ""

    try:
        spreadsheet_id = secrets_manager.get_secret("SPREADSHEET_ID", project=project)
    except ValueError:
        spreadsheet_id = ""

    try:
        ollama_url = secrets_manager.get_secret("OLLAMA_URL", project=project)
    except ValueError:
        ollama_url = settings.OLLAMA_URL

    try:
        ollama_model = secrets_manager.get_secret(
            "OLLAMA_DEF_SMALL_MODEL", project=project
        )
    except ValueError:
        ollama_model = ""

    import os

    # Resolve project name for Google APIs
    from core.google_creds import get_project_name

    resolved_project = get_project_name(project)

    mcp_env = {
        "GOOGLE_API_KEY": google_api_key,
        "OPENAI_API_KEY": openai_api_key,
        "ANTHROPIC_API_KEY": anthropic_api_key,
        "SERPER_API_KEY": serper_api_key,
        # ExpertAgent specific settings
        "MAIL_TO": mail_to,
        "PODCAST_SCRIPT_DEFAULT_MODEL": podcast_model,
        "SPREADSHEET_ID": spreadsheet_id,
        "OLLAMA_URL": ollama_url,
        "OLLAMA_DEF_SMALL_MODEL": ollama_model,
        "EXTRACT_KNOWLEDGE_MODEL": os.getenv(
            "EXTRACT_KNOWLEDGE_MODEL", settings.EXTRACT_KNOWLEDGE_MODEL
        ),
        "MLX_LLM_SERVER_URL": os.getenv(
            "MLX_LLM_SERVER_URL", settings.MLX_LLM_SERVER_URL
        ),
        # Google APIs project specification
        "GOOGLE_APIS_DEFAULT_PROJECT": resolved_project,
        # MyVault configuration for MCP subprocess
        "MYVAULT_ENABLED": "true" if settings.MYVAULT_ENABLED else "false",
        "MYVAULT_BASE_URL": settings.MYVAULT_BASE_URL,
        "MYVAULT_SERVICE_NAME": settings.MYVAULT_SERVICE_NAME,
        "MYVAULT_SERVICE_TOKEN": settings.MYVAULT_SERVICE_TOKEN,
        # Logging configuration for MCP subprocess
        "LOG_DIR": settings.LOG_DIR,
        "LOG_LEVEL": "DEBUG",  # Force DEBUG for MCP subprocess
        "MCP_LOG_FILE": "mcp_stdio.log",
    }

    logger.debug(f"mcp_env: {mcp_env}")

    print(
        f"[DEBUG] mcp_env GOOGLE_API_KEY: {mcp_env['GOOGLE_API_KEY'][:10]}..."
        if mcp_env["GOOGLE_API_KEY"]
        else "[DEBUG] mcp_env GOOGLE_API_KEY is empty"
    )

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
    project: str | None = None,
):
    # モデル選択は現状維持
    if _model is None:
        _model = settings.GRAPH_AGENT_MODEL

    if isChatGptAPI(_model) or isChatGPT_o(_model):
        model = ChatOpenAI(model=_model)
    elif isGemini(_model):
        # Lazy import to avoid loading Google credentials at module import time
        from langchain_google_genai import ChatGoogleGenerativeAI

        # Get API key from secrets_manager for Gemini
        try:
            google_api_key_for_model = secrets_manager.get_secret(
                "GOOGLE_API_KEY", project=project
            )
        except ValueError as e:
            raise ValueError(
                f"Failed to initialize Gemini model '{_model}': {e}. "
                f"Please ensure GOOGLE_API_KEY is set in MyVault for project: {project or 'default'}"
            ) from e
        model = ChatGoogleGenerativeAI(
            model=_model, google_api_key=google_api_key_for_model
        )
    elif isClaude(_model):
        model = ChatAnthropic(model=_model)
    else:
        model = ChatOllama(model=_model, base_url=settings.OLLAMA_URL)

    # Get secrets from SecretsManager (MyVault priority)
    try:
        google_api_key = secrets_manager.get_secret("GOOGLE_API_KEY", project=project)
    except ValueError:
        google_api_key = ""

    try:
        openai_api_key = secrets_manager.get_secret("OPENAI_API_KEY", project=project)
    except ValueError:
        openai_api_key = ""

    try:
        anthropic_api_key = secrets_manager.get_secret(
            "ANTHROPIC_API_KEY", project=project
        )
    except ValueError:
        anthropic_api_key = ""

    try:
        serper_api_key = secrets_manager.get_secret("SERPER_API_KEY", project=project)
    except ValueError:
        serper_api_key = ""

    try:
        mail_to = secrets_manager.get_secret("MAIL_TO", project=project)
    except ValueError:
        mail_to = ""

    try:
        podcast_model = secrets_manager.get_secret(
            "PODCAST_SCRIPT_DEFAULT_MODEL", project=project
        )
    except ValueError:
        podcast_model = ""

    try:
        spreadsheet_id = secrets_manager.get_secret("SPREADSHEET_ID", project=project)
    except ValueError:
        spreadsheet_id = ""

    try:
        ollama_url = secrets_manager.get_secret("OLLAMA_URL", project=project)
    except ValueError:
        ollama_url = settings.OLLAMA_URL

    try:
        ollama_model = secrets_manager.get_secret(
            "OLLAMA_DEF_SMALL_MODEL", project=project
        )
    except ValueError:
        ollama_model = ""

    import os

    # Resolve project name for Google APIs
    from core.google_creds import get_project_name

    resolved_project = get_project_name(project)

    mcp_env = {
        "GOOGLE_API_KEY": google_api_key,
        "OPENAI_API_KEY": openai_api_key,
        "ANTHROPIC_API_KEY": anthropic_api_key,
        "SERPER_API_KEY": serper_api_key,
        # ExpertAgent specific settings
        "MAIL_TO": mail_to,
        "PODCAST_SCRIPT_DEFAULT_MODEL": podcast_model,
        "SPREADSHEET_ID": spreadsheet_id,
        "OLLAMA_URL": ollama_url,
        "OLLAMA_DEF_SMALL_MODEL": ollama_model,
        "EXTRACT_KNOWLEDGE_MODEL": os.getenv(
            "EXTRACT_KNOWLEDGE_MODEL", settings.EXTRACT_KNOWLEDGE_MODEL
        ),
        "MLX_LLM_SERVER_URL": os.getenv(
            "MLX_LLM_SERVER_URL", settings.MLX_LLM_SERVER_URL
        ),
        # Google APIs project specification
        "GOOGLE_APIS_DEFAULT_PROJECT": resolved_project,
        # MyVault configuration for MCP subprocess
        "MYVAULT_ENABLED": "true" if settings.MYVAULT_ENABLED else "false",
        "MYVAULT_BASE_URL": settings.MYVAULT_BASE_URL,
        "MYVAULT_SERVICE_NAME": settings.MYVAULT_SERVICE_NAME,
        "MYVAULT_SERVICE_TOKEN": settings.MYVAULT_SERVICE_TOKEN,
        # Logging configuration for MCP subprocess
        "LOG_DIR": settings.LOG_DIR,
        "LOG_LEVEL": "DEBUG",  # Force DEBUG for MCP subprocess
        "MCP_LOG_FILE": "mcp_stdio.log",
    }

    print(
        f"[DEBUG] mcp_env GOOGLE_API_KEY: {mcp_env['GOOGLE_API_KEY'][:10]}..."
        if mcp_env["GOOGLE_API_KEY"]
        else "[DEBUG] mcp_env GOOGLE_API_KEY is empty"
    )

    print(
        f"[DEBUG] mcp_env GOOGLE_APIS_DEFAULT_PROJECT: {mcp_env['GOOGLE_APIS_DEFAULT_PROJECT'][:10]}..."
        if mcp_env["GOOGLE_APIS_DEFAULT_PROJECT"]
        else "[DEBUG] mcp_env GOOGLE_APIS_DEFAULT_PROJECT is empty"
    )

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


@asynccontextmanager
async def make_playwright_graph(
    _graphname: str = "Playwright Agent",
    _model: str = settings.GRAPH_AGENT_MODEL,
    _max_iterations: int | None = None,
):
    """Playwright MCP専用のグラフを作成します。

    Args:
        _graphname: グラフ名
        _model: 使用するモデル名
        _max_iterations: 最大試行回数
    """
    if _model is None:
        _model = settings.GRAPH_AGENT_MODEL

    if isChatGptAPI(_model) or isChatGPT_o(_model):
        model = ChatOpenAI(model=_model)
    elif isGemini(_model):
        # Lazy import to avoid loading Google credentials at module import time
        from langchain_google_genai import ChatGoogleGenerativeAI

        # Get API key from secrets_manager for Gemini
        try:
            google_api_key_for_model = secrets_manager.get_secret(
                "GOOGLE_API_KEY", project=None
            )
        except ValueError as e:
            raise ValueError(
                f"Failed to initialize Gemini model '{_model}': {e}. "
                "Please ensure GOOGLE_API_KEY is set in MyVault for default project"
            ) from e
        model = ChatGoogleGenerativeAI(
            model=_model, google_api_key=google_api_key_for_model
        )
    elif isClaude(_model):
        model = ChatAnthropic(model=_model)
    else:
        model = ChatOllama(model=_model, base_url=settings.OLLAMA_URL)

    # Playwright MCP client setup with headless mode and no-sandbox for Docker
    # Explicitly specify chromium browser for ARM64 compatibility
    mcp_client = MultiServerMCPClient(
        {
            "playwright": {
                "command": "npx",
                "args": [
                    "-y",
                    "@playwright/mcp@latest",
                    "--headless",
                    "--no-sandbox",
                    "--browser",
                    "chromium",
                ],
                "transport": "stdio",
            }
        }
    )

    mcp_tools = await mcp_client.get_tools()
    print(f"Available Playwright tools: {[tool.name for tool in mcp_tools]}")

    # ReAct エージェントを生成
    graph = create_react_agent(model, mcp_tools)

    # 最大試行回数を recursion_limit に反映
    if _max_iterations is not None:
        recursion_limit = 2 * _max_iterations + 1
        graph = graph.with_config(recursion_limit=recursion_limit, max_concurrency=2)

    graph.name = _graphname
    yield graph


@asynccontextmanager
async def make_wikipedia_graph(
    _graphname: str = "Wikipedia Agent",
    _model: str = settings.GRAPH_AGENT_MODEL,
    _max_iterations: int | None = None,
    _language: str = "ja",
):
    """Wikipedia MCP専用のグラフを作成します。

    Args:
        _graphname: グラフ名
        _model: 使用するモデル名
        _max_iterations: 最大試行回数
        _language: Wikipedia言語コード（デフォルト: ja）
    """
    if _model is None:
        _model = settings.GRAPH_AGENT_MODEL

    if isChatGptAPI(_model) or isChatGPT_o(_model):
        model = ChatOpenAI(model=_model)
    elif isGemini(_model):
        # Lazy import to avoid loading Google credentials at module import time
        from langchain_google_genai import ChatGoogleGenerativeAI

        # Get API key from secrets_manager for Gemini
        try:
            google_api_key_for_model = secrets_manager.get_secret(
                "GOOGLE_API_KEY", project=None
            )
        except ValueError as e:
            raise ValueError(
                f"Failed to initialize Gemini model '{_model}': {e}. "
                "Please ensure GOOGLE_API_KEY is set in MyVault for default project"
            ) from e
        model = ChatGoogleGenerativeAI(
            model=_model, google_api_key=google_api_key_for_model
        )
    elif isClaude(_model):
        model = ChatAnthropic(model=_model)
    else:
        model = ChatOllama(model=_model, base_url=settings.OLLAMA_URL)

    # Wikipedia MCP client setup with language support
    mcp_client = MultiServerMCPClient(
        {
            "wikipedia": {
                "command": "wikipedia-mcp",
                "args": ["--language", _language],
                "transport": "stdio",
            }
        }
    )

    mcp_tools = await mcp_client.get_tools()
    print(f"Available Wikipedia tools: {[tool.name for tool in mcp_tools]}")

    # ReAct エージェントを生成
    graph = create_react_agent(model, mcp_tools)

    # 最大試行回数を recursion_limit に反映
    if _max_iterations is not None:
        recursion_limit = 2 * _max_iterations + 1
        graph = graph.with_config(recursion_limit=recursion_limit, max_concurrency=2)

    graph.name = _graphname
    yield graph
