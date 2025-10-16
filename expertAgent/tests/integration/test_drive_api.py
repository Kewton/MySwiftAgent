"""Google Drive Upload API の統合テスト"""

import json
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestDriveUploadAPIIntegration:
    """Google Drive Upload API 統合テストクラス"""

    def test_upload_endpoint_success(self):
        """IT-01: エンドポイント呼び出し成功（200 OK）"""
        # Arrange
        mock_result = {
            "status": "success",
            "file_id": "test123",
            "file_name": "uploaded_test.txt",
            "web_view_link": "https://drive.google.com/file/d/test123/view",
            "web_content_link": None,
            "folder_path": "ルート",
            "file_size_mb": 0.01,
            "upload_method": "normal",
        }

        request_data = {
            "file_path": "/tmp/test.txt",
            "file_name": "uploaded_test.txt",
        }

        # Act & Assert
        with patch(
            "app.api.v1.drive_endpoints.upload_file_to_drive_tool",
            new_callable=AsyncMock,
        ) as mock_tool:
            mock_tool.return_value = json.dumps(mock_result)

            response = client.post("/v1/utility/drive/upload", json=request_data)

            assert response.status_code == 200
            response_json = response.json()
            assert response_json["status"] == "success"
            assert response_json["file_id"] == "test123"
            assert response_json["file_name"] == "uploaded_test.txt"

    def test_upload_endpoint_file_not_found_error(self):
        """IT-02: エラー時のHTTPステータスコード（400）"""
        # Arrange
        request_data = {"file_path": "/nonexistent/file.txt"}

        mock_error_result = {
            "status": "error",
            "error_type": "FileNotFoundError",
            "message": "指定されたファイルが存在しません",
        }

        # Act & Assert
        with patch(
            "app.api.v1.drive_endpoints.upload_file_to_drive_tool",
            new_callable=AsyncMock,
        ) as mock_tool:
            mock_tool.return_value = json.dumps(mock_error_result)

            response = client.post("/v1/utility/drive/upload", json=request_data)

            assert response.status_code == 400
            assert "存在しません" in response.json()["detail"]

    def test_upload_endpoint_server_error(self):
        """IT-03: サーバーエラー時のHTTPステータスコード（500）"""
        # Arrange
        request_data = {"file_path": "/tmp/test.txt"}

        mock_error_result = {
            "status": "error",
            "error_type": "InternalError",
            "message": "サーバー内部エラーが発生しました",
        }

        # Act & Assert
        with patch(
            "app.api.v1.drive_endpoints.upload_file_to_drive_tool",
            new_callable=AsyncMock,
        ) as mock_tool:
            mock_tool.return_value = json.dumps(mock_error_result)

            response = client.post("/v1/utility/drive/upload", json=request_data)

            assert response.status_code == 500
            assert "エラーが発生" in response.json()["detail"]

    def test_upload_endpoint_response_format(self):
        """IT-04: レスポンス形式の検証"""
        # Arrange
        mock_result = {
            "status": "success",
            "file_id": "1a2b3c4d5e",
            "file_name": "test.txt",
            "web_view_link": "https://drive.google.com/file/d/1a2b3c4d5e/view",
            "web_content_link": "https://drive.google.com/uc?id=1a2b3c4d5e",
            "folder_path": "reports/2025",
            "file_size_mb": 1.5,
            "upload_method": "normal",
        }

        request_data = {
            "file_path": "/tmp/test.txt",
        }

        # Act & Assert
        with patch(
            "app.api.v1.drive_endpoints.upload_file_to_drive_tool",
            new_callable=AsyncMock,
        ) as mock_tool:
            mock_tool.return_value = json.dumps(mock_result)

            response = client.post("/v1/utility/drive/upload", json=request_data)

        # Assert
        assert response.status_code == 200
        response_json = response.json()

        # 必須フィールドの存在確認
        required_fields = [
            "status",
            "file_id",
            "file_name",
            "web_view_link",
            "folder_path",
            "file_size_mb",
            "upload_method",
        ]
        for field in required_fields:
            assert field in response_json, f"Required field '{field}' is missing"

        # データ型の検証
        assert isinstance(response_json["status"], str)
        assert isinstance(response_json["file_id"], str)
        assert isinstance(response_json["file_name"], str)
        assert isinstance(response_json["web_view_link"], str)
        assert isinstance(response_json["folder_path"], str)
        assert isinstance(response_json["file_size_mb"], (int, float))
        assert isinstance(response_json["upload_method"], str)

    def test_upload_endpoint_validation_error(self):
        """IT-05: リクエストバリデーションエラー（422）"""
        # Arrange: file_pathが欠けている不正なリクエスト
        request_data = {"file_name": "test.txt"}

        # Act
        response = client.post("/v1/utility/drive/upload", json=request_data)

        # Assert
        assert response.status_code == 422
        response_json = response.json()
        assert "detail" in response_json or "errors" in response_json

    def test_upload_endpoint_with_subdirectory(self):
        """IT-06: サブディレクトリ指定のレスポンス検証"""
        # Arrange
        mock_result = {
            "status": "success",
            "file_id": "abc123",
            "file_name": "report.pdf",
            "web_view_link": "https://drive.google.com/file/d/abc123/view",
            "web_content_link": None,
            "folder_path": "reports/2025",
            "file_size_mb": 2.5,
            "upload_method": "normal",
        }

        request_data = {
            "file_path": "/tmp/report.pdf",
            "sub_directory": "reports/2025",
        }

        # Act & Assert
        with patch(
            "app.api.v1.drive_endpoints.upload_file_to_drive_tool",
            new_callable=AsyncMock,
        ) as mock_tool:
            mock_tool.return_value = json.dumps(mock_result)

            response = client.post("/v1/utility/drive/upload", json=request_data)

            assert response.status_code == 200
            response_json = response.json()
            assert response_json["folder_path"] == "reports/2025"

    def test_upload_endpoint_resumable_upload(self):
        """IT-07: Resumable Upload のレスポンス検証"""
        # Arrange
        mock_result = {
            "status": "success",
            "file_id": "large123",
            "file_name": "large_file.zip",
            "web_view_link": "https://drive.google.com/file/d/large123/view",
            "web_content_link": None,
            "folder_path": "ルート",
            "file_size_mb": 150.5,
            "upload_method": "resumable",
        }

        request_data = {
            "file_path": "/tmp/large_file.zip",
            "size_threshold_mb": 50,
        }

        # Act & Assert
        with patch(
            "app.api.v1.drive_endpoints.upload_file_to_drive_tool",
            new_callable=AsyncMock,
        ) as mock_tool:
            mock_tool.return_value = json.dumps(mock_result)

            response = client.post("/v1/utility/drive/upload", json=request_data)

            assert response.status_code == 200
            response_json = response.json()
            assert response_json["upload_method"] == "resumable"
            assert response_json["file_size_mb"] > 100
