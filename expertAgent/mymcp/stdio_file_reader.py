"""File Reader MCP Server

FastMCPを使用したFile Reader MCPサーバー実装。
stdio transportを使用してLangGraphエージェントと統合されます。

提供するツール:
- read_file_from_url_tool: インターネットURLからファイルを読み込み
- read_file_from_google_drive_tool: Google Driveからファイルを読み込み
- read_file_from_local_tool: ローカルファイルシステムからファイルを読み込み
"""

import logging
import os
import tempfile
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from core.logger import setup_logging
from mymcp.tool.file_reader_processors import process_file
from mymcp.tool.file_reader_sources import (
    download_from_google_drive,
    download_from_url,
    read_from_local,
)

# デバッグ: MCPサブプロセス起動を記録（stdio通信と干渉しないように stderr へ）
debug_trace_file = Path(tempfile.gettempdir()) / "mcp_file_reader_debug.log"
try:
    with open(debug_trace_file, "a") as f:
        f.write(f"=== File Reader MCP subprocess started (PID: {os.getpid()}) ===\n")
        f.write(f"MCP_LOG_FILE env: {os.getenv('MCP_LOG_FILE')}\n")
        f.write(f"LOG_DIR env: {os.getenv('LOG_DIR')}\n")
        f.write(f"LOG_LEVEL env: {os.getenv('LOG_LEVEL')}\n")
except Exception as e:
    # デバッグ出力失敗は無視（本番動作に影響させない）
    import sys

    print(
        f"[stdio_file_reader.py] Debug trace write failed: {e}",
        file=sys.stderr,
        flush=True,
    )

# MCPサブプロセス専用のログファイル名を環境変数から取得
mcp_log_file = os.getenv("MCP_LOG_FILE", "mcp_file_reader.log")

try:
    with open(debug_trace_file, "a") as f:
        f.write(f"Calling setup_logging(log_file_name='{mcp_log_file}')\n")
except Exception as e:
    # デバッグ出力失敗は無視（本番動作に影響させない）
    import sys

    print(
        f"[stdio_file_reader.py] Debug trace write failed: {e}",
        file=sys.stderr,
        flush=True,
    )

setup_logging(log_file_name=mcp_log_file)

try:
    with open(debug_trace_file, "a") as f:
        f.write("setup_logging() completed successfully\n")
except Exception as e:
    # デバッグ出力失敗は無視（本番動作に影響させない）
    import sys

    print(
        f"[stdio_file_reader.py] Debug trace write failed: {e}",
        file=sys.stderr,
        flush=True,
    )

logger = logging.getLogger(__name__)

mcp = FastMCP("fileReaderMcp")


@mcp.tool()
async def read_file_from_url_tool(url: str, user_instruction: str) -> str:
    """インターネットURLからファイルをダウンロードし、抽出したテキストをそのまま返します。

    このツールは公開されているインターネット上のファイル（HTTP/HTTPS）をダウンロードし、
    ファイル形式に応じた処理を実行します:
    - PDF: 全ページのテキストを抽出してそのまま返す（要約しない）
    - 画像: Vision APIで解析
    - 音声: Whisper APIで文字起こし
    - テキスト/CSV: 内容をそのまま返す

    IMPORTANT: このツールは抽出したテキストをそのまま返します。
    要約や解釈が必要な場合は、あなた（LLM）が受け取ったテキストに対して行ってください。

    Args:
        url: ダウンロード元のHTTP/HTTPS URL
        user_instruction: ファイル処理に関するユーザーからの指示
                         （画像解析時のみ使用。PDFは全文抽出）

    Returns:
        str: 抽出されたテキスト全文（PDFの場合は全ページ）。
             失敗時はエラーメッセージ。

    Examples:
        >>> result = await read_file_from_url_tool(
        ...     "https://example.com/document.pdf",
        ...     "PDFの内容を抽出"
        ... )
        >>> print(result)
        "--- Page 1 ---\\nPDFの全文..."
    """
    logger.info(f"read_file_from_url_tool called: url={url}")

    try:
        # URLからファイルをダウンロード
        file_path, mime_type = await download_from_url(url)
        logger.info(f"Downloaded file from URL: {file_path}, MIME type: {mime_type}")

        # ファイルを処理
        result = process_file(file_path, mime_type, user_instruction)
        logger.info(f"File processing completed. Result length: {len(result)}")

        # 一時ファイルを削除
        try:
            file_path.unlink()
            logger.debug(f"Deleted temporary file: {file_path}")
        except Exception as cleanup_error:
            logger.warning(f"Failed to delete temporary file: {cleanup_error}")

        return result

    except Exception as e:
        error_msg = f"Failed to read file from URL: {e}"
        logger.error(error_msg)
        return f"Error: {error_msg}"


