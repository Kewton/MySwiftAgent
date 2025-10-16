"""Google Drive Upload API エンドポイント

このモジュールは、Google Drive へのファイルアップロード機能を提供するAPIエンドポイントを実装します。
既存のMCPツール（upload_file_to_drive_tool）をラッパーとして活用します。
"""

import asyncio
import json
import logging
import os
import tempfile
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException

from app.schemas.driveSchemas import (
    DriveFileUploadResult,
    DriveUploadFromUrlRequest,
    DriveUploadFromUrlResponse,
    DriveUploadRequest,
    DriveUploadResponse,
)
from core.test_mode_handler import handle_test_mode
from mymcp.stdio_action import upload_file_to_drive_tool

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/utility/drive/upload",
    response_model=DriveUploadResponse,
    summary="Upload file to Google Drive",
    description="""
    ローカルファイルまたはコンテンツから生成したファイルをGoogle Driveにアップロードします。

    **主要機能**:
    - ローカルファイルのアップロード
    - コンテンツからファイル生成＆アップロード
    - サブディレクトリ自動作成
    - 重複ファイル名自動回避
    - 大ファイル対応（Resumable Upload自動切替）

    **使用例**:
    1. ローカルファイルアップロード:
       ```json
       {
         "file_path": "/tmp/report.pdf",
         "drive_folder_url": "https://drive.google.com/drive/folders/xxx",
         "sub_directory": "reports/2025"
       }
       ```

    2. コンテンツからファイル作成:
       ```json
       {
         "file_path": "/tmp/generated.txt",
         "content": "Hello, World!",
         "file_format": "txt",
         "create_file": true
       }
       ```
    """,
)
async def upload_file_to_drive_api(
    request: DriveUploadRequest,
) -> DriveUploadResponse | Any:
    """
    Google Driveにファイルをアップロード

    Args:
        request: アップロードリクエスト

    Returns:
        DriveUploadResponse | Any: アップロード結果（テストモード時はAny）

    Raises:
        HTTPException: アップロード失敗時
            - 400: パラメータ不正、ファイル不存在
            - 500: Google Drive API エラー、予期しないエラー
    """
    try:
        # Test mode check using common handler
        test_result = handle_test_mode(
            request.test_mode, request.test_response, "drive_upload"
        )
        if test_result is not None:
            return test_result  # type: ignore[return-value]

        # MCPツールを呼び出し（asyncラッパー）
        result_json = await upload_file_to_drive_tool(
            file_path=request.file_path,
            drive_folder_url=request.drive_folder_url,
            file_name=request.file_name,
            sub_directory=request.sub_directory,
            size_threshold_mb=request.size_threshold_mb,
            content=request.content,
            file_format=request.file_format,
            create_file=request.create_file,
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
                    "file_path": request.file_path,
                    "create_file": request.create_file,
                },
            )

            raise HTTPException(status_code=status_code, detail=error_message)

        # 成功レスポンスを返却
        return DriveUploadResponse(**result)

    except HTTPException:
        # HTTPExceptionはそのまま再raiseして上位でハンドリング
        raise

    except Exception as e:
        # 予期しないエラー
        logger.exception(
            "Unexpected error in drive upload API",
            extra={
                "file_path": request.file_path,
                "create_file": request.create_file,
            },
        )
        raise HTTPException(
            status_code=500,
            detail="An internal server error occurred during file upload",
        ) from e


async def download_file_from_url(
    url: str,
    user_agent: str,
    referer: str | None,
    timeout: int,
) -> tuple[str, bytes, str | None]:
    """
    URLからファイルをダウンロードする

    Args:
        url: ダウンロード対象URL
        user_agent: User-Agentヘッダー
        referer: Refererヘッダー（Noneの場合は設定しない）
        timeout: タイムアウト（秒）

    Returns:
        tuple[str, bytes, str | None]: (ファイル名, ファイル内容, Content-Type)

    Raises:
        HTTPException: ダウンロード失敗時
    """
    headers = {"User-Agent": user_agent}
    if referer:
        headers["Referer"] = referer

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            # ファイル名を取得（URLの最後のセグメント）
            file_name = url.split("/")[-1].split("?")[0]
            if not file_name or "." not in file_name:
                file_name = "downloaded_file"

            content_type = response.headers.get("Content-Type")

            # Content-Typeが text/html の場合は403エラーとみなす
            if content_type and "text/html" in content_type.lower():
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file: received HTML page (likely 403 Forbidden). URL: {url}",
                )

            # 小さすぎるファイル（< 1KB）はエラーページの可能性
            if len(response.content) < 1024:
                logger.warning(
                    f"Downloaded file is very small ({len(response.content)} bytes), may be an error page"
                )

            return file_name, response.content, content_type

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error downloading {url}: {e.response.status_code}")
            raise HTTPException(
                status_code=400,
                detail=f"HTTP {e.response.status_code} error downloading file from {url}",
            ) from e
        except httpx.TimeoutException as e:
            logger.error(f"Timeout downloading {url}")
            raise HTTPException(
                status_code=408, detail=f"Timeout downloading file from {url}"
            ) from e
        except Exception as e:
            logger.exception(f"Error downloading {url}")
            raise HTTPException(
                status_code=500, detail=f"Failed to download file from {url}: {str(e)}"
            ) from e


