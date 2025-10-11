from typing import List, Literal

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


class ExpertAiAgentResponse(BaseModel):
    # result フィールドを ChatMessage モデルのリストとして定義
    result: str
    text: str | None = None
    type: str | None = None
    chathistory: List[ChatMessage] | None = None


class ExpertAiAgentResponseJson(BaseModel):
    # result フィールドを ChatMessage モデルのリストとして定義
    result: dict
    type: str | None = None
    chathistory: List[ChatMessage] | None = None
