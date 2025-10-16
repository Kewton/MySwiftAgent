from fastapi import APIRouter, HTTPException

from app.schemas.utilitySchemas import (
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
@router.post("/utility/google_search", summary="", description="")
async def google_search_by_serper_api(request: SearchUtilityRequest):
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
        return SearchUtilityResponse(result=result)
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