async def upload_single_file(
    url: str,
    folder_id: str,
    user_agent: str,
    referer: str | None,
    timeout: int,
) -> DriveFileUploadResult:
    """
    単一ファイルをダウンロード→Google Driveにアップロード

    Args:
        url: ダウンロード対象URL
        folder_id: Google DriveフォルダID
        user_agent: User-Agentヘッダー
        referer: Refererヘッダー
        timeout: タイムアウト（秒）

    Returns:
        DriveFileUploadResult: アップロード結果
    """
    temp_file_path = None
    try:
        # URLからダウンロード
        file_name, content, content_type = await download_file_from_url(
            url, user_agent, referer, timeout
        )

        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(
            mode="wb", delete=False, suffix=f"_{file_name}"
        ) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Google Driveにアップロード
        folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
        result_json = await upload_file_to_drive_tool(
            file_path=temp_file_path,
            drive_folder_url=folder_url,
            file_name=file_name,
        )

        result = json.loads(result_json)

        if result["status"] == "error":
            error_msg = result.get("message", "Unknown upload error")
            return DriveFileUploadResult(
                source_url=url,
                status="failed",
                error=f"Upload failed: {error_msg}",
            )

        # 成功レスポンス
        return DriveFileUploadResult(
            source_url=url,
            status="success",
            drive_url=result["web_view_link"],
            file_id=result["file_id"],
            file_name=result["file_name"],
            file_size=len(content),
            mime_type=content_type,
        )

    except HTTPException as e:
        # ダウンロード失敗
        return DriveFileUploadResult(
            source_url=url,
            status="failed",
            error=e.detail,
        )
    except Exception as e:
        logger.exception(f"Unexpected error uploading {url}")
        return DriveFileUploadResult(
            source_url=url,
            status="failed",
            error=f"Unexpected error: {str(e)}",
        )
    finally:
        # 一時ファイルを削除
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_file_path}: {e}")


@router.post(
    "/utility/drive/upload_from_url",
    response_model=DriveUploadFromUrlResponse,
    summary="Upload files from URLs to Google Drive",
    description="""
    URL配列から複数ファイルをダウンロードし、Google Driveに一括アップロードします。

    **主要機能**:
    - URL配列からの並列ダウンロード
    - User-Agent/Refererヘッダー指定（403エラー回避）
    - ファイル検証（HTMLエラーページ検出）
    - 一括アップロード結果の返却

    **使用例**:
    ```json
    {
      "urls": [
        "https://example.com/file1.pdf",
        "https://example.com/file2.pdf"
      ],
      "folder_id": "1Xrv6nJPuMB92s2DGcvZo_lH2H4cd_OsQ",
      "user_agent": "Mozilla/5.0...",
      "referer": "https://example.com/"
    }
    ```

    **レスポンス**:
    - folder_url: アップロード先フォルダURL
    - files: 各ファイルの結果（drive_url, file_id, status等）
    """,
)
async def upload_files_from_urls(
    request: DriveUploadFromUrlRequest,
) -> DriveUploadFromUrlResponse:
    """
    URL配列からGoogle Driveに一括アップロード

    Args:
        request: アップロードリクエスト

    Returns:
        DriveUploadFromUrlResponse: アップロード結果

    Raises:
        HTTPException: リクエスト不正時
    """
    try:
        # Test mode check
        if request.test_mode:
            # テストモード用のダミーレスポンス
            test_files = [
                DriveFileUploadResult(
                    source_url=url,
                    status="success",
                    drive_url=f"https://drive.google.com/file/d/TEST_ID_{i}/view",
                    file_id=f"TEST_ID_{i}",
                    file_name=url.split("/")[-1],
                    file_size=1000,
                    mime_type="application/pdf",
                )
                for i, url in enumerate(request.urls)
            ]
            return DriveUploadFromUrlResponse(
                folder_url=f"https://drive.google.com/drive/folders/{request.folder_id}",
                folder_id=request.folder_id,
                files=test_files,
            )

        # 並列アップロード
        tasks = [
            upload_single_file(
                url=url,
                folder_id=request.folder_id,
                user_agent=request.user_agent or "",
                referer=request.referer,
                timeout=request.timeout,
            )
            for url in request.urls
        ]

        results = await asyncio.gather(*tasks)

        # レスポンス構築
        return DriveUploadFromUrlResponse(
            folder_url=f"https://drive.google.com/drive/folders/{request.folder_id}",
            folder_id=request.folder_id,
            files=list(results),
        )

    except Exception as e:
        logger.exception("Unexpected error in upload_files_from_urls")
        raise HTTPException(
            status_code=500,
            detail=f"An internal server error occurred: {str(e)}",
        ) from e
