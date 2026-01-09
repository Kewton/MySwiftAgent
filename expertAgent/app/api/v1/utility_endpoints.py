import json
from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas.utilitySchemas import (
    ExtractArticleUrlsRequest,
    ExtractArticleUrlsResponse,
    FetchWebContentRequest,
    FetchWebContentResponse,
    GoogleSearchResponse,
    JsonStringifyRequest,
    JsonStringifyResponse,
    SearchUtilityRequest,
    SearchUtilityResponse,
    UtilityRequest,
    UtilityResponse,
)
from core.config import settings
from core.test_mode_handler import handle_test_mode
from mymcp.googleapis.gmail.send import send_email
from mymcp.tool.google_search_by_serper import (
    get_overview_by_google_serper,
    google_search_by_serper_list,
)
from mymcp.tool.tts_and_upload_drive import tts_and_upload_drive
from mymcp.utils.generate_subject_from_text import generate_subject_from_text
from mymcp.utils.html2markdown import getMarkdown

router = APIRouter()


@router.post("/utility/tts_and_upload_drive", summary="", description="")
async def tts_and_upload_drive_api(request: UtilityRequest):
    """
    テキストの台本をインプットに音声合成を行い音声ファイル(.mp3)を生成しGoogle Driveにアップロードします。
    アップロードしたファイルへのURLリンクを返却します。

    Args:
        user_input (str): 音声合成するテキストメッセージ。

    Returns:
        str: アップロード結果を示すメッセージまたはファイルURリンク
    """
    try:
        # Test mode check using common handler
        test_result = handle_test_mode(
            request.test_mode, request.test_response, "tts_and_upload_drive"
        )
        if test_result is not None:
            return test_result

        # タイトル生成
        title = generate_subject_from_text(request.user_input, max_length=40)

        print(f"Generated title: {title}")

        # 音声合成とGoogle Driveへのアップロード
        result = tts_and_upload_drive(request.user_input, title)

        body = f"""

        音声合成とGoogle Driveへのアップロードが完了しました。

        # アップロード結果:
        {result}
        ---

        # 台本:
        {request.user_input}
        """

        # メール送信
        send_email(settings.MAIL_TO, title, body)

        return UtilityResponse(result=result)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(
            status_code=500, detail="An internal server error occurred in the utility."
        ) from e


# search_tool
@router.post(
    "/utility/google_search",
    response_model=GoogleSearchResponse,
    summary="Google Search via Serper API",
    description="Performs Google search and returns results with predictable field names for workflow generation.",
)
async def google_search_by_serper_api(
    request: SearchUtilityRequest,
) -> GoogleSearchResponse | Any:
    """
    Google検索を実行し、ワークフロー生成で予測しやすい形式で結果を返す。

    レスポンス形式:
    - search_results: 検索結果の配列
    - search_results_count: 結果件数
    - status: ステータス

    ワークフローでの参照例:
    - :fetch_search_results.search_results
    - :fetch_search_results.search_results_count
    """
    print(f"request: {request}")
    try:
        # Test mode check using common handler
        test_result = handle_test_mode(
            request.test_mode, request.test_response, "google_search"
        )
        if test_result is not None:
            return test_result

        if request.num is None:
            result = await google_search_by_serper_list(request.queries)
        else:
            result = await google_search_by_serper_list(request.queries, request.num)

        # Extract search results from the nested structure
        # Original format: {"text": "ok", "result": [...]}
        search_results = result.get("result", [])

        return GoogleSearchResponse(
            search_results=search_results,
            search_results_count=len(search_results),
            status=result.get("text", "ok"),
        )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(
            status_code=500, detail="An internal server error occurred in the utility."
        ) from e


# search_tool
@router.post("/utility/google_search_overview", summary="", description="")
async def get_overview_by_google_serper_api(request: SearchUtilityRequest):
    print(f"request: {request}")
    try:
        # Test mode check using common handler
        test_result = handle_test_mode(
            request.test_mode, request.test_response, "google_search_overview"
        )
        if test_result is not None:
            return test_result

        if request.num is None:
            result = await get_overview_by_google_serper(request.queries)
        else:
            result = await get_overview_by_google_serper(request.queries, request.num)
        return SearchUtilityResponse(result=result)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(
            status_code=500, detail="An internal server error occurred in the utility."
        ) from e


