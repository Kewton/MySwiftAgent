"""File Reader Agent

LangGraphを使用したFile Readerエージェント。
MCPツール（read_file_from_url, read_file_from_google_drive, read_file_from_local）を
使用してファイルを読み込み、処理結果を返します。
"""

from langchain_core.messages import AIMessage

from aiagent.langgraph.common import make_graph


async def filereaderagent(
    query: str, _modelname: str, project: str | None = None
) -> str:
    """File Readerエージェントを実行します。

    Args:
        query: ユーザーからの問い合わせ（ファイルパス/URLと指示を含む）
        _modelname: 使用するLLMモデル名（例: "gpt-4o", "gemini-1.5-flash"）
        project: プロジェクト名（MyVault認証用、デフォルトはNone）

    Returns:
        str: エージェントからの応答メッセージ

    Examples:
        >>> result = await filereaderagent(
        ...     "https://example.com/document.pdfの内容を要約してください",
        ...     "gpt-4o"
        ... )
        >>> print(result)
        "PDFの要約結果..."
    """
    async with make_graph(
        "mymcp.stdio_file_reader", "filereaderagent", _modelname, project=project
    ) as graph:
        result = await graph.ainvoke({"messages": query})
        aiMessage = ""
        for message in result.get("messages", []):
            if isinstance(message, AIMessage):
                aiMessage = str(message.content) if message.content else ""
        return aiMessage
