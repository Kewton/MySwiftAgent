from typing import Any, List, Literal

from pydantic import BaseModel


# チャットメッセージの形式を表すモデル
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class StandardAiAgentResponse(BaseModel):
    # result フィールドを ChatMessage モデルのリストとして定義
    result: List[ChatMessage]


class ExpertAiAgentRequest(BaseModel):
    user_input: str
    system_imput: str | None = None
    model_name: str | None = None
    project: str | None = None  # MyVault project name for secrets
    test_mode: bool = False  # Test mode flag for workflow development
    test_response: dict | str | None = None  # Test response data
    force_json: bool = True  # Force JSON response (default: True)
    max_retries: int = 2  # Maximum retry attempts for JSON conversion (default: 2)
    language: str | None = None  # Language parameter for some agents (e.g., wikipedia)


class ExpertAiAgentResponse(BaseModel):
    # result フィールドを ChatMessage モデルのリストとして定義
    result: str
    text: str | None = None
    type: str | None = None
    chathistory: List[ChatMessage] | None = None


class ExpertAiAgentResponseJson(BaseModel):
    # result can be either dict (JSON object) or list (JSON array)
    result: dict | list[Any]
    type: str | None = None
    chathistory: List[ChatMessage] | None = None
    attempts: int | None = None  # Number of retry attempts (if applicable)
    is_json_guaranteed: bool = True  # JSON guarantee flag
