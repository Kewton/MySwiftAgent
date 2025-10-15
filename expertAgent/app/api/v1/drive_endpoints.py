"""Google Drive Upload API エンドポイント

このモジュールは、Google Drive へのファイルアップロード機能を提供するAPIエンドポイントを実装します。
既存のMCPツール（upload_file_to_drive_tool）をラッパーとして活用します。
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas.driveSchemas import DriveUploadRequest, DriveUploadResponse
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
