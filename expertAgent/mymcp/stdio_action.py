import os
import tempfile
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from core.logger import setup_logging
from core.secrets import resolve_runtime_value
from mymcp.googleapis.gmail.send import send_email
from mymcp.tool.tts_and_upload_drive import tts_and_upload_drive
from mymcp.utils.generate_subject_from_text import generate_subject_from_text

# デバッグ: MCPサブプロセス起動を記録（stdio通信と干渉しないように stderr へ）
debug_trace_file = Path(tempfile.gettempdir()) / "mcp_stdio_debug.log"
try:
    with open(debug_trace_file, "a") as f:
        f.write(f"=== MCP subprocess started (PID: {os.getpid()}) ===\n")
        f.write(f"MCP_LOG_FILE env: {os.getenv('MCP_LOG_FILE')}\n")
        f.write(f"LOG_DIR env: {os.getenv('LOG_DIR')}\n")
        f.write(f"LOG_LEVEL env: {os.getenv('LOG_LEVEL')}\n")
except Exception as e:
    # デバッグ出力失敗は無視（本番動作に影響させない）
    import sys

    print(
        f"[stdio_action.py] Debug trace write failed: {e}", file=sys.stderr, flush=True
    )

# MCPサブプロセス専用のログファイル名を環境変数から取得
mcp_log_file = os.getenv("MCP_LOG_FILE", "mcp_stdio.log")

try:
    with open(debug_trace_file, "a") as f:
        f.write(f"Calling setup_logging(log_file_name='{mcp_log_file}')\n")
except Exception as e:
    # デバッグ出力失敗は無視（本番動作に影響させない）
    import sys

    print(
        f"[stdio_action.py] Debug trace write failed: {e}", file=sys.stderr, flush=True
    )

setup_logging(log_file_name=mcp_log_file)

try:
    with open(debug_trace_file, "a") as f:
        f.write("setup_logging() completed successfully\n")
except Exception as e:
    # デバッグ出力失敗は無視（本番動作に影響させない）
    import sys

    print(
        f"[stdio_action.py] Debug trace write failed: {e}", file=sys.stderr, flush=True
    )

mcp = FastMCP("myMcp")


