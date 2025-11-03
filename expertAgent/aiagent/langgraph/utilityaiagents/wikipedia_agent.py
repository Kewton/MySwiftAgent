from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from aiagent.langgraph.common import make_wikipedia_graph


async def wikipediaagent(query: str, _modelname: str, language: str = "ja") -> str:
    """Wikipedia MCPを使用してWikipedia記事の検索・取得を実行します。

    Args:
        query: 実行するタスクの説明（例: "日本の歴史について教えてください"）
        _modelname: 使用するLLMモデル名
        language: Wikipedia言語コード（デフォルト: ja）

    Returns:
        str: 実行結果のメッセージ
    """
    # System message to inform Wikipedia capabilities
    system_msg = SystemMessage(
        content=f"""You are a Wikipedia research assistant with access to Wikipedia tools.
Language: {language}
Available capabilities:
- Search Wikipedia articles
- Retrieve full article content
- Get article summaries
- Extract specific sections
- Find related topics and links

Provide comprehensive and accurate information from Wikipedia."""
    )

    human_msg = HumanMessage(content=query)

    async with make_wikipedia_graph(
        "wikipediaagent", _modelname, 15, language
    ) as graph:
        result = await graph.ainvoke({"messages": [system_msg, human_msg]})
        aiMessage = ""
        for message in result.get("messages", []):
            if isinstance(message, AIMessage) and isinstance(message.content, str):
                aiMessage = message.content
        return aiMessage
