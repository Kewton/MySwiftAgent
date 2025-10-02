from typing import List

from pydantic import BaseModel


class UtilityRequest(BaseModel):
    user_input: str


class UtilityResponse(BaseModel):
    # result フィールドを ChatMessage モデルのリストとして定義
    result: str


class SearchUtilityRequest(BaseModel):
    queries: List[str]
    num: int | None = None


class SearchUtilityResponse(BaseModel):
    result: str
