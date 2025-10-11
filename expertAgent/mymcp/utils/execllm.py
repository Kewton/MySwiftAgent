import logging
from typing import List, Optional

import google.generativeai as genai
from openai import OpenAI

from app.schemas.standardAiAgent import ChatMessage
from core.secrets import secrets_manager
from mymcp.utils.chatollama import chatOllama

logger = logging.getLogger(__name__)

# Lazy initialization - clients are created when first used
_chatgpt_client = None
_genai_configured = False


def get_chatgpt_client() -> OpenAI:
    """Get or create OpenAI client with API key from SecretsManager."""
    global _chatgpt_client
    if _chatgpt_client is None:
        logger.info("Initializing OpenAI client")
        api_key = secrets_manager.get_secret("OPENAI_API_KEY")
        _chatgpt_client = OpenAI(api_key=api_key)
        logger.debug("OpenAI client initialized successfully")
    return _chatgpt_client


def configure_genai() -> None:
    """Configure Google Generative AI with API key from SecretsManager."""
    global _genai_configured
    if not _genai_configured:
        logger.info("Configuring Google Generative AI")
        api_key = secrets_manager.get_secret("GOOGLE_API_KEY")
        genai.configure(api_key=api_key)
        _genai_configured = True
        logger.debug("Google Generative AI configured successfully")


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
                logger.debug("Appending image to message content")
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
    """
    Build messages in Gemini API format from ChatMessage objects.

    Args:
        _messages: List of ChatMessage Pydantic models

    Returns:
        Tuple of (contents_for_api, system_instruction)
    """
    system_instruction = None
    contents_for_api = []

    for msg in _messages:
        # Convert ChatMessage object to dict
        msg_dict = msg.model_dump()
        role = msg_dict.get("role")
        content = msg_dict.get("content")

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


def execLlmApi(_selected_model: str, _messages: List[ChatMessage]) -> Optional[str]:
    """
    Execute LLM API call with the specified model and messages.

    Args:
        _selected_model: Model name/identifier (e.g., "gpt-4o", "gemini-1.5-flash", "ollama:model")
        _messages: List of ChatMessage Pydantic objects

    Returns:
        Optional[str]: Generated response text, or None if generation fails

    Note:
        Phase 3: Type-safe design - only accepts ChatMessage objects.
        All messages must be ChatMessage instances with 'role' and 'content' fields.
    """
    logger.info(f"Executing LLM API call with model: {_selected_model}")
    logger.debug(f"Number of messages: {len(_messages)}")

    # Convert ChatMessage objects to dictionaries for API calls
    messages_dict = [msg.model_dump() for msg in _messages]

    if isChatGptAPI(_selected_model) or isChatGPT_o(_selected_model):
        logger.info(f"Using ChatGPT API with model: {_selected_model}")
        client = get_chatgpt_client()
        response = client.chat.completions.create(
            model=_selected_model, messages=messages_dict  # type: ignore[arg-type]
        )
        result = response.choices[0].message.content
        logger.info(
            f"ChatGPT API call completed successfully. Response length: {len(result) if result else 0}"
        )
        return result

    elif isGemini(_selected_model):
        logger.info(f"Using Google Gemini API with model: {_selected_model}")
        configure_genai()
        _inpurt_messages, _systemrole = buildInpurtMessagesForGemini(_messages)
        logger.debug(
            f"System instruction length: {len(_systemrole) if _systemrole else 0}"
        )
        # モデル名を有効なものにすること！ (例: "gemini-1.5-flash-latest")
        model = genai.GenerativeModel(
            model_name=_selected_model,  # ★★★ モデル名を有効なものに！ ★★★
            system_instruction=_systemrole,
        )
        gemini_response = model.generate_content(_inpurt_messages)
        gemini_result: Optional[str] = gemini_response.text
        logger.info(
            f"Gemini API call completed successfully. Response length: {len(gemini_result) if gemini_result else 0}"
        )
        return gemini_result

    else:
        # Ollama APIを使用してチャットを行う関数
        logger.info(f"Using Ollama API with model: {_selected_model}")
        # messages_dict is already normalized to dictionary format
        result = chatOllama(messages_dict, _selected_model)
        logger.info(
            f"Ollama API call completed successfully. Response length: {len(result) if result else 0}"
        )
        return result
