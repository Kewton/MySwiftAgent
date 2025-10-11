from langchain_core.messages import AIMessage

from aiagent.langgraph.common import make_graph


async def actionagent(query: str, _modelname: str, project: str | None = None) -> str:
    async with make_graph(
        "mymcp.stdio_action", "actionagent", _modelname, project=project
    ) as graph:
        result = await graph.ainvoke({"messages": query})
        aiMessage = ""
        for message in result.get("messages", []):
            if isinstance(message, AIMessage):
                aiMessage = message.content
        return aiMessage
