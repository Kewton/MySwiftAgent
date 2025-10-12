"""File Reader ユーティリティモジュール

このモジュールは、File Readerエージェントで使用される共通ユーティリティ関数を提供します。

主な機能:
- MIME type検出
- ファイルサイズバリデーション
- ローカルパスセキュリティ検証
- Google Drive URLからのファイルID抽出
"""

import logging
import mimetypes
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ファイルサイズ制限（バイト）
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# 許可するローカルファイルディレクトリ（ホワイトリスト）
ALLOWED_DIRECTORIES = [
    "/tmp",  # noqa: S108  # Intentional for temporary file processing
    "/var/tmp",  # noqa: S108  # Intentional for temporary file processing
    "/private/tmp",  # macOS: /tmp symlink target  # noqa: S108
    "/private/var",  # macOS: tempfile.gettempdir() location  # noqa: S108
    str(Path.home() / "Downloads"),
    str(Path.home() / "Documents"),
]


def detect_mime_type(file_path: Path) -> str:
    """ファイルのMIME typeを検出します。

    python-magicが利用可能な場合はそれを使用し、
    利用不可の場合はmimetypesモジュールでフォールバック。

    Args:
        file_path: 検出対象のファイルパス

    Returns:
        str: MIME type (例: 'image/jpeg', 'application/pdf')
             検出できない場合は 'application/octet-stream'

    Examples:
        >>> detect_mime_type(Path("/tmp/sample.jpg"))
        'image/jpeg'
        >>> detect_mime_type(Path("/tmp/document.pdf"))
        'application/pdf'
    """
    try:
        # python-magicを優先
        import magic  # type: ignore

        mime = magic.Magic(mime=True)
        mime_type = mime.from_file(str(file_path))
        logger.debug(f"Detected MIME type (magic): {mime_type} for {file_path}")
        return mime_type
    except ImportError:
        # python-magic未インストール時はmimetypesでフォールバック
        logger.debug("python-magic not available, using mimetypes module")
        guessed_type = mimetypes.guess_type(str(file_path))
        detected_type: Optional[str] = guessed_type[0] if guessed_type[0] else None
        if detected_type:
            logger.debug(
                f"Detected MIME type (mimetypes): {detected_type} for {file_path}"
            )
            return detected_type
        logger.warning(f"Could not detect MIME type for {file_path}")
        return "application/octet-stream"
    except Exception as e:
        logger.error(f"Error detecting MIME type for {file_path}: {e}")
        return "application/octet-stream"


def validate_file_size(file_path: Path, max_size: int = MAX_FILE_SIZE) -> None:
    """ファイルサイズが制限内であることを検証します。

    Args:
        file_path: 検証対象のファイルパス
        max_size: 最大ファイルサイズ（バイト）。デフォルトは50MB。

    Raises:
        ValueError: ファイルサイズが制限を超えている場合

    Examples:
        >>> validate_file_size(Path("/tmp/small.txt"))  # OK
        >>> validate_file_size(Path("/tmp/huge.mp4"))  # ValueError
        Traceback (most recent call last):
        ...
        ValueError: File size (60.5 MB) exceeds limit (50.0 MB)
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    file_size = file_path.stat().st_size

    if file_size > max_size:
        size_mb = file_size / (1024 * 1024)
        limit_mb = max_size / (1024 * 1024)
        raise ValueError(
            f"File size ({size_mb:.1f} MB) exceeds limit ({limit_mb:.1f} MB): {file_path}"
        )

    logger.debug(f"File size validation passed: {file_size} bytes for {file_path}")


def validate_local_path(file_path: str) -> Path:
    """ローカルファイルパスのセキュリティ検証を行います。

    Path traversal攻撃を防ぐため、以下をチェック:
    1. 絶対パスに解決（resolve）
    2. 許可ディレクトリ内に存在するか検証
    3. ファイルが実在するか検証

    Args:
        file_path: 検証対象のファイルパス文字列

    Returns:
        Path: 検証済みの絶対パス

    Raises:
        ValueError: パスが許可ディレクトリ外の場合
        FileNotFoundError: ファイルが存在しない場合

    Examples:
        >>> validate_local_path("/tmp/sample.txt")
        PosixPath('/tmp/sample.txt')
        >>> validate_local_path("../../../etc/passwd")  # セキュリティエラー
        Traceback (most recent call last):
        ...
        ValueError: Path outside allowed directories
    """
    # 絶対パスに解決（シンボリックリンク解決含む）
    resolved_path = Path(file_path).resolve()

    # ファイル存在チェック
    if not resolved_path.exists():
        raise FileNotFoundError(f"File not found: {resolved_path}")

    # 許可ディレクトリチェック
    allowed = False
    for allowed_dir in ALLOWED_DIRECTORIES:
        allowed_dir_path = Path(allowed_dir).resolve()
        try:
            # resolved_pathがallowed_dir_path配下にあるかチェック
            resolved_path.relative_to(allowed_dir_path)
            allowed = True
            logger.debug(
                f"Path validation passed: {resolved_path} is under {allowed_dir_path}"
            )
            break
        except ValueError:
            # relative_to()が失敗 = 配下にない
            continue

    if not allowed:
        raise ValueError(
            f"Path outside allowed directories: {resolved_path}. "
            f"Allowed directories: {ALLOWED_DIRECTORIES}"
        )

    return resolved_path


def extract_google_drive_file_id(url: str) -> Optional[str]:
    """Google Drive URLからファイルIDを抽出します。

    対応するURL形式:
    - https://drive.google.com/file/d/{FILE_ID}/view
    - https://drive.google.com/open?id={FILE_ID}
    - https://drive.google.com/uc?id={FILE_ID}

    Args:
        url: Google DriveのURL

    Returns:
        str: ファイルID。抽出できない場合はNone。

    Examples:
        >>> extract_google_drive_file_id("https://drive.google.com/file/d/1ABC123/view")
        '1ABC123'
        >>> extract_google_drive_file_id("https://drive.google.com/open?id=1XYZ789")
        '1XYZ789'
        >>> extract_google_drive_file_id("https://example.com/invalid")
        None
    """
    # Pattern 1: /file/d/{FILE_ID}/view
    match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    if match:
        file_id = match.group(1)
        logger.debug(f"Extracted file ID (pattern 1): {file_id} from {url}")
        return file_id

    # Pattern 2: ?id={FILE_ID}
    match = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", url)
    if match:
        file_id = match.group(1)
        logger.debug(f"Extracted file ID (pattern 2): {file_id} from {url}")
        return file_id

    logger.warning(f"Could not extract file ID from URL: {url}")
    return None
