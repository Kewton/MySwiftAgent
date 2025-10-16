from typing import List

from pydantic import BaseModel


class UtilityRequest(BaseModel):
    user_input: str
    project: str | None = None  # MyVault project name for secrets
    test_mode: bool = False  # Test mode flag for development/debugging
    test_response: dict | str | None = None  # Mock response for test mode


class UtilityResponse(BaseModel):
    # result フィールドを ChatMessage モデルのリストとして定義
    result: str


class SearchUtilityRequest(BaseModel):
    queries: List[str]
    num: int | None = None
    project: str | None = None  # MyVault project name for secrets
    test_mode: bool = False  # Test mode flag for development/debugging
    test_response: dict | str | None = None  # Mock response for test mode


class SearchUtilityResponse(BaseModel):
    result: str
