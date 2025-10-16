"""Text-to-Speech (TTS) API エンドポイントの単体テスト"""

import base64
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.tts_endpoints import text_to_speech_api, text_to_speech_drive_api
from app.schemas.ttsSchemas import TTSDriveRequest, TTSRequest


@pytest.mark.asyncio
class TestTextToSpeechAPI:
    """Text-to-Speech API（Base64返却）のテストクラス"""

    async def test_text_to_speech_success(self):
        """UT-01: TTS変換成功（Base64返却）"""
        # Arrange
        request = TTSRequest(
            text="こんにちは、これはテストです。",
            model="tts-1",
            voice="alloy",
        )

        mock_audio_data = b"fake_audio_data"
        mock_audio_base64 = base64.b64encode(mock_audio_data).decode("utf-8")

        # Act & Assert
        with patch("app.api.v1.tts_endpoints.tts") as mock_tts:
            with patch("pathlib.Path.mkdir"):
                with patch("pathlib.Path.exists", return_value=True):
                    with patch("pathlib.Path.stat") as mock_stat:
                        mock_stat.return_value.st_size = len(mock_audio_data)
                        with patch("builtins.open", create=True) as mock_open:
                            mock_open.return_value.__enter__.return_value.read.return_value = mock_audio_data

                            response = await text_to_speech_api(request)

                            assert response.audio_content == mock_audio_base64
                            assert response.format == "mp3"
                            assert response.size_bytes == len(mock_audio_data)
                            mock_tts.assert_called_once()

    async def test_text_to_speech_test_mode(self):
        """UT-02: テストモード動作確認"""
        # Arrange
        request = TTSRequest(
            text="テスト",
            test_mode=True,
            test_response="Test response from TTS",
        )

        # Act & Assert
        with patch("app.api.v1.tts_endpoints.handle_test_mode") as mock_test_handler:
            mock_test_handler.return_value = "Test response from TTS"

            response = await text_to_speech_api(request)

            assert response == "Test response from TTS"
            mock_test_handler.assert_called_once_with(
                True, "Test response from TTS", "text_to_speech"
            )

    async def test_text_to_speech_text_too_long(self):
        """UT-03: テキスト長超過エラー（400）"""
        # Arrange
        request = TTSRequest(
            text="あ" * 5000,  # 4096文字超過
            model="tts-1",
            voice="alloy",
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await text_to_speech_api(request)

        assert exc_info.value.status_code == 400
        assert "4096文字以内" in exc_info.value.detail

    async def test_text_to_speech_invalid_model(self):
        """UT-04: 無効なモデル指定（400）"""
        # Arrange
        request = TTSRequest(
            text="テスト",
            model="invalid-model",
            voice="alloy",
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await text_to_speech_api(request)

        assert exc_info.value.status_code == 400
        assert "tts-1" in exc_info.value.detail

    async def test_text_to_speech_invalid_voice(self):
        """UT-05: 無効な音声タイプ指定（400）"""
        # Arrange
        request = TTSRequest(
            text="テスト",
            model="tts-1",
            voice="invalid-voice",
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await text_to_speech_api(request)

        assert exc_info.value.status_code == 400
        assert "alloy" in exc_info.value.detail

    async def test_text_to_speech_tts_failure(self):
        """UT-06: TTS処理失敗（500）"""
        # Arrange
        request = TTSRequest(
            text="テスト",
            model="tts-1",
            voice="alloy",
        )

        # Act & Assert
        with patch("app.api.v1.tts_endpoints.tts"):
            with patch("pathlib.Path.exists", return_value=False):
                with pytest.raises(HTTPException) as exc_info:
                    await text_to_speech_api(request)

                assert exc_info.value.status_code == 500
                assert "生成に失敗" in exc_info.value.detail

    async def test_text_to_speech_empty_file(self):
        """UT-07: 空ファイル生成エラー（500）"""
        # Arrange
        request = TTSRequest(
            text="テスト",
            model="tts-1",
            voice="alloy",
        )

        # Act & Assert
        with patch("app.api.v1.tts_endpoints.tts"):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_size = 0  # Empty file

                    with pytest.raises(HTTPException) as exc_info:
                        await text_to_speech_api(request)

                    assert exc_info.value.status_code == 500
                    assert (
                        "予期しない" in exc_info.value.detail
                        or "生成に失敗" in exc_info.value.detail
                    )

    async def test_text_to_speech_unexpected_exception(self):
        """UT-08: 予期しない例外（500）"""
        # Arrange
        request = TTSRequest(
            text="テスト",
            model="tts-1",
            voice="alloy",
        )

        # Act & Assert
        with patch(
            "app.api.v1.tts_endpoints.tts", side_effect=RuntimeError("Unexpected")
        ):
            with pytest.raises(HTTPException) as exc_info:
                await text_to_speech_api(request)

            assert exc_info.value.status_code == 500
            assert "予期しない" in exc_info.value.detail


@pytest.mark.asyncio
class TestTextToSpeechDriveAPI:
    """Text-to-Speech + Drive Upload API のテストクラス"""

    async def test_text_to_speech_drive_success(self):
        """UT-09: TTS変換＋Driveアップロード成功"""
        # Arrange
        request = TTSDriveRequest(
            text="こんにちは、これはテストです。",
            drive_folder_url="https://drive.google.com/drive/folders/test123",
            file_name="greeting",
            sub_directory="podcasts/2025",
            model="tts-1",
            voice="alloy",
        )

        mock_drive_result = {
            "status": "success",
            "file_id": "1a2b3c4d5e",
            "file_name": "greeting.mp3",
            "web_view_link": "https://drive.google.com/file/d/1a2b3c4d5e/view",
            "web_content_link": "https://drive.google.com/uc?id=1a2b3c4d5e",
            "folder_path": "podcasts/2025",
            "file_size_mb": 0.15,
        }

        # Act & Assert
        with patch("app.api.v1.tts_endpoints.tts") as mock_tts:
            with patch("pathlib.Path.mkdir"):
                with patch("pathlib.Path.exists", return_value=True):
                    with patch("pathlib.Path.stat") as mock_stat:
                        mock_stat.return_value.st_size = 1024
                        with patch(
                            "app.api.v1.tts_endpoints.upload_file_to_drive_tool",
                            new_callable=AsyncMock,
                        ) as mock_upload:
                            mock_upload.return_value = json.dumps(mock_drive_result)

                            response = await text_to_speech_drive_api(request)

                            assert response.file_id == "1a2b3c4d5e"
                            assert response.file_name == "greeting.mp3"
                            assert response.folder_path == "podcasts/2025"
                            assert response.file_size_mb == 0.15
                            mock_tts.assert_called_once()
                            mock_upload.assert_called_once()

    async def test_text_to_speech_drive_auto_filename(self):
        """UT-10: ファイル名自動生成"""
        # Arrange
        request = TTSDriveRequest(
            text="テスト",
            model="tts-1",
            voice="alloy",
            # file_name未指定
        )

        mock_drive_result = {
            "status": "success",
            "file_id": "auto123",
            "file_name": "audio_001_20250101_120000.mp3",
            "web_view_link": "https://drive.google.com/file/d/auto123/view",
            "web_content_link": None,
            "folder_path": "ルート",
            "file_size_mb": 0.05,
        }

        # Act & Assert
        with patch("app.api.v1.tts_endpoints.tts"):
            with patch("pathlib.Path.mkdir"):
                with patch("pathlib.Path.exists", return_value=True):
                    with patch("pathlib.Path.stat") as mock_stat:
                        mock_stat.return_value.st_size = 512
                        with patch(
                            "app.api.v1.tts_endpoints.upload_file_to_drive_tool",
                            new_callable=AsyncMock,
                        ) as mock_upload:
                            mock_upload.return_value = json.dumps(mock_drive_result)

                            await text_to_speech_drive_api(request)

                            # file_nameが指定されていないので、upload_file_to_drive_toolに
                            # Noneが渡されることを確認
                            call_args = mock_upload.call_args[1]
                            assert call_args["file_name"] is None

    async def test_text_to_speech_drive_test_mode(self):
        """UT-11: テストモード動作確認"""
        # Arrange
        request = TTSDriveRequest(
            text="テスト",
            test_mode=True,
            test_response="Test response from TTS Drive",
        )

        # Act & Assert
        with patch("app.api.v1.tts_endpoints.handle_test_mode") as mock_test_handler:
            mock_test_handler.return_value = "Test response from TTS Drive"

            response = await text_to_speech_drive_api(request)

            assert response == "Test response from TTS Drive"
            mock_test_handler.assert_called_once_with(
                True, "Test response from TTS Drive", "text_to_speech_drive"
            )

    async def test_text_to_speech_drive_text_too_long(self):
        """UT-12: テキスト長超過エラー（400）"""
        # Arrange
        request = TTSDriveRequest(
            text="あ" * 5000,  # 4096文字超過
            model="tts-1",
            voice="alloy",
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await text_to_speech_drive_api(request)

        assert exc_info.value.status_code == 400
        assert "4096文字以内" in exc_info.value.detail

    async def test_text_to_speech_drive_upload_error(self):
        """UT-13: Driveアップロードエラー（400）"""
        # Arrange
        request = TTSDriveRequest(
            text="テスト",
            model="tts-1",
            voice="alloy",
        )

        mock_error_result = {
            "status": "error",
            "error_type": "ValueError",
            "message": "無効なフォルダURLです",
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

                            with pytest.raises(HTTPException) as exc_info:
                                await text_to_speech_drive_api(request)

                            assert exc_info.value.status_code == 400
                            assert "無効" in exc_info.value.detail

    async def test_text_to_speech_drive_google_api_error(self):
        """UT-14: Google Drive API エラー（500）"""
        # Arrange
        request = TTSDriveRequest(
            text="テスト",
            model="tts-1",
            voice="alloy",
        )

        mock_error_result = {
            "status": "error",
            "error_type": "GoogleAPIError",
            "message": "Google Drive API でエラーが発生しました",
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

                            with pytest.raises(HTTPException) as exc_info:
                                await text_to_speech_drive_api(request)

                            assert exc_info.value.status_code == 500
                            assert "エラーが発生" in exc_info.value.detail

    async def test_text_to_speech_drive_unexpected_exception(self):
        """UT-15: 予期しない例外（500）"""
        # Arrange
        request = TTSDriveRequest(
            text="テスト",
            model="tts-1",
            voice="alloy",
        )

        # Act & Assert
        with patch(
            "app.api.v1.tts_endpoints.tts", side_effect=RuntimeError("Unexpected")
        ):
            with pytest.raises(HTTPException) as exc_info:
                await text_to_speech_drive_api(request)

            assert exc_info.value.status_code == 500
            assert "予期しない" in exc_info.value.detail
