import json
import re
from aiagent.langgraph.util import isChatGptAPI, isGemini, isChatGPT_o, isClaude
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import JsonOutputParser
from core.config import settings
from aiagent.langgraph.common import remove_think_tags
from langchain_core.messages import AIMessage
from aiagent.langgraph.common import make_utility_graph


async def jsonOutputagent(query: str, _modelname: str = "gpt-4o-mini") -> dict:
    async with make_utility_graph("mymcp.stdio_explorer", "exploreragent", _modelname, 2) as graph:
        print(f"mymcp.stdio_explorer start query:{query}")
        result = await graph.ainvoke({"messages": query})
        aiMessage = ""
        for message in result.get('messages', []):
            if isinstance(message, AIMessage):
                aiMessage = message.content
                aiMessage = remove_think_tags(aiMessage)
                char_count = len(aiMessage.replace(" ", "").replace("\n", "").replace("\t", ""))
                if char_count > 0:
                    print(f"before parse_json: {aiMessage}")
                    aiMessage = toParseJson(aiMessage)
                    print(f"after parse_json: {aiMessage}")
        return aiMessage


async def jsonOutputagent_old(query: str, _model: str = "gpt-4o-mini") -> dict:
    if _model is None:
        _model = "gpt-4o-mini"
        
    if isChatGptAPI(_model) or isChatGPT_o(_model):
        llm_openai = ChatOpenAI(model=_model, temperature=0.3)
    elif isGemini(_model):
        # gemini-2.5-flash-preview-04-17
        llm_openai = ChatGoogleGenerativeAI(model=_model)
    elif isClaude(_model):
        llm_openai = ChatAnthropic(model=_model)
    else:
        llm_openai = ChatOllama(
            model=_model,
            base_url=settings.OLLAMA_URL,
        )

    # llm_openai = ChatOpenAI(model=_model, temperature=0.3)
    outline_json = (await llm_openai.ainvoke(query)).content
    outline_json = remove_think_tags(outline_json)
    print("~~~~ outline_json [start]~~~~")
    print(outline_json)
    print("~~~~ outline_json [end]~~~~")

    parser = JsonOutputParser()
    try:
        parsed_json = parser.parse(outline_json)
    except Exception as e:
        print(f"Error parsing JSON with JsonOutputParser: {e}")
        # --- (または、正規表現を使用する場合) ---
        match = re.search(r"```json\s*(\{.*?\})\s*```", outline_json, re.DOTALL)
        if match:
            json_content = match.group(1)
            try:
                parsed_json = json.loads(json_content)
            except json.JSONDecodeError as e:
                print(f"JSONDecodeError after regex extraction: {e}")
                raise
            except KeyError as e:
                print(f"KeyError: {e}. 'outline' key not found.")
                raise
        else:
            print("Could not extract JSON block using regex.")
            # JSONブロックが見つからない場合のエラーハンドリング
            raise ValueError("Failed to extract JSON block from LLM response.")

    return parsed_json


def toParseJson(outline_json):
    parser = JsonOutputParser()
    try:
        parsed_json = parser.parse(outline_json)
    except Exception as e:
        print(f"Error parsing JSON with JsonOutputParser: {e}")
        # --- (または、正規表現を使用する場合) ---
        match = re.search(r"```json\s*(\{.*?\})\s*```", outline_json, re.DOTALL)
        if match:
            json_content = match.group(1)
            try:
                parsed_json = json.loads(json_content)
            except json.JSONDecodeError as e:
                print(f"JSONDecodeError after regex extraction: {e}")
                raise
            except KeyError as e:
                print(f"KeyError: {e}. 'outline' key not found.")
                raise
        else:
            print("Could not extract JSON block using regex.")
            # JSONブロックが見つからない場合のエラーハンドリング
            raise ValueError("Failed to extract JSON block from LLM response.")
    return parsed_json
