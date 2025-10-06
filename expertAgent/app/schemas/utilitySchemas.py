from typing import List

from pydantic import BaseModel


class UtilityRequest(BaseModel):
    user_input: str
    project: str | None = None  # MyVault project name for secrets


class UtilityResponse(BaseModel):
    # result フィールドを ChatMessage モデルのリストとして定義
    result: str


class SearchUtilityRequest(BaseModel):
    queries: List[str]
    num: int | None = None
    project: str | None = None  # MyVault project name for secrets


class SearchUtilityResponse(BaseModel):
    result: str
