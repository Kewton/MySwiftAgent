from typing import Any, List

from pydantic import BaseModel, Field


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
    num: int | None = Field(
        default=None,
        le=3,
        description="Number of results per query (max=3 to prevent timeout)",
    )
    project: str | None = None  # MyVault project name for secrets
    test_mode: bool = False  # Test mode flag for development/debugging
    test_response: dict | None = None  # Mock response for test mode


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


class FetchWebContentRequest(BaseModel):
    """Request schema for web content fetch API.

    Used in GraphAI workflows to fetch actual article content from URLs.
    """

    url: str = Field(..., description="The URL to fetch content from")
    upload_to_drive: bool = Field(
        default=False,
        description="Whether to upload the markdown to Google Drive",
    )


class FetchWebContentResponse(BaseModel):
    """Response schema for web content fetch API.

    Returns the web page content converted to Markdown format.
    Workflows can reference:
    - :fetch_content.markdown_content
    - :fetch_content.status
    """

    markdown_content: str = Field(
        ..., description="The web page content in Markdown format"
    )
    status: str = Field(default="success", description="Status indicator")
    error: str | None = Field(
        default=None, description="Error message if status is 'failed'"
    )


class ExtractArticleUrlsRequest(BaseModel):
    """Request schema for extracting article URLs from search results.

    Used in GraphAI workflows to extract top N article URLs from
    nested search results structure.
    """

    search_results: List[dict] = Field(
        ..., description="Search results from Google search API"
    )
    max_urls: int = Field(
        default=2, description="Maximum number of URLs to extract", le=5
    )


class ExtractArticleUrlsResponse(BaseModel):
    """Response schema for extract article URLs API.

    Returns flattened list of article URLs.
    Workflows can reference:
    - :extract_urls.article_url_1
    - :extract_urls.article_url_2
    """

    article_url_1: str | None = Field(default=None, description="First article URL")
    article_url_2: str | None = Field(default=None, description="Second article URL")
    article_url_3: str | None = Field(default=None, description="Third article URL")
    urls: List[str] = Field(
        default_factory=list, description="List of all extracted URLs"
    )
    count: int = Field(default=0, description="Number of URLs extracted")
