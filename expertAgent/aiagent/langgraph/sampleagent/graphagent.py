# graph.py
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.messages.tool import ToolMessage
from aiagent.langgraph.common import make_graph


# Run the graph with question
async def ainvoke_graphagent(query):
    chat_history = []
    chat_history.append({"role": "user", "content": query})
    async with make_graph() as graph:
        result = await graph.ainvoke({"messages": query})
        # 1. 'messages' キーでメッセージリストを取得
        message_list = result.get('messages', [])  # .get() を使うとキーが存在しない場合もエラーにならない

        # 2. リストが空でないことを確認し、最後のメッセージを取得
        final_output = {}
        humanMessage = ""
        aiMessage = ""
        toolMessages = []
        for message in message_list:
            print("~~~~")
            if isinstance(message, AIMessage):
                aiMessage = message.content
            elif isinstance(message, HumanMessage):
                humanMessage = message.content
            elif isinstance(message, ToolMessage):
                toolMessages.append({
                    "tool_call_id": message.tool_call_id,
                    "content": message.content,
                    "name": message.name if hasattr(message, 'name') else None
                })
            else:
                print("Unknown message type:", type(message))
                print(message)

        # final_output = {
        #     "humanMessage": humanMessage,
        #     "aiMessage": aiMessage,
        #     "toolMessages": toolMessages
        # }
        
        chat_history.append({"role": "assistant", "content": aiMessage})
        return chat_history, aiMessage