@mcp.tool()
def read_file_from_google_drive_tool(url: str, user_instruction: str) -> str:
    """Google Driveからファイルをダウンロードし、抽出したテキストをそのまま返します。

    このツールはGoogle Drive上のファイルをOAuth2認証を使用してダウンロードし、
    ファイル形式に応じた処理を実行します:
    - PDF: 全ページのテキストを抽出してそのまま返す（要約しない）
    - 画像: Vision APIで解析
    - 音声: Whisper APIで文字起こし
    - テキスト/CSV: 内容をそのまま返す

    認証情報はMyVaultから取得されます。

    IMPORTANT: このツールは抽出したテキストをそのまま返します。
    要約や解釈が必要な場合は、あなた（LLM）が受け取ったテキストに対して行ってください。

    Args:
        url: Google DriveのファイルURL
             （例: https://drive.google.com/file/d/FILE_ID/view）
        user_instruction: ファイル処理に関するユーザーからの指示
                         （画像解析時のみ使用。PDFは全文抽出）

    Returns:
        str: 抽出されたテキスト全文（PDFの場合は全ページ）。
             失敗時はエラーメッセージ。

    Examples:
        >>> result = read_file_from_google_drive_tool(
        ...     "https://drive.google.com/file/d/1ABC123XYZ/view",
        ...     "PDFの内容を抽出"
        ... )
        >>> print(result)
        "--- Page 1 ---\\nPDFの全文..."
    """
    logger.info(f"read_file_from_google_drive_tool called: url={url}")

    try:
        # Google Driveからファイルをダウンロード
        file_path, mime_type = download_from_google_drive(url)
        logger.info(
            f"Downloaded file from Google Drive: {file_path}, MIME type: {mime_type}"
        )

        # ファイルを処理
        result = process_file(file_path, mime_type, user_instruction)
        logger.info(f"File processing completed. Result length: {len(result)}")

        # 一時ファイルを削除
        try:
            file_path.unlink()
            logger.debug(f"Deleted temporary file: {file_path}")
        except Exception as cleanup_error:
            logger.warning(f"Failed to delete temporary file: {cleanup_error}")

        return result

    except Exception as e:
        error_msg = f"Failed to read file from Google Drive: {e}"
        logger.error(error_msg)
        return f"Error: {error_msg}"


@mcp.tool()
def read_file_from_local_tool(file_path: str, user_instruction: str) -> str:
    """ローカルファイルシステムからファイルを読み込み、抽出したテキストをそのまま返します。

    このツールはローカルファイルシステム上のファイルを読み込み、
    ファイル形式に応じた処理を実行します:
    - PDF: 全ページのテキストを抽出してそのまま返す（要約しない）
    - 画像: Vision APIで解析
    - 音声: Whisper APIで文字起こし
    - テキスト/CSV: 内容をそのまま返す

    セキュリティのため、許可されたディレクトリ内のファイルのみアクセス可能です。

    許可ディレクトリ:
    - /tmp, /var/tmp
    - ~/Downloads, ~/Documents

    IMPORTANT: このツールは抽出したテキストをそのまま返します。
    要約や解釈が必要な場合は、あなた（LLM）が受け取ったテキストに対して行ってください。

    Args:
        file_path: ローカルファイルの絶対パスまたは相対パス
        user_instruction: ファイル処理に関するユーザーからの指示
                         （画像解析時のみ使用。PDFは全文抽出）

    Returns:
        str: 抽出されたテキスト全文（PDFの場合は全ページ）。
             失敗時はエラーメッセージ。

    Examples:
        >>> result = read_file_from_local_tool(
        ...     "/tmp/document.pdf",
        ...     "PDFの内容を抽出"
        ... )
        >>> print(result)
        "--- Page 1 ---\\nPDFの全文..."
    """
    logger.info(f"read_file_from_local_tool called: file_path={file_path}")

    try:
        # ローカルファイルを読み込み（セキュリティ検証含む）
        validated_path, mime_type = read_from_local(file_path)
        logger.info(f"Validated local file: {validated_path}, MIME type: {mime_type}")

        # ファイルを処理
        result = process_file(validated_path, mime_type, user_instruction)
        logger.info(f"File processing completed. Result length: {len(result)}")

        return result

    except Exception as e:
        error_msg = f"Failed to read local file: {e}"
        logger.error(error_msg)
        return f"Error: {error_msg}"


if __name__ == "__main__":
    logger.debug("Starting File Reader MCP with stdio transport")
    mcp.run(transport="stdio")
