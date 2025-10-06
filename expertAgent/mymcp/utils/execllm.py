from typing import List

import google.generativeai as genai
from openai import OpenAI

from app.schemas.standardAiAgent import ChatMessage
from core.secrets import secrets_manager
from mymcp.utils.chatollama import chatOllama

# Lazy initialization - clients are created when first used
_chatgpt_client = None
_genai_configured = False


def get_chatgpt_client() -> OpenAI:
    """Get or create OpenAI client with API key from SecretsManager."""
    global _chatgpt_client
    if _chatgpt_client is None:
        api_key = secrets_manager.get_secret("OPENAI_API_KEY")
        _chatgpt_client = OpenAI(api_key=api_key)
    return _chatgpt_client


def configure_genai() -> None:
    """Configure Google Generative AI with API key from SecretsManager."""
    global _genai_configured
    if not _genai_configured:
        api_key = secrets_manager.get_secret("GOOGLE_API_KEY")
        genai.configure(api_key=api_key)
        _genai_configured = True


def isChatGptAPI(_selected_model):
    if "gpt" in _selected_model:
        return True
    else:
        return False


def isChatGPT_o(_selected_model):
    if "o1" in _selected_model:
        return True
    elif "o3" in _selected_model:
        return True
    else:
        return False


def isChatGPTImageAPI(_selected_model):
    if "gpt-4o" in _selected_model:
        return True
    elif "o1" in _selected_model:
        return True
    elif "o3" in _selected_model:
        return True
    else:
        return False


def isGemini(_selected_model):
    if "gemini" in _selected_model:
        return True
    else:
        return False


def buildInpurtMessages(_messages, encoded_file):
    _inpurt_messages = []
    _systemrole = ""
    for _rec in _messages:
        if _rec["role"] == "system":
            _systemrole = _rec["content"]
        elif _rec["role"] == "user":
            if len(encoded_file) > 0:
                print("append image")
                _content = []
                _content.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": encoded_file,
                        },
                    }
                )
                _content.append({"type": "text", "text": _rec["content"]})

                _inpurt_messages.append({"role": _rec["role"], "content": _content})
            else:
                _inpurt_messages.append(_rec)

    return _inpurt_messages, _systemrole


def buildInpurtMessagesForGemini(_messages: List[ChatMessage]):
    system_instruction = None
    contents_for_api = []

    for msg in _messages:
        role = msg.get("role")
        content = msg.get("content")
        if not role or not content:
            continue

        if role == "system":
            system_instruction = content
        elif role == "user":
            # 正しい形式: 'parts' キーの中に {'text': ...} のリストを入れる
            contents_for_api.append({"role": "user", "parts": [{"text": content}]})
        elif role == "assistant" or role == "model":
            # 正しい形式: 'parts' キーの中に {'text': ...} のリストを入れる
            contents_for_api.append({"role": "model", "parts": [{"text": content}]})

    return contents_for_api, system_instruction


def execLlmApi(_selected_model: str, _messages: List[ChatMessage]):
    if isChatGptAPI(_selected_model) or isChatGPT_o(_selected_model):
        client = get_chatgpt_client()
        response = client.chat.completions.create(
            model=_selected_model, messages=_messages
        )
        return response.choices[0].message.content

    elif isGemini(_selected_model):
        configure_genai()
        _inpurt_messages, _systemrole = buildInpurtMessagesForGemini(_messages)
        # モデル名を有効なものにすること！ (例: "gemini-1.5-flash-latest")
        model = genai.GenerativeModel(
            model_name=_selected_model,  # ★★★ モデル名を有効なものに！ ★★★
            system_instruction=_systemrole,
        )
        response = model.generate_content(_inpurt_messages)
        return response.text

    else:
        # Ollama APIを使用してチャットを行う関数
        return chatOllama(_messages, _selected_model)
