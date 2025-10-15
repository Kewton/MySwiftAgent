"""Text-to-Speech (TTS) API エンドポイント

このモジュールは、OpenAI TTS APIを使用したテキスト音声変換機能を提供します。
2つのパターンをサポート:
1. Base64エンコードされた音声データを返却
2. Google Driveにアップロードしてリンクを返却
"""

import base64
import json
import logging
import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas.ttsSchemas import (
    TTSDriveRequest,
    TTSDriveResponse,
    TTSRequest,
    TTSResponse,
)
from core.test_mode_handler import handle_test_mode
from mymcp.stdio_action import upload_file_to_drive_tool
from mymcp.tts.tts import tts

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/utility/text_to_speech",
    response_model=TTSResponse,
    summary="Convert text to speech (Base64)",
    description="""
    テキストを音声に変換し、Base64エンコードされた音声データを返却します。

    **主要機能**:
    - OpenAI TTS APIによる高品質音声合成
    - 複数の音声タイプ選択可能（alloy, echo, fable, onyx, nova, shimmer）
    - 2つのモデル選択（tts-1: 標準品質、tts-1-hd: 高品質）
    - Base64エンコードでJSON形式で返却

    **使用例**:
    ```json
    {
      "text": "こんにちは、これはテスト音声です。",
      "model": "tts-1",
      "voice": "alloy"
    }
    ```

    **レスポンス例**:
    ```json
    {
      "audio_content": "SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4Ljc2LjEwMAAAAAAAAAAAAAAA...",
      "format": "mp3",
      "size_bytes": 15360
    }
    ```
    """,
)
async def text_to_speech_api(
    request: TTSRequest,
) -> TTSResponse | Any:
    """
    テキストを音声に変換（Base64返却）

    Args:
        request: TTS変換リクエスト

    Returns:
        TTSResponse | Any: Base64エンコードされた音声データ（テストモード時はAny）

    Raises:
        HTTPException: TTS変換失敗時
            - 400: テキスト長超過、無効なパラメータ
            - 500: OpenAI API エラー、予期しないエラー
    """
    try:
        # Test mode check
        test_result = handle_test_mode(
            request.test_mode, request.test_response, "text_to_speech"
        )
        if test_result is not None:
            return test_result  # type: ignore[return-value]

        # 入力検証
        if len(request.text) > 4096:
            raise HTTPException(
                status_code=400, detail="テキストは4096文字以内にしてください"
            )

        if request.model not in ["tts-1", "tts-1-hd"]:
            raise HTTPException(
                status_code=400,
                detail="モデルは 'tts-1' または 'tts-1-hd' を指定してください",
            )

        if request.voice not in [
            "alloy",
            "echo",
            "fable",
            "onyx",
            "nova",
            "shimmer",
        ]:
            raise HTTPException(
                status_code=400,
                detail="音声タイプは alloy, echo, fable, onyx, nova, shimmer のいずれかを指定してください",
            )

        # 一時ファイル作成
        temp_dir = Path(tempfile.gettempdir()) / "tts_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        unique_filename = f"{uuid.uuid4()}.mp3"
        speech_file_path = temp_dir / unique_filename

        try:
            # OpenAI TTS API 呼び出し
            logger.info(
                f"Generating speech for text (length: {len(request.text)})",
                extra={
                    "model": request.model,
                    "voice": request.voice,
                },
            )

            # 既存のtts関数を使用（内部でOpenAI API呼び出し）
            tts(str(speech_file_path), request.text)

            # ファイル存在確認
            if not speech_file_path.exists() or speech_file_path.stat().st_size == 0:
                logger.error("TTS failed: No audio file generated")
                raise HTTPException(
                    status_code=500, detail="音声ファイルの生成に失敗しました"
                )

            # ファイルをBase64エンコード
            with open(speech_file_path, "rb") as f:
                audio_bytes = f.read()
                audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

            file_size = speech_file_path.stat().st_size

            logger.info(
                f"TTS successful: Generated {file_size} bytes",
                extra={
                    "text_length": len(request.text),
                    "file_size": file_size,
                },
            )

            return TTSResponse(
                audio_content=audio_base64, format="mp3", size_bytes=file_size
            )

        finally:
            # 一時ファイル削除
            if speech_file_path.exists():
                try:
                    speech_file_path.unlink()
                    logger.debug(f"Deleted temporary file: {speech_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file: {e}")

    except HTTPException:
        # HTTPExceptionはそのまま再raise
        raise

    except Exception as e:
        # 予期しないエラー
        logger.exception(
            "Unexpected error in text_to_speech API",
            extra={
                "text_length": len(request.text),
            },
        )
        raise HTTPException(
            status_code=500,
            detail="音声変換中に予期しないエラーが発生しました",
        ) from e