def _create_file_from_content(
    file_path: str,
    content: str | bytes,
    file_format: str,
) -> str:
    """コンテンツからファイルを作成する

    Args:
        file_path: 作成するファイルパス
        content: ファイル内容（テキストまたはバイナリ、Base64エンコード済み文字列も可）
        file_format: ファイル形式（拡張子: "pdf", "txt", "mp3"など）

    Returns:
        str: 実際に作成されたファイルパス（リネーム後）

    Raises:
        ValueError: パラメータ不正
        RuntimeError: ファイル作成失敗
    """
    import base64
    from datetime import datetime

    # 親ディレクトリ作成
    parent_dir = os.path.dirname(file_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    # ファイル名リネーム（既存ファイルがある場合）
    if os.path.exists(file_path):
        base_name = os.path.basename(file_path)
        name_without_ext = os.path.splitext(base_name)[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 連番付きファイル名生成
        counter = 1
        while True:
            new_name = f"{name_without_ext}_{counter:03d}_{timestamp}.{file_format}"
            new_path = os.path.join(parent_dir, new_name) if parent_dir else new_name
            if not os.path.exists(new_path):
                file_path = new_path
                break
            counter += 1
            if counter > 1000:
                raise RuntimeError(
                    "Failed to generate unique filename after 1000 attempts"
                )

    # ファイル作成
    try:
        if isinstance(content, str):
            # テキストコンテンツの場合
            # Base64エンコードされている可能性をチェック
            try:
                # Base64デコード試行
                decoded = base64.b64decode(content, validate=True)
                # デコード成功→バイナリファイル作成
                with open(file_path, "wb") as f:
                    f.write(decoded)
            except Exception:
                # デコード失敗→通常のテキストファイル
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

        elif isinstance(content, bytes):
            # バイナリコンテンツ
            with open(file_path, "wb") as f:
                f.write(content)

        else:
            raise ValueError(f"Unsupported content type: {type(content)}")

    except Exception as e:
        raise RuntimeError(f"Failed to create file: {e}") from e

    return file_path


@mcp.tool()
async def send_email_tool(body: str) -> str:
    """メール送信ツール。gmailサービスを利用してメール送信する

    入力したメールの本文から件名を自動生成し事前に設定した宛先にメールを送信し、
    結果を示すメッセージを返します。

    Args:
        body: メールの本文。

    Returns:
        str: 成功時は成功メッセージ、失敗時はエラーメッセージ。
    """
    subject = generate_subject_from_text(body)
    mail_to = resolve_runtime_value("MAIL_TO")
    if not mail_to:
        raise ValueError("MAIL_TO is not configured")

    return send_email(str(mail_to), subject, body)


# @mcp.tool()
# async def generate_subject_from_text_tool(
#     text_body: str,
#     max_length: int = 20,
# ) -> str:
#     """与えられたテキスト本文からタイトルを生成します。

#     Args:
#         text_body (str): タイトルを生成したいテキスト本文。
#         max_length (int): 生成するタイトルの最大文字数（目安）。

#     Returns:
#         str: 生成されたタイトル名。エラーの場合はエラーメッセージ。
#     """
#     return generate_subject_from_text(text_body, max_length)


@mcp.tool()
async def tts_and_upload_drive_tool(input_message: str, file_name: str) -> str:
    """ポッドキャスト作成ツール

    テキストの台本をインプットに音声合成を行い音声ファイル(.mp3)を生成しGoogle Driveにアップロードします。
    アップロードしたファイルへのURLリンクを返却します。

    Args:
        input_message (str): 音声合成するテキストメッセージ。
        file_name (str): Google Driveに保存する際のファイル名。

    Returns:
        str: アップロード結果を示すメッセージまたはファイルURリンク
    """
    return tts_and_upload_drive(input_message, file_name)


@mcp.tool()
async def upload_file_to_drive_tool(
    file_path: str,
    drive_folder_url: str | None = None,
    file_name: str | None = None,
    sub_directory: str | None = None,
    size_threshold_mb: int = 100,
    content: str | bytes | None = None,
    file_format: str | None = None,
    create_file: bool = False,
) -> str:
    """GoogleDriveファイルアップロードツール

    ローカルファイルをGoogleDriveの指定フォルダにアップロードし、リンクURLを返却します。
    ファイルサイズに応じて自動的に通常アップロードまたはResumable Uploadを選択します。

    コンテンツからファイルを作成してアップロードすることも可能です（create_file=True時）。

    Args:
        file_path: アップロード対象のローカルファイルパス（必須）
                  create_file=True の場合、作成先パスとして使用
        drive_folder_url: GoogleDriveフォルダのURL（任意、未指定時はルート）
                         例: https://drive.google.com/drive/folders/1a2b3c4d5e
        file_name: 保存時のファイル名（任意、未指定時は元のファイル名）
        sub_directory: サブディレクトリパス（任意、例: "reports/2025"）
        size_threshold_mb: Resumable Upload閾値（MB、デフォルト100MB）
        content: ファイル内容（create_file=True時のみ使用）
                テキスト、バイナリ、Base64エンコード文字列に対応
        file_format: ファイル形式の拡張子（create_file=True時のみ使用、例: "pdf", "txt"）
        create_file: ファイル作成モードを有効化（デフォルト: False）

    Returns:
        str: アップロード結果のJSONメッセージ
             成功時: {"status": "success", "file_id": "...", "web_view_link": "..."}
             エラー時: {"status": "error", "error_type": "...", "message": "..."}
    """
    import json
    import logging
    import os

    from mymcp.googleapis.drive import (
        create_subfolder_under_parent,
        extract_folder_id_from_url,
        generate_unique_filename,
        get_google_drive_file_links,
        get_mime_type,
        get_or_create_folder,
        resumable_upload,
        upload_file,
    )

    logger = logging.getLogger(__name__)
    created_file_path = None  # クリーンアップ用

    try:
        # 🆕 ファイル作成モード
        if create_file:
            if content is None:
                return json.dumps(
                    {
                        "status": "error",
                        "error_type": "ValueError",
                        "message": "create_file=True の場合、content パラメータが必須です",
                    },
                    ensure_ascii=False,
                )

            if file_format is None:
                return json.dumps(
                    {
                        "status": "error",
                        "error_type": "ValueError",
                        "message": "create_file=True の場合、file_format パラメータが必須です",
                    },
                    ensure_ascii=False,
                )

            # ファイル作成
            try:
                created_file_path = _create_file_from_content(
                    file_path, content, file_format
                )
                file_path = created_file_path  # 以降のロジックで使用
            except Exception as create_error:
                return json.dumps(
                    {
                        "status": "error",
                        "error_type": type(create_error).__name__,
                        "message": f"ファイル作成に失敗しました: {create_error}",
                    },
                    ensure_ascii=False,
                )

        # 1. ファイル存在チェック
        if not os.path.exists(file_path):
            return json.dumps(
                {
                    "status": "error",
                    "error_type": "FileNotFoundError",
                    "message": f"指定されたファイルが存在しません: {file_path}",
                },
                ensure_ascii=False,
            )

        if not os.path.isfile(file_path):
            return json.dumps(
                {
                    "status": "error",
                    "error_type": "ValueError",
                    "message": f"指定されたパスはファイルではありません: {file_path}",
                },
                ensure_ascii=False,
            )

        # 2. フォルダID取得
        folder_id = None
        folder_path = ""

        if drive_folder_url:
            try:
                folder_id = extract_folder_id_from_url(drive_folder_url)
                folder_path = "指定フォルダ"
            except ValueError as e:
                return json.dumps(
                    {
                        "status": "error",
                        "error_type": "ValueError",
                        "message": str(e),
                    },
                    ensure_ascii=False,
                )

        # 3. サブディレクトリ処理
        if sub_directory:
            if folder_id:
                # フォルダID配下にサブディレクトリを作成
                folder_id = create_subfolder_under_parent(folder_id, sub_directory)
                folder_path = (
                    f"{folder_path}/{sub_directory}" if folder_path else sub_directory
                )
            else:
                # ルートからのパスとしてサブディレクトリを作成
                folder_id = get_or_create_folder(sub_directory)
                folder_path = sub_directory

        # 4. ファイル名決定
        upload_filename = file_name if file_name else os.path.basename(file_path)

        # 5. 重複チェック＆ユニークファイル名生成
        if folder_id:
            upload_filename = generate_unique_filename(upload_filename, folder_id)

        # 6. MIMEタイプ判定
        mime_type = get_mime_type(file_path)

        # 7. ファイルサイズ取得
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

        # 8. アップロード実行（サイズに応じて切り替え）
        if file_size_mb >= size_threshold_mb:
            # Resumable Upload
            file_id = resumable_upload(upload_filename, file_path, mime_type, folder_id)
        else:
            # 通常アップロード
            file_id = upload_file(upload_filename, file_path, mime_type, folder_id)

        # 9. リンク取得
        links = get_google_drive_file_links(file_id)

        if not links:
            return json.dumps(
                {
                    "status": "error",
                    "error_type": "RuntimeError",
                    "message": f"ファイルはアップロードされましたが、リンク取得に失敗しました。File ID: {file_id}",
                },
                ensure_ascii=False,
            )

        # 10. 成功レスポンス
        result = json.dumps(
            {
                "status": "success",
                "file_id": file_id,
                "file_name": upload_filename,
                "web_view_link": links.get("webViewLink"),
                "web_content_link": links.get("webContentLink"),
                "folder_path": folder_path if folder_path else "ルート",
                "file_size_mb": round(file_size_mb, 2),
                "upload_method": "resumable"
                if file_size_mb >= size_threshold_mb
                else "normal",
            },
            ensure_ascii=False,
        )

        # 🆕 クリーンアップ（作成した一時ファイルを削除）
        if created_file_path:
            try:
                os.remove(created_file_path)
                logger.debug(f"Temporary file deleted: {created_file_path}")
            except Exception as cleanup_error:
                # 削除失敗はログに記録するがエラーにはしない
                logger.warning(
                    f"Failed to cleanup temporary file {created_file_path}: {cleanup_error}"
                )

        return result

    except Exception as e:
        # 🆕 エラー時もクリーンアップ
        if created_file_path and os.path.exists(created_file_path):
            try:
                os.remove(created_file_path)
                logger.debug(f"Temporary file deleted after error: {created_file_path}")
            except Exception as cleanup_error:
                logger.debug(f"Cleanup failed (ignored): {cleanup_error}")

        # 予期しないエラー
        import traceback

        error_detail = traceback.format_exc()
        return json.dumps(
            {
                "status": "error",
                "error_type": type(e).__name__,
                "message": str(e),
                "detail": error_detail,
            },
            ensure_ascii=False,
        )


if __name__ == "__main__":
    import logging

    logger = logging.getLogger(__name__)
    logger.debug("Starting myMcp with stdio transport")
    mcp.run(transport="stdio")
