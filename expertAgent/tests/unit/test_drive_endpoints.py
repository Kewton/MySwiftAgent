"""Google Drive Upload API エンドポイントの単体テスト"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.drive_endpoints import upload_file_to_drive_api
from app.schemas.driveSchemas import DriveUploadRequest


@pytest.mark.asyncio
class TestDriveUploadAPI:
    """Google Drive Upload API のテストクラス"""

    async def test_upload_local_file_success(self):
        """UT-01: ローカルファイルアップロード成功"""
        # Arrange
        request = DriveUploadRequest(
            file_path="/tmp/test.txt",
            file_name="uploaded_test.txt",
        )

        mock_result = {
            "status": "success",
            "file_id": "1a2b3c4d5e",
            "file_name": "uploaded_test.txt",
            "web_view_link": "https://drive.google.com/file/d/1a2b3c4d5e/view",
            "web_content_link": "https://drive.google.com/uc?id=1a2b3c4d5e",
            "folder_path": "ルート",
            "file_size_mb": 0.01,
            "upload_method": "normal",
        }

        # Act & Assert
        with patch(
            "app.api.v1.drive_endpoints.upload_file_to_drive_tool",
            new_callable=AsyncMock,
        ) as mock_tool:
            mock_tool.return_value = json.dumps(mock_result)

            response = await upload_file_to_drive_api(request)

            assert response.status == "success"
            assert response.file_id == "1a2b3c4d5e"
            assert response.file_name == "uploaded_test.txt"
            assert response.upload_method == "normal"
            mock_tool.assert_called_once()

    async def test_upload_with_content_creation_success(self):
        """UT-02: コンテンツからファイル作成＆アップロード成功"""
        # Arrange
        request = DriveUploadRequest(
            file_path="/tmp/generated.txt",
            content="Hello, World!",
            file_format="txt",
            create_file=True,
        )

        mock_result = {
            "status": "success",
            "file_id": "2b3c4d5e6f",
            "file_name": "generated.txt",
            "web_view_link": "https://drive.google.com/file/d/2b3c4d5e6f/view",
            "web_content_link": None,
            "folder_path": "ルート",
            "file_size_mb": 0.001,
            "upload_method": "normal",
        }

        # Act & Assert
        with patch(
            "app.api.v1.drive_endpoints.upload_file_to_drive_tool",
            new_callable=AsyncMock,
        ) as mock_tool:
            mock_tool.return_value = json.dumps(mock_result)

            response = await upload_file_to_drive_api(request)

            assert response.status == "success"
            assert response.file_id == "2b3c4d5e6f"
            assert response.file_name == "generated.txt"
            mock_tool.assert_called_once_with(
                file_path="/tmp/generated.txt",
                drive_folder_url=None,
                file_name=None,
                sub_directory=None,
                size_threshold_mb=100,
                content="Hello, World!",
                file_format="txt",
                create_file=True,
            )

    async def test_upload_with_subdirectory_success(self):
        """UT-03: サブディレクトリ指定アップロード成功"""
        # Arrange
        request = DriveUploadRequest(
            file_path="/tmp/report.pdf",
            sub_directory="reports/2025",
        )

        mock_result = {
            "status": "success",
            "file_id": "3c4d5e6f7g",
            "file_name": "report.pdf",
            "web_view_link": "https://drive.google.com/file/d/3c4d5e6f7g/view",
            "web_content_link": None,
            "folder_path": "reports/2025",
            "file_size_mb": 1.5,
            "upload_method": "normal",
        }

        # Act & Assert
        with patch(
            "app.api.v1.drive_endpoints.upload_file_to_drive_tool",
            new_callable=AsyncMock,
        ) as mock_tool:
            mock_tool.return_value = json.dumps(mock_result)

            response = await upload_file_to_drive_api(request)

            assert response.status == "success"
            assert response.folder_path == "reports/2025"

    async def test_upload_with_resumable_upload(self):
        """UT-04: Resumable Upload（大ファイル）成功"""
        # Arrange
        request = DriveUploadRequest(
            file_path="/tmp/large_file.zip",
            size_threshold_mb=50,  # 閾値を低く設定
        )

        mock_result = {
            "status": "success",
            "file_id": "4d5e6f7g8h",
            "file_name": "large_file.zip",
            "web_view_link": "https://drive.google.com/file/d/4d5e6f7g8h/view",
            "web_content_link": None,
            "folder_path": "ルート",
            "file_size_mb": 150.5,
            "upload_method": "resumable",
        }

        # Act & Assert
        with patch(
            "app.api.v1.drive_endpoints.upload_file_to_drive_tool",
            new_callable=AsyncMock,
        ) as mock_tool:
            mock_tool.return_value = json.dumps(mock_result)

            response = await upload_file_to_drive_api(request)

            assert response.status == "success"
            assert response.upload_method == "resumable"
            assert response.file_size_mb == 150.5

    async def test_upload_file_not_found_error(self):
        """UT-05: ファイル不存在エラー（400）"""
        # Arrange
        request = DriveUploadRequest(file_path="/nonexistent/file.txt")

        mock_error_result = {
            "status": "error",
            "error_type": "FileNotFoundError",
            "message": "指定されたファイルが存在しません: /nonexistent/file.txt",
        }

        # Act & Assert
        with patch(
            "app.api.v1.drive_endpoints.upload_file_to_drive_tool",
            new_callable=AsyncMock,
        ) as mock_tool:
            mock_tool.return_value = json.dumps(mock_error_result)

            with pytest.raises(HTTPException) as exc_info:
                await upload_file_to_drive_api(request)

            assert exc_info.value.status_code == 400
            assert "存在しません" in exc_info.value.detail

    async def test_upload_invalid_folder_url_error(self):
        """UT-06: 無効なフォルダURL（400）"""
        # Arrange
        request = DriveUploadRequest(
            file_path="/tmp/test.txt", drive_folder_url="invalid_url"
        )

        mock_error_result = {
            "status": "error",
            "error_type": "ValueError",
            "message": "無効なGoogle DriveフォルダURLです",
        }

        # Act & Assert
        with patch(
            "app.api.v1.drive_endpoints.upload_file_to_drive_tool",
            new_callable=AsyncMock,
        ) as mock_tool:
            mock_tool.return_value = json.dumps(mock_error_result)

            with pytest.raises(HTTPException) as exc_info:
                await upload_file_to_drive_api(request)

            assert exc_info.value.status_code == 400
            assert "無効" in exc_info.value.detail

    async def test_upload_create_file_without_content_error(self):
        """UT-07: create_file=True でcontent未指定（400）"""
        # Arrange
        request = DriveUploadRequest(
            file_path="/tmp/test.txt", create_file=True, file_format="txt"
        )

        mock_error_result = {
            "status": "error",
            "error_type": "ValueError",
            "message": "create_file=True の場合、content パラメータが必須です",
        }

        # Act & Assert
        with patch(
            "app.api.v1.drive_endpoints.upload_file_to_drive_tool",
            new_callable=AsyncMock,
        ) as mock_tool:
            mock_tool.return_value = json.dumps(mock_error_result)

            with pytest.raises(HTTPException) as exc_info:
                await upload_file_to_drive_api(request)

            assert exc_info.value.status_code == 400
            assert "content" in exc_info.value.detail

    async def test_upload_test_mode(self):
        """UT-08: テストモード動作確認"""
        # Arrange
        request = DriveUploadRequest(
            file_path="/tmp/test.txt",
            test_mode=True,
            test_response="Test response from drive upload",
        )

        # Act & Assert
        with patch("app.api.v1.drive_endpoints.handle_test_mode") as mock_test_handler:
            mock_test_handler.return_value = "Test response from drive upload"

            response = await upload_file_to_drive_api(request)

            assert response == "Test response from drive upload"
            mock_test_handler.assert_called_once_with(
                True, "Test response from drive upload", "drive_upload"
            )

    async def test_upload_google_api_error(self):
        """UT-09: Google Drive API エラー（500）"""
        # Arrange
        request = DriveUploadRequest(file_path="/tmp/test.txt")

        mock_error_result = {
            "status": "error",
            "error_type": "GoogleAPIError",
            "message": "Google Drive API でエラーが発生しました",
        }

        # Act & Assert
        with patch(
            "app.api.v1.drive_endpoints.upload_file_to_drive_tool",
            new_callable=AsyncMock,
        ) as mock_tool:
            mock_tool.return_value = json.dumps(mock_error_result)

            with pytest.raises(HTTPException) as exc_info:
                await upload_file_to_drive_api(request)

            assert exc_info.value.status_code == 500
            assert "エラーが発生" in exc_info.value.detail

    async def test_upload_unexpected_exception(self):
        """UT-10: 予期しない例外（500）"""
        # Arrange
        request = DriveUploadRequest(file_path="/tmp/test.txt")

        # Act & Assert
        with patch(
            "app.api.v1.drive_endpoints.upload_file_to_drive_tool",
            new_callable=AsyncMock,
        ) as mock_tool:
            mock_tool.side_effect = RuntimeError("Unexpected error")

            with pytest.raises(HTTPException) as exc_info:
                await upload_file_to_drive_api(request)

            assert exc_info.value.status_code == 500
            assert "internal server error" in exc_info.value.detail.lower()