@router.post(
    "/utility/text_to_speech_drive",
    response_model=TTSDriveResponse,
    summary="Convert text to speech and upload to Google Drive",
    description="""
    テキストを音声に変換し、Google Driveにアップロードしてリンクを返却します。

    **主要機能**:
    - OpenAI TTS APIによる高品質音声合成
    - Google Driveへの直接アップロード
    - サブディレクトリ自動作成
    - 重複ファイル名自動回避
    - ファイルリンク返却

    **使用例**:
    ```json
    {
      "text": "こんにちは、これはテスト音声です。",
      "drive_folder_url": "https://drive.google.com/drive/folders/xxx",
      "sub_directory": "podcasts/2025",
      "file_name": "greeting",
      "model": "tts-1",
      "voice": "alloy"
    }
    ```

    **レスポンス例**:
    ```json
    {
      "file_id": "1a2b3c4d5e",
      "file_name": "greeting.mp3",
      "web_view_link": "https://drive.google.com/file/d/1a2b3c4d5e/view",
      "web_content_link": "https://drive.google.com/uc?id=1a2b3c4d5e",
      "folder_path": "podcasts/2025",
      "file_size_mb": 0.15
    }
    ```
    """,
)
async def text_to_speech_drive_api(
    request: TTSDriveRequest,
) -> TTSDriveResponse | Any:
    """
    テキストを音声に変換してGoogle Driveにアップロード

    Args:
        request: TTS変換＋Driveアップロードリクエスト

    Returns:
        TTSDriveResponse | Any: アップロードされたファイル情報（テストモード時はAny）

    Raises:
        HTTPException: TTS変換またはアップロード失敗時
            - 400: テキスト長超過、無効なパラメータ
            - 500: OpenAI API エラー、Drive API エラー、予期しないエラー
    """
    try:
        # Test mode check
        test_result = handle_test_mode(
            request.test_mode, request.test_response, "text_to_speech_drive"
        )
        if test_result is not None:
            return test_result  # type: ignore[return-value]

        # 入力検証
        if len(request.text) > 4096:
            raise HTTPException(
                status_code=400, detail="テキストは4096文字以内にしてください"
            )

        if request.model not in ["tts-1", "tts-1-hd"]:
            raise HTTPException(
                status_code=400,
                detail="モデルは 'tts-1' または 'tts-1-hd' を指定してください",
            )

        if request.voice not in [
            "alloy",
            "echo",
            "fable",
            "onyx",
            "nova",
            "shimmer",
        ]:
            raise HTTPException(
                status_code=400,
                detail="音声タイプは alloy, echo, fable, onyx, nova, shimmer のいずれかを指定してください",
            )

        # 一時ファイル作成
        temp_dir = Path(tempfile.gettempdir()) / "tts_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        unique_filename = f"{uuid.uuid4()}.mp3"
        speech_file_path = temp_dir / unique_filename

        try:
            # OpenAI TTS API 呼び出し
            logger.info(
                f"Generating speech for Drive upload (text length: {len(request.text)})",
                extra={
                    "model": request.model,
                    "voice": request.voice,
                    "sub_directory": request.sub_directory,
                },
            )

            # 既存のtts関数を使用
            tts(str(speech_file_path), request.text)

            # ファイル存在確認
            if not speech_file_path.exists() or speech_file_path.stat().st_size == 0:
                logger.error("TTS failed: No audio file generated")
                raise HTTPException(
                    status_code=500, detail="音声ファイルの生成に失敗しました"
                )

            logger.info("TTS successful, uploading to Google Drive")

            # Google Driveにアップロード
            # ファイル名が指定されていない場合は自動生成
            drive_file_name = f"{request.file_name}.mp3" if request.file_name else None

            result_json = await upload_file_to_drive_tool(
                file_path=str(speech_file_path),
                drive_folder_url=request.drive_folder_url,
                file_name=drive_file_name,
                sub_directory=request.sub_directory,
                size_threshold_mb=100,  # MP3は通常小さいので通常アップロード
                content=None,
                file_format=None,
                create_file=False,
            )

            # JSONレスポンスをパース
            result = json.loads(result_json)

            # エラーレスポンスの場合
            if result["status"] == "error":
                error_type = result.get("error_type", "UnknownError")
                error_message = result.get("message", "An unknown error occurred")

                # エラータイプに応じてHTTPステータスコードを決定
                if error_type in ["FileNotFoundError", "ValueError"]:
                    status_code = 400
                else:
                    status_code = 500

                logger.error(
                    f"Drive upload failed: {error_type} - {error_message}",
                    extra={
                        "error_type": error_type,
                        "file_path": str(speech_file_path),
                    },
                )

                raise HTTPException(status_code=status_code, detail=error_message)

            # 成功レスポンスを返却
            logger.info(
                f"TTS and Drive upload successful: {result['file_id']}",
                extra={
                    "file_id": result["file_id"],
                    "file_name": result["file_name"],
                    "folder_path": result["folder_path"],
                },
            )

            return TTSDriveResponse(**result)

        finally:
            # 一時ファイル削除
            if speech_file_path.exists():
                try:
                    speech_file_path.unlink()
                    logger.debug(f"Deleted temporary file: {speech_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file: {e}")

    except HTTPException:
        # HTTPExceptionはそのまま再raise
        raise

    except Exception as e:
        # 予期しないエラー
        logger.exception(
            "Unexpected error in text_to_speech_drive API",
            extra={
                "text_length": len(request.text),
                "sub_directory": request.sub_directory,
            },
        )
        raise HTTPException(
            status_code=500,
            detail="音声変換またはアップロード中に予期しないエラーが発生しました",
        ) from e
