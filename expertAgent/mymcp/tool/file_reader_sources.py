"""File Reader ソースハンドラモジュール

このモジュールは、さまざまなソースからファイルをダウンロード/読み込む機能を提供します。

サポートするソース:
- インターネットURL (HTTP/HTTPS)
- Google Drive (OAuth2認証)
- ローカルファイルシステム
"""

import io
import logging
import tempfile
from pathlib import Path
from typing import Tuple

import httpx
from googleapiclient.http import MediaIoBaseDownload

from mymcp.googleapis.googleapi_services import get_googleapis_service
from mymcp.tool.file_reader_utils import (
    detect_mime_type,
    extract_google_drive_file_id,
    validate_file_size,
    validate_local_path,
)

logger = logging.getLogger(__name__)

# HTTPクライアントのタイムアウト設定（秒）
HTTP_TIMEOUT = 30


async def download_from_url(url: str) -> Tuple[Path, str]:
    """インターネットURLからファイルをダウンロードします。

    Args:
        url: ダウンロード元のHTTP/HTTPS URL

    Returns:
        Tuple[Path, str]: (一時ファイルパス, MIME type)

    Raises:
        ValueError: URLが無効、またはダウンロード失敗
        httpx.HTTPError: ネットワークエラー

    Examples:
        >>> path, mime = await download_from_url("https://example.com/doc.pdf")
        >>> print(f"Downloaded to {path}, MIME: {mime}")
        Downloaded to /tmp/tmp12345.pdf, MIME: application/pdf
    """
    logger.info(f"Downloading from URL: {url}")

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            # HEADリクエストでContent-Typeを事前取得
            try:
                head_response = await client.head(url, follow_redirects=True)
                content_type = head_response.headers.get("content-type", "").split(";")[
                    0
                ]
                logger.debug(f"Content-Type from HEAD: {content_type}")
            except Exception as e:
                logger.warning(f"HEAD request failed: {e}, proceeding with GET")
                content_type = None

            # GETリクエストでファイルをダウンロード
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

            # Content-Typeが取得できていない場合はGETレスポンスから取得
            if not content_type:
                content_type = response.headers.get("content-type", "").split(";")[0]

            # 一時ファイルに保存
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".tmp")
            temp_path = Path(temp_file.name)

            with open(temp_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Downloaded {len(response.content)} bytes to {temp_path}")

            # ファイルサイズ検証
            validate_file_size(temp_path)

            # MIME type検出（Content-Typeが不明な場合はファイルから検出）
            if content_type and content_type != "application/octet-stream":
                mime_type = content_type
            else:
                mime_type = detect_mime_type(temp_path)

            logger.info(f"Successfully downloaded from URL. MIME type: {mime_type}")
            return temp_path, mime_type

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error {e.response.status_code}: {e}")
        raise ValueError(
            f"Failed to download from URL (HTTP {e.response.status_code}): {url}"
        ) from e
    except httpx.TimeoutException as e:
        logger.error(f"Timeout while downloading from URL: {e}")
        raise ValueError(f"Download timeout ({HTTP_TIMEOUT}s): {url}") from e
    except Exception as e:
        logger.error(f"Unexpected error while downloading from URL: {e}")
        raise ValueError(f"Download failed: {url}") from e


def download_from_google_drive(url: str) -> Tuple[Path, str]:
    """Google Driveからファイルをダウンロードします。

    OAuth2認証を使用してGoogle Drive API v3経由でダウンロードします。
    認証情報はMyVaultから取得されます。

    Args:
        url: Google DriveのファイルURL

    Returns:
        Tuple[Path, str]: (一時ファイルパス, MIME type)

    Raises:
        ValueError: URLからファイルIDが抽出できない、またはダウンロード失敗
        FileNotFoundError: ファイルがDrive上に存在しない
        ConnectionError: Drive APIサービスの取得に失敗

    Examples:
        >>> url = "https://drive.google.com/file/d/1ABC123XYZ/view"
        >>> path, mime = download_from_google_drive(url)
        >>> print(f"Downloaded {path.name}, MIME: {mime}")
        Downloaded tmpXYZ.pdf, MIME: application/pdf
    """
    logger.info(f"Downloading from Google Drive: {url}")

    # ファイルID抽出
    file_id = extract_google_drive_file_id(url)
    if not file_id:
        raise ValueError(f"Could not extract file ID from Google Drive URL: {url}")

    logger.debug(f"Extracted file ID: {file_id}")

    # Google Drive APIサービス取得
    service = get_googleapis_service("drive")
    if not service:
        raise ConnectionError(
            "Failed to get Google Drive service. "
            "Please check MyVault configuration for Google credentials."
        )

    try:
        # ファイルメタデータ取得
        file_metadata = (
            service.files().get(fileId=file_id, fields="name,mimeType").execute()
        )
        file_name = file_metadata.get("name", "unknown")
        mime_type = file_metadata.get("mimeType", "application/octet-stream")

        logger.info(f"File metadata: name='{file_name}', mimeType='{mime_type}'")

        # ファイルダウンロード
        request = service.files().get_media(fileId=file_id)

        # 一時ファイルに保存
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".tmp")
        temp_path = Path(temp_file.name)

        with io.FileIO(temp_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            downloaded_bytes = 0

            while not done:
                status, done = downloader.next_chunk()
                if status:
                    downloaded_bytes = int(status.resumable_progress)
                    progress_pct = int(status.progress() * 100)
                    logger.debug(f"Download progress: {progress_pct}%")

        logger.info(f"Downloaded {downloaded_bytes} bytes to {temp_path}")

        # ファイルサイズ検証
        validate_file_size(temp_path)

        logger.info(
            f"Successfully downloaded from Google Drive. MIME type: {mime_type}"
        )
        return temp_path, mime_type

    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "File not found" in error_msg:
            raise FileNotFoundError(
                f"File not found on Google Drive (ID: {file_id})"
            ) from e
        elif "403" in error_msg or "Forbidden" in error_msg:
            raise ValueError(
                f"Permission denied for Google Drive file (ID: {file_id}). "
                "File may be private or sharing is disabled."
            ) from e
        else:
            logger.error(f"Unexpected error while downloading from Google Drive: {e}")
            raise ValueError(
                f"Failed to download from Google Drive (ID: {file_id}): {error_msg}"
            ) from e


def read_from_local(file_path: str) -> Tuple[Path, str]:
    """ローカルファイルシステムからファイルを読み込みます。

    セキュリティ検証を行い、許可されたディレクトリ内のファイルのみアクセスを許可します。

    Args:
        file_path: ローカルファイルの絶対パスまたは相対パス

    Returns:
        Tuple[Path, str]: (検証済みファイルパス, MIME type)

    Raises:
        FileNotFoundError: ファイルが存在しない
        ValueError: パスが許可ディレクトリ外

    Examples:
        >>> path, mime = read_from_local("/tmp/sample.txt")
        >>> print(f"File: {path}, MIME: {mime}")
        File: /tmp/sample.txt, MIME: text/plain
    """
    logger.info(f"Reading from local file: {file_path}")

    # パスセキュリティ検証（Path traversal攻撃防止）
    validated_path = validate_local_path(file_path)

    # ファイルサイズ検証
    validate_file_size(validated_path)

    # MIME type検出
    mime_type = detect_mime_type(validated_path)

    logger.info(f"Successfully validated local file. MIME type: {mime_type}")
    return validated_path, mime_type
