from langchain_core.messages import AIMessage

from aiagent.langgraph.common import make_utility_graph


async def actionagent(query: str, _modelname: str, project: str | None = None) -> str:
    async with make_utility_graph(
        "mymcp.stdio_action",
        "actionagent",
        _modelname,
        _max_iterations=1,
        project=project,
    ) as graph:
        result = await graph.ainvoke({"messages": query})
        aiMessage = ""
        for message in result.get("messages", []):
            if isinstance(message, AIMessage) and isinstance(message.content, str):
                aiMessage = message.content
        return aiMessage
