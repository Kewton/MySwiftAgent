from typing import Any, List

from pydantic import BaseModel


class UtilityRequest(BaseModel):
    user_input: str
    project: str | None = None  # MyVault project name for secrets
    test_mode: bool = False  # Test mode flag for development/debugging
    test_response: dict | str | None = None  # Mock response for test mode


class JsonStringifyRequest(BaseModel):
    """Request schema for JSON stringify utility."""

    data: Any  # Any JSON-serializable data


class JsonStringifyResponse(BaseModel):
    """Response schema for JSON stringify utility."""

    json_string: str  # JSON-stringified result


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
    result: dict


class GoogleSearchResponse(BaseModel):
    """Response schema for Google Search API.

    Designed for predictable field names in workflow generation.
    Workflows can reference fields directly:
    - :fetch_search_results.search_results
    - :fetch_search_results.search_results_count
    """

    search_results: List[dict]  # List of search result items
    search_results_count: int  # Number of results
    status: str = "ok"  # Status indicator
