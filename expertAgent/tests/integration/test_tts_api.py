"""Text-to-Speech (TTS) API の統合テスト"""

import base64
import json
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestTextToSpeechAPIIntegration:
    """Text-to-Speech API（Base64返却）統合テストクラス"""

    def test_text_to_speech_endpoint_success(self):
        """IT-01: エンドポイント呼び出し成功（200 OK）"""
        # Arrange
        mock_audio_data = b"fake_mp3_audio_data"
        mock_audio_base64 = base64.b64encode(mock_audio_data).decode("utf-8")

        request_data = {
            "text": "こんにちは、これはテストです。",
            "model": "tts-1",
            "voice": "alloy",
        }

        # Act & Assert
        with patch("app.api.v1.tts_endpoints.tts"):
            with patch("pathlib.Path.mkdir"):
                with patch("pathlib.Path.exists", return_value=True):
                    with patch("pathlib.Path.stat") as mock_stat:
                        mock_stat.return_value.st_size = len(mock_audio_data)
                        with patch("builtins.open", create=True) as mock_open:
                            mock_open.return_value.__enter__.return_value.read.return_value = mock_audio_data

                            response = client.post(
                                "/v1/utility/text_to_speech", json=request_data
                            )

                            assert response.status_code == 200
                            response_json = response.json()
                            assert response_json["audio_content"] == mock_audio_base64
                            assert response_json["format"] == "mp3"
                            assert response_json["size_bytes"] == len(mock_audio_data)

    def test_text_to_speech_endpoint_validation_error(self):
        """IT-02: リクエストバリデーションエラー（422）"""
        # Arrange: textが欠けている不正なリクエスト
        request_data = {"model": "tts-1", "voice": "alloy"}

        # Act
        response = client.post(
            "/aiagent-api/v1/utility/text_to_speech", json=request_data
        )

        # Assert
        assert response.status_code == 422
        response_json = response.json()
        assert "detail" in response_json or "errors" in response_json

    def test_text_to_speech_endpoint_text_too_long(self):
        """IT-03: テキスト長超過エラー（400）"""
        # Arrange
        request_data = {
            "text": "あ" * 5000,  # 4096文字超過
            "model": "tts-1",
            "voice": "alloy",
        }

        # Act
        response = client.post(
            "/aiagent-api/v1/utility/text_to_speech", json=request_data
        )

        # Assert
        assert response.status_code == 400
        assert "4096文字以内" in response.json()["detail"]

    def test_text_to_speech_endpoint_invalid_model(self):
        """IT-04: 無効なモデル指定エラー（400）"""
        # Arrange
        request_data = {
            "text": "テスト",
            "model": "invalid-model",
            "voice": "alloy",
        }

        # Act
        response = client.post(
            "/aiagent-api/v1/utility/text_to_speech", json=request_data
        )

        # Assert
        assert response.status_code == 400
        assert "tts-1" in response.json()["detail"]

    def test_text_to_speech_endpoint_invalid_voice(self):
        """IT-05: 無効な音声タイプ指定エラー（400）"""
        # Arrange
        request_data = {
            "text": "テスト",
            "model": "tts-1",
            "voice": "invalid-voice",
        }

        # Act
        response = client.post(
            "/aiagent-api/v1/utility/text_to_speech", json=request_data
        )

        # Assert
        assert response.status_code == 400
        assert "alloy" in response.json()["detail"]

    def test_text_to_speech_endpoint_response_format(self):
        """IT-06: レスポンス形式の検証"""
        # Arrange
        mock_audio_data = b"test_audio"
        request_data = {
            "text": "テスト音声",
            "model": "tts-1",
            "voice": "alloy",
        }

        # Act & Assert
        with patch("app.api.v1.tts_endpoints.tts"):
            with patch("pathlib.Path.mkdir"):
                with patch("pathlib.Path.exists", return_value=True):
                    with patch("pathlib.Path.stat") as mock_stat:
                        mock_stat.return_value.st_size = len(mock_audio_data)
                        with patch("builtins.open", create=True) as mock_open:
                            mock_open.return_value.__enter__.return_value.read.return_value = mock_audio_data

                            response = client.post(
                                "/v1/utility/text_to_speech", json=request_data
                            )

                            # Assert
                            assert response.status_code == 200
                            response_json = response.json()

                            # 必須フィールドの存在確認
                            required_fields = ["audio_content", "format", "size_bytes"]
                            for field in required_fields:
                                assert field in response_json, (
                                    f"Required field '{field}' is missing"
                                )

                            # データ型の検証
                            assert isinstance(response_json["audio_content"], str)
                            assert isinstance(response_json["format"], str)
                            assert isinstance(response_json["size_bytes"], int)
                            assert response_json["format"] == "mp3"


