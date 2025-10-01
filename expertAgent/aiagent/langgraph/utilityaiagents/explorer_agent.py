from langchain_core.messages import AIMessage
from aiagent.langgraph.common import make_graph, make_utility_graph


async def exploreragent(query: str, _modelname: str) -> str:
    async with make_utility_graph("mymcp.stdio_explorer", "exploreragent", _modelname, 2) as graph:
        result = await graph.ainvoke({"messages": query})
        aiMessage = ""
        for message in result.get('messages', []):
            if isinstance(message, AIMessage):
                aiMessage = message.content
        return aiMessage
