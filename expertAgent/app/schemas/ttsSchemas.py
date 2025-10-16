"""Text-to-Speech (TTS) API スキーマ定義

このモジュールは、TTS APIのリクエスト/レスポンススキーマを定義します。
"""

from typing import Optional

from pydantic import BaseModel, Field


class TTSRequest(BaseModel):
    """TTS API リクエスト (Base64音声データ返却)

    OpenAI TTS APIを使用してテキストを音声化し、Base64エンコードされた
    音声データを返却します。
    """

    text: str = Field(
        ...,
        description="音声合成するテキスト（最大4096文字）",
        min_length=1,
    )
    model: str = Field(
        "tts-1",
        description="TTSモデル (tts-1: 標準品質, tts-1-hd: 高品質)",
    )
    voice: str = Field(
        "alloy",
        description="音声タイプ (alloy, echo, fable, onyx, nova, shimmer)",
    )
    test_mode: bool = Field(
        False,
        description="テストモード（CI/CD環境での自動テスト用）",
    )
    test_response: str = Field(
        "",
        description="テストモード時に返却するレスポンス",
    )


class TTSResponse(BaseModel):
    """TTS API レスポンス (Base64音声データ)

    Base64エンコードされた音声データと関連情報
    """

    audio_content: str = Field(
        ...,
        description="Base64エンコードされた音声データ（MP3形式）",
    )
    format: str = Field(
        ...,
        description="音声フォーマット（常に 'mp3'）",
    )
    size_bytes: int = Field(
        ...,
        description="元のファイルサイズ（バイト単位）",
    )


class TTSDriveRequest(BaseModel):
    """TTS + Drive Upload API リクエスト

    OpenAI TTS APIを使用してテキストを音声化し、
    Google Driveに直接アップロードします。
    """

    text: str = Field(
        ...,
        description="音声合成するテキスト（最大4096文字）",
        min_length=1,
    )
    drive_folder_url: Optional[str] = Field(
        None,
        description="GoogleDriveフォルダのURL（任意、未指定時はルート）",
    )
    file_name: Optional[str] = Field(
        None,
        description="保存時のファイル名（任意、未指定時は自動生成）",
    )
    sub_directory: Optional[str] = Field(
        None,
        description="サブディレクトリパス（任意）",
    )
    model: str = Field(
        "tts-1",
        description="TTSモデル (tts-1: 標準品質, tts-1-hd: 高品質)",
    )
    voice: str = Field(
        "alloy",
        description="音声タイプ (alloy, echo, fable, onyx, nova, shimmer)",
    )
    test_mode: bool = Field(
        False,
        description="テストモード（CI/CD環境での自動テスト用）",
    )
    test_response: str = Field(
        "",
        description="テストモード時に返却するレスポンス",
    )


class TTSDriveResponse(BaseModel):
    """TTS + Drive Upload API レスポンス

    Google Driveにアップロードされた音声ファイル情報
    """

    file_id: str = Field(
        ...,
        description="Google Drive ファイルID",
    )
    file_name: str = Field(
        ...,
        description="アップロードされたファイル名",
    )
    web_view_link: str = Field(
        ...,
        description="ファイル閲覧用URL",
    )
    web_content_link: Optional[str] = Field(
        None,
        description="ファイルダウンロード用URL",
    )
    folder_path: str = Field(
        ...,
        description="アップロード先フォルダパス",
    )
    file_size_mb: float = Field(
        ...,
        description="ファイルサイズ（MB）",
    )
