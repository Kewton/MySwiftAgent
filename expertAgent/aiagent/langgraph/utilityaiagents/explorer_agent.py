from langchain_core.messages import AIMessage

from aiagent.langgraph.common import make_utility_graph


async def exploreragent(
    query: str, _modelname: str, project: str | None = None
) -> str:
    async with make_utility_graph(
        "mymcp.stdio_explorer", "exploreragent", _modelname, 2, project=project
    ) as graph:
        result = await graph.ainvoke({"messages": query})
        aiMessage = ""
        for message in result.get("messages", []):
            if isinstance(message, AIMessage):
                aiMessage = message.content
        return aiMessage
