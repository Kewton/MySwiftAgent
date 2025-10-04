from langchain_core.messages import AIMessage

from aiagent.langgraph.common import make_playwright_graph


async def playwrightagent(query: str, _modelname: str) -> str:
    """Playwright MCPを使用してWebページのスクレイピングやファイルダウンロードを実行します。

    Args:
        query: 実行するタスクの説明（例: "https://example.com のページ内容を取得してください"）
        _modelname: 使用するLLMモデル名

    Returns:
        str: 実行結果のメッセージ
    """
    async with make_playwright_graph(
        "playwrightagent", _modelname, 5
    ) as graph:
        result = await graph.ainvoke({"messages": query})
        aiMessage = ""
        for message in result.get("messages", []):
            if isinstance(message, AIMessage):
                aiMessage = message.content
        return aiMessage
