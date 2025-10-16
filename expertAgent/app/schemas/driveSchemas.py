"""Google Drive Upload API スキーマ定義

このモジュールは、Google Drive Upload APIのリクエスト/レスポンススキーマを定義します。
"""

from typing import List, Optional, Union

from pydantic import BaseModel, Field


class DriveUploadRequest(BaseModel):
    """Google Drive アップロードリクエスト

    ローカルファイルのアップロードまたはコンテンツからファイルを生成してアップロードします。
    """

    file_path: str = Field(
        ...,
        description="アップロード対象のローカルファイルパス（必須）。"
        "create_file=True の場合、作成先パスとして使用",
    )
    drive_folder_url: Optional[str] = Field(
        None,
        description="GoogleDriveフォルダのURL（任意、未指定時はルート）",
    )
    file_name: Optional[str] = Field(
        None,
        description="保存時のファイル名（任意、未指定時は元のファイル名）",
    )
    sub_directory: Optional[str] = Field(
        None,
        description="サブディレクトリパス（任意）",
    )
    size_threshold_mb: int = Field(
        100,
        description="Resumable Upload閾値（MB、デフォルト100MB）",
        ge=1,
        le=1000,
    )

    # コンテンツからファイル作成モード
    content: Optional[Union[str, bytes]] = Field(
        None,
        description="ファイル内容（create_file=True時のみ使用）。"
        "テキスト、バイナリ、Base64エンコード文字列に対応",
    )
    file_format: Optional[str] = Field(
        None,
        description="ファイル形式の拡張子（create_file=True時のみ使用）",
    )
    create_file: bool = Field(
        False,
        description="ファイル作成モードを有効化（デフォルト: False）",
    )

    # テストモード
    test_mode: bool = Field(
        False,
        description="テストモード（CI/CD環境での自動テスト用）",
    )
    test_response: str = Field(
        "",
        description="テストモード時に返却するレスポンス",
    )


class DriveUploadResponse(BaseModel):
    """Google Drive アップロードレスポンス

    アップロード成功時のレスポンス情報
    """

    status: str = Field(
        ...,
        description="処理ステータス（success/error）",
    )
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
    upload_method: str = Field(
        ...,
        description="アップロードメソッド（normal/resumable）",
    )


class DriveUploadFromUrlRequest(BaseModel):
    """URL配列からGoogle Driveへの一括アップロードリクエスト"""

    urls: List[str] = Field(
        ...,
        description="アップロード対象のURL配列",
        min_length=1,
    )
    folder_id: str = Field(
        ...,
        description="アップロード先のGoogle DriveフォルダID",
    )
    user_agent: Optional[str] = Field(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        description="HTTPリクエスト時のUser-Agent（デフォルト: Chrome）",
    )
    referer: Optional[str] = Field(
        None,
        description="HTTPリクエスト時のRefererヘッダー（必要な場合のみ）",
    )
    timeout: int = Field(
        30,
        description="ダウンロードタイムアウト（秒）",
        ge=5,
        le=300,
    )
    test_mode: bool = Field(
        False,
        description="テストモード（CI/CD環境での自動テスト用）",
    )


class DriveFileUploadResult(BaseModel):
    """個別ファイルのアップロード結果"""

    source_url: str = Field(..., description="元のURL")
    status: str = Field(..., description="success / failed")
    drive_url: Optional[str] = Field(None, description="Google DriveファイルURL")
    file_id: Optional[str] = Field(None, description="Google Drive ファイルID")
    file_name: Optional[str] = Field(None, description="ファイル名")
    file_size: Optional[int] = Field(None, description="ファイルサイズ（bytes）")
    mime_type: Optional[str] = Field(None, description="MIMEタイプ")
    error: Optional[str] = Field(None, description="エラーメッセージ（失敗時）")


class DriveUploadFromUrlResponse(BaseModel):
    """URL配列からのGoogle Driveアップロードレスポンス"""

    folder_url: str = Field(..., description="アップロード先フォルダのURL")
    folder_id: str = Field(..., description="アップロード先フォルダのID")
    files: List[DriveFileUploadResult] = Field(..., description="各ファイルの結果")