class TestTextToSpeechDriveAPIIntegration:
    """Text-to-Speech + Drive Upload API 統合テストクラス"""

    def test_text_to_speech_drive_endpoint_success(self):
        """IT-07: エンドポイント呼び出し成功（200 OK）"""
        # Arrange
        mock_drive_result = {
            "status": "success",
            "file_id": "test123",
            "file_name": "greeting.mp3",
            "web_view_link": "https://drive.google.com/file/d/test123/view",
            "web_content_link": "https://drive.google.com/uc?id=test123",
            "folder_path": "podcasts/2025",
            "file_size_mb": 0.15,
        }

        request_data = {
            "text": "こんにちは、これはテストです。",
            "file_name": "greeting",
            "sub_directory": "podcasts/2025",
        }

        # Act & Assert
        with patch("app.api.v1.tts_endpoints.tts"):
            with patch("pathlib.Path.mkdir"):
                with patch("pathlib.Path.exists", return_value=True):
                    with patch("pathlib.Path.stat") as mock_stat:
                        mock_stat.return_value.st_size = 1024
                        with patch(
                            "app.api.v1.tts_endpoints.upload_file_to_drive_tool",
                            new_callable=AsyncMock,
                        ) as mock_upload:
                            mock_upload.return_value = json.dumps(mock_drive_result)

                            response = client.post(
                                "/v1/utility/text_to_speech_drive", json=request_data
                            )

                            assert response.status_code == 200
                            response_json = response.json()
                            assert response_json["file_id"] == "test123"
                            assert response_json["file_name"] == "greeting.mp3"
                            assert response_json["folder_path"] == "podcasts/2025"

    def test_text_to_speech_drive_endpoint_validation_error(self):
        """IT-08: リクエストバリデーションエラー（422）"""
        # Arrange: textが欠けている不正なリクエスト
        request_data = {"file_name": "test"}

        # Act
        response = client.post(
            "/aiagent-api/v1/utility/text_to_speech_drive", json=request_data
        )

        # Assert
        assert response.status_code == 422
        response_json = response.json()
        assert "detail" in response_json or "errors" in response_json

    def test_text_to_speech_drive_endpoint_text_too_long(self):
        """IT-09: テキスト長超過エラー（400）"""
        # Arrange
        request_data = {
            "text": "あ" * 5000,  # 4096文字超過
            "model": "tts-1",
            "voice": "alloy",
        }

        # Act
        response = client.post(
            "/aiagent-api/v1/utility/text_to_speech_drive", json=request_data
        )

        # Assert
        assert response.status_code == 400
        assert "4096文字以内" in response.json()["detail"]

    def test_text_to_speech_drive_endpoint_upload_error(self):
        """IT-10: Driveアップロードエラー（400）"""
        # Arrange
        request_data = {
            "text": "テスト",
            "drive_folder_url": "invalid_url",
        }

        mock_error_result = {
            "status": "error",
            "error_type": "ValueError",
            "message": "無効なGoogle DriveフォルダURLです",
        }

        # Act & Assert
        with patch("app.api.v1.tts_endpoints.tts"):
            with patch("pathlib.Path.mkdir"):
                with patch("pathlib.Path.exists", return_value=True):
                    with patch("pathlib.Path.stat") as mock_stat:
                        mock_stat.return_value.st_size = 1024
                        with patch(
                            "app.api.v1.tts_endpoints.upload_file_to_drive_tool",
                            new_callable=AsyncMock,
                        ) as mock_upload:
                            mock_upload.return_value = json.dumps(mock_error_result)

                            response = client.post(
                                "/v1/utility/text_to_speech_drive", json=request_data
                            )

                            assert response.status_code == 400
                            assert "無効" in response.json()["detail"]

    def test_text_to_speech_drive_endpoint_server_error(self):
        """IT-11: サーバーエラー時のHTTPステータスコード（500）"""
        # Arrange
        request_data = {
            "text": "テスト",
        }

        mock_error_result = {
            "status": "error",
            "error_type": "InternalError",
            "message": "サーバー内部エラーが発生しました",
        }

        # Act & Assert
        with patch("app.api.v1.tts_endpoints.tts"):
            with patch("pathlib.Path.mkdir"):
                with patch("pathlib.Path.exists", return_value=True):
                    with patch("pathlib.Path.stat") as mock_stat:
                        mock_stat.return_value.st_size = 1024
                        with patch(
                            "app.api.v1.tts_endpoints.upload_file_to_drive_tool",
                            new_callable=AsyncMock,
                        ) as mock_upload:
                            mock_upload.return_value = json.dumps(mock_error_result)

                            response = client.post(
                                "/v1/utility/text_to_speech_drive", json=request_data
                            )

                            assert response.status_code == 500
                            assert "エラーが発生" in response.json()["detail"]

    def test_text_to_speech_drive_endpoint_response_format(self):
        """IT-12: レスポンス形式の検証"""
        # Arrange
        mock_drive_result = {
            "status": "success",
            "file_id": "1a2b3c4d5e",
            "file_name": "test.mp3",
            "web_view_link": "https://drive.google.com/file/d/1a2b3c4d5e/view",
            "web_content_link": "https://drive.google.com/uc?id=1a2b3c4d5e",
            "folder_path": "ルート",
            "file_size_mb": 0.1,
        }

        request_data = {
            "text": "テスト音声",
        }

        # Act & Assert
        with patch("app.api.v1.tts_endpoints.tts"):
            with patch("pathlib.Path.mkdir"):
                with patch("pathlib.Path.exists", return_value=True):
                    with patch("pathlib.Path.stat") as mock_stat:
                        mock_stat.return_value.st_size = 1024
                        with patch(
                            "app.api.v1.tts_endpoints.upload_file_to_drive_tool",
                            new_callable=AsyncMock,
                        ) as mock_upload:
                            mock_upload.return_value = json.dumps(mock_drive_result)

                            response = client.post(
                                "/v1/utility/text_to_speech_drive", json=request_data
                            )

                            # Assert
                            assert response.status_code == 200
                            response_json = response.json()

                            # 必須フィールドの存在確認
                            required_fields = [
                                "file_id",
                                "file_name",
                                "web_view_link",
                                "folder_path",
                                "file_size_mb",
                            ]
                            for field in required_fields:
                                assert field in response_json, (
                                    f"Required field '{field}' is missing"
                                )

                            # データ型の検証
                            assert isinstance(response_json["file_id"], str)
                            assert isinstance(response_json["file_name"], str)
                            assert isinstance(response_json["web_view_link"], str)
                            assert isinstance(response_json["folder_path"], str)
                            assert isinstance(
                                response_json["file_size_mb"], (int, float)
                            )