@router.post(
    "/utility/json_stringify",
    response_model=JsonStringifyResponse,
    summary="Convert data to JSON string",
    description="Converts any JSON-serializable data to a JSON string. "
    "Useful for GraphAI workflows that need to embed objects in string templates.",
)
async def json_stringify_api(request: JsonStringifyRequest) -> JsonStringifyResponse:
    """
    Convert any JSON-serializable data to a JSON string.

    This utility is designed for GraphAI workflows where stringTemplateAgent
    needs to embed complex objects (arrays, nested objects) in string templates.
    Without JSON serialization, objects become "[object Object]" in templates.

    Args:
        request: Contains the data to be JSON-stringified

    Returns:
        JsonStringifyResponse with the JSON string representation
    """
    try:
        json_string = json.dumps(request.data, ensure_ascii=False, indent=2)
        return JsonStringifyResponse(json_string=json_string)
    except (TypeError, ValueError) as e:
        raise HTTPException(
            status_code=400, detail=f"Data is not JSON-serializable: {e}"
        ) from e


@router.post(
    "/utility/fetch_web_content",
    response_model=FetchWebContentResponse,
    summary="Fetch web page content as Markdown",
    description="Fetches a web page and converts its HTML content to Markdown format. "
    "Useful for GraphAI workflows that need to analyze or summarize web article content.",
)
async def fetch_web_content_api(
    request: FetchWebContentRequest,
) -> FetchWebContentResponse:
    """
    Fetch web page content and convert it to Markdown.

    This utility is designed for GraphAI workflows that need to:
    1. Fetch actual article content from URLs (not just search snippets)
    2. Summarize or analyze the full content of web pages
    3. Process web content in subsequent LLM calls

    Args:
        request: Contains the URL to fetch and options

    Returns:
        FetchWebContentResponse with the Markdown content

    Example workflow usage:
        - :fetch_content.markdown_content - The article content in Markdown
        - :fetch_content.status - "success" or "failed"
    """
    try:
        result = getMarkdown(request.url, isUpload=request.upload_to_drive)

        if isinstance(result, dict):
            if result.get("state") == "success":
                return FetchWebContentResponse(
                    markdown_content=result.get("result", ""),
                    status="success",
                )
            else:
                return FetchWebContentResponse(
                    markdown_content="",
                    status="failed",
                    error=result.get("result", "Unknown error"),
                )
        else:
            # If result is a string, it's likely an error message
            return FetchWebContentResponse(
                markdown_content="",
                status="failed",
                error=str(result),
            )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch web content: {e}"
        ) from e


@router.post(
    "/utility/extract_article_urls",
    response_model=ExtractArticleUrlsResponse,
    summary="Extract article URLs from search results",
    description="Extracts article URLs from nested Google search results structure. "
    "Useful for GraphAI workflows that need to access individual article URLs.",
)
async def extract_article_urls_api(
    request: ExtractArticleUrlsRequest,
) -> ExtractArticleUrlsResponse:
    """
    Extract article URLs from nested search results.

    This utility handles the nested structure of Google search results:
    search_results[0].organic[n].link

    It flattens this structure and returns individual URL fields that can
    be easily accessed in GraphAI workflows.

    Args:
        request: Contains search results and max URLs to extract

    Returns:
        ExtractArticleUrlsResponse with individual URL fields
    """
    try:
        urls: list[str] = []

        # Extract URLs from nested structure
        for result in request.search_results:
            organic = result.get("organic", [])
            for item in organic:
                link = item.get("link")
                if link and len(urls) < request.max_urls:
                    urls.append(link)

        # Build response with individual URL fields
        response = ExtractArticleUrlsResponse(
            urls=urls,
            count=len(urls),
            article_url_1=urls[0] if len(urls) > 0 else None,
            article_url_2=urls[1] if len(urls) > 1 else None,
            article_url_3=urls[2] if len(urls) > 2 else None,
        )

        return response
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to extract article URLs: {e}"
        ) from e
