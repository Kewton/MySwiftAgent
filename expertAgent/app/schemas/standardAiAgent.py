"""Schema definitions for Standard AI Agent API.

Issue #333: Added system_prompt field and backward compatibility for system_imput.
"""

import warnings
from typing import Any, List, Literal

from pydantic import BaseModel, model_validator


# チャットメッセージの形式を表すモデル
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class StandardAiAgentResponse(BaseModel):
    # result フィールドを ChatMessage モデルのリストとして定義
    result: List[ChatMessage]


class ExpertAiAgentRequest(BaseModel):
    """Expert AI Agent request schema.

    Issue #333: Added system_prompt as the correct field name.
    system_imput is kept for backward compatibility but is deprecated.
    """

    user_input: str
    # Issue #333: system_prompt is the correct field name
    system_prompt: str | None = None
    # Issue #333: Backward compatibility - system_imput is deprecated
    system_imput: str | None = None
    model_name: str | None = None
    project: str | None = None  # MyVault project name for secrets
    test_mode: bool = False  # Test mode flag for workflow development
    test_response: dict | str | None = None  # Test response data
    force_json: bool = True  # Force JSON response (default: True)
    max_retries: int = 2  # Maximum retry attempts for JSON conversion (default: 2)
    language: str | None = None  # Language parameter for some agents (e.g., wikipedia)
    user_id: str | None = None  # User ID for Langfuse tracing (Issue #113)
    session_id: str | None = None  # Session ID for Langfuse tracing (Issue #113)

    @model_validator(mode="before")
    @classmethod
    def handle_system_imput_deprecation(cls, data: Any) -> Any:
        """Handle deprecated system_imput field.

        Issue #333: Map system_imput to system_prompt for backward compatibility.
        system_prompt takes precedence if both are provided.
        """
        if isinstance(data, dict):
            system_imput = data.get("system_imput")
            system_prompt = data.get("system_prompt")

            # If system_imput is provided but system_prompt is not, use system_imput
            if system_imput is not None and system_prompt is None:
                warnings.warn(
                    "system_imput is deprecated, use system_prompt instead",
                    DeprecationWarning,
                    stacklevel=2,
                )
                data["system_prompt"] = system_imput

        return data


class ExpertAiAgentResponse(BaseModel):
    # result フィールドを ChatMessage モデルのリストとして定義
    result: str
    text: str | None = None
    type: str | None = None
    chathistory: List[ChatMessage] | None = None
    trace_id: str | None = None  # Langfuse trace ID (Issue #113)
    langfuse_url: str | None = None  # Langfuse UI URL (Issue #113)


class ExpertAiAgentResponseJson(BaseModel):
    # result can be either dict (JSON object) or list (JSON array)
    result: dict | list[Any]
    type: str | None = None
    chathistory: List[ChatMessage] | None = None
    attempts: int | None = None  # Number of retry attempts (if applicable)
    is_json_guaranteed: bool = True  # JSON guarantee flag
    trace_id: str | None = None  # Langfuse trace ID (Issue #113)
    langfuse_url: str | None = None  # Langfuse UI URL (Issue #113)
