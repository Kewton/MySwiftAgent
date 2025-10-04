from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from aiagent.langgraph.common import make_playwright_graph


async def playwrightagent(query: str, _modelname: str) -> str:
    """Playwright MCPを使用してWebページのスクレイピングやファイルダウンロードを実行します。

    Args:
        query: 実行するタスクの説明（例: "https://example.com のページ内容を取得してください"）
        _modelname: 使用するLLMモデル名

    Returns:
        str: 実行結果のメッセージ
    """
    # System message to inform that browser is already installed
    system_msg = SystemMessage(content="""IMPORTANT: Chromium browser is already installed and ready to use.
Do NOT use browser_install tool. Start directly with browser_navigate to access web pages.
Environment: Linux ARM64 with Chromium headless browser pre-installed.""")

    human_msg = HumanMessage(content=query)

    async with make_playwright_graph(
        "playwrightagent", _modelname, 5
    ) as graph:
        result = await graph.ainvoke({"messages": [system_msg, human_msg]})
        aiMessage = ""
        for message in result.get("messages", []):
            if isinstance(message, AIMessage):
                aiMessage = message.content
        return aiMessage
