import os
import tempfile
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from core.logger import setup_logging
from core.secrets import resolve_runtime_value
from mymcp.googleapis.gmail.readonly import get_emails_by_keyword
from mymcp.googleapis.gmail.send import send_email
from mymcp.specializedtool.generate_melmaga_script import (
    generate_melmaga_and_send_email_from_urls,
)
from mymcp.tool.generate_melmaga_script import generate_melmaga_script
from mymcp.tool.generate_podcast_script import (
    generate_podcast_mp3_and_upload,
    generate_podcast_script,
)
from mymcp.tool.google_search_by_gemini import googleSearchAgent
from mymcp.tool.tts_and_upload_drive import tts_and_upload_drive
from mymcp.utils.generate_subject_from_text import generate_subject_from_text
from mymcp.utils.html2markdown import getMarkdown

# デバッグ: MCPサブプロセス起動を記録（stdio通信と干渉しないようにファイルへ）
debug_trace_file = Path(tempfile.gettempdir()) / "mcp_stdio_debug.log"
try:
    with open(debug_trace_file, "a") as f:
        f.write(f"=== MCP subprocess (stdioall.py) started (PID: {os.getpid()}) ===\n")
        f.write(f"MCP_LOG_FILE env: {os.getenv('MCP_LOG_FILE')}\n")
        f.write(f"LOG_DIR env: {os.getenv('LOG_DIR')}\n")
        f.write(f"LOG_LEVEL env: {os.getenv('LOG_LEVEL')}\n")

        # MyVault関連の環境変数確認
        f.write("\n=== MyVault Environment Variables ===\n")
        f.write(f"MYVAULT_ENABLED: {os.getenv('MYVAULT_ENABLED')}\n")
        f.write(f"MYVAULT_BASE_URL: {os.getenv('MYVAULT_BASE_URL')}\n")
        f.write(f"MYVAULT_SERVICE_NAME: {os.getenv('MYVAULT_SERVICE_NAME')}\n")
        token_status = "*" * 10 if os.getenv("MYVAULT_SERVICE_TOKEN") else "EMPTY"
        f.write(f"MYVAULT_SERVICE_TOKEN: {token_status}\n")

        # Google APIs関連の環境変数確認
        f.write("\n=== Google APIs Environment Variables ===\n")
        f.write(
            f"GOOGLE_APIS_DEFAULT_PROJECT: {os.getenv('GOOGLE_APIS_DEFAULT_PROJECT')}\n"
        )
        google_key_status = "*" * 10 if os.getenv("GOOGLE_API_KEY") else "EMPTY"
        f.write(f"GOOGLE_API_KEY: {google_key_status}\n")

        # その他のAPI Key確認
        f.write("\n=== Other API Keys ===\n")
        openai_status = "*" * 10 if os.getenv("OPENAI_API_KEY") else "EMPTY"
        f.write(f"OPENAI_API_KEY: {openai_status}\n")
        anthropic_status = "*" * 10 if os.getenv("ANTHROPIC_API_KEY") else "EMPTY"
        f.write(f"ANTHROPIC_API_KEY: {anthropic_status}\n")
        serper_status = "*" * 10 if os.getenv("SERPER_API_KEY") else "EMPTY"
        f.write(f"SERPER_API_KEY: {serper_status}\n")

        f.write("\n=== End of Environment Variables Check ===\n\n")
except Exception as e:
    # デバッグ出力失敗は無視（本番動作に影響させない）
    import sys

    print(f"[stdioall.py] Debug trace write failed: {e}", file=sys.stderr, flush=True)

# MCPサブプロセス専用のログファイル名を環境変数から取得
mcp_log_file = os.getenv("MCP_LOG_FILE", "mcp_stdio.log")

try:
    with open(debug_trace_file, "a") as f:
        f.write(f"Calling setup_logging(log_file_name='{mcp_log_file}')\n")
except Exception as e:
    # デバッグ出力失敗は無視（本番動作に影響させない）
    import sys

    print(f"[stdioall.py] Debug trace write failed: {e}", file=sys.stderr, flush=True)

setup_logging(log_file_name=mcp_log_file)

try:
    with open(debug_trace_file, "a") as f:
        f.write("setup_logging() completed successfully\n")
except Exception as e:
    # デバッグ出力失敗は無視（本番動作に影響させない）
    import sys

    print(f"[stdioall.py] Debug trace write failed: {e}", file=sys.stderr, flush=True)

mcp = FastMCP("myMcp")


def _resolve_mail_to() -> str:
    mail_to = resolve_runtime_value("MAIL_TO")
    if not mail_to:
        raise ValueError("MAIL_TO is not configured")
    return str(mail_to)


def _resolve_podcast_model() -> str:
    model_value = resolve_runtime_value("PODCAST_SCRIPT_DEFAULT_MODEL")
    if not model_value:
        raise ValueError("PODCAST_SCRIPT_DEFAULT_MODEL is not configured")
    return str(model_value)


@mcp.tool()
async def gmail_search_search_tool(keywrod: str, top: int = 5) -> Any:
    """gmailからキーワード検索した結果をtopに指定した件数文返却します。"""
    return get_emails_by_keyword(keywrod, top)


@mcp.tool()
async def send_email_tool(body: str) -> str:
    """gmailサービスを利用してメール送信する

    入力したメールの本文から件名を自動生成し事前に設定した宛先にメールを送信し、
    結果を示すメッセージを返します。

    Args:
        body: メールの本文。

    Returns:
        str: 成功時は成功メッセージ、失敗時はエラーメッセージ。
    """
    subject = generate_subject_from_text(body)
    return send_email(_resolve_mail_to(), subject, body)


@mcp.tool()
async def generate_melmaga_script_from_urls_tool(input_urls: list[str]) -> str:
    """入力されたURLから情報を収集しメルマガを生成してメール送信します。

    指定されたURLを元にLLMを活用してメルマガを生成し、指定されたメールアドレスに送信します。
    【重要】：URLは最大5個まで指定可能です。wikipediaは指定不可です。
    各URLから情報を取得し、メルマガの本文を生成します。
    メルマガの件名は本文から自動生成されます。
    メルマガの本文は、各URLに対する情報をテーマごとにまとめたものになります。
    各テーマは、URLごとに分けられています。

    Args:
        urls (list): メルマガを生成するためのURLのリスト。
            例）['https://sportsbull.jp/p/2047296/',
                'https://www.expo2025.or.jp/']

    Returns:
        str: 生成したメルマガ
    """
    return generate_melmaga_and_send_email_from_urls(input_urls)


@mcp.tool()
async def generate_melmaga_script_tool(input_info: str) -> str:
    """指定された情報とモデル名からメルマガを生成する

    指定された情報を元にLLMを活用してメルマガを生成します
    インプット情報が詳細で具体的であればあるほど良いです。
    集めた情報をそのまま入力してください。

    Args:
        input_info (str): メルマガを生成するためのインプット情報。詳細で具体的であればあるほど良いです。

    Returns:
        str: 生成したメルマガ
    """
    result = generate_melmaga_script(input_info, _resolve_podcast_model())
    if not isinstance(result, str):
        raise ValueError("generate_melmaga_script must return a string")
    return result


@mcp.tool()
async def generate_podcast_script_tool(
    topic_details: str,
    model_name: str | None = None,
) -> str:
    """与えられたトピック詳細情報からポッドキャストの台本を生成します。

    Args:
        topic_details (str): ポッドキャストのトピック、キーポイント、構成案などの詳細情報。
        model_name (str): 台本生成に使用するOpenAIモデル名 (デフォルト: gpt-4o-mini)。

    Returns:
        str: 生成されたポッドキャスト台本テキスト。
    """
    resolved_model = model_name or _resolve_podcast_model()
    result = generate_podcast_script(topic_details, resolved_model)
    if not isinstance(result, str):
        raise ValueError("generate_podcast_script must return a string")
    return result


@mcp.tool()
async def generate_podcast_mp3_and_upload_tool(
    topic_details: str,
    model_name: str | None = None,
    subject_max_length: int = 25,
) -> str:
    """与えられたトピック詳細情報からポッドキャストの台本を生成し、
    その内容から件名を生成、テキストをMP3音声に変換してGoogle Driveにアップロードします。

    Args:
        topic_details (str): ポッドキャストのトピック、キーポイント、構成案などの詳細情報。
        model_name (str): 台本生成に使用するOpenAIモデル名 (デフォルト: gpt-4o-mini)。
        subject_max_length (int): 生成する件名の最大文字数 (デフォルト: 25)。

    Returns:
        str: Google Driveへのアップロード結果を示すメッセージまたはファイルURL。
    """
    resolved_model = model_name or _resolve_podcast_model()
    return generate_podcast_mp3_and_upload(
        topic_details, resolved_model, subject_max_length
    )


@mcp.tool()
async def google_search_tool(input_query: str) -> str:
    """Google Searchを用いて情報を取得し、結果を返す。

    Gemini APIを使用してGoogle Searchを実行し、
    検索結果から必要な情報を抽出して返却する。

    Args:
        query (str): 検索クエリ。

    Returns:
        dict: 検索結果を含む辞書。
              - result (str): Gemini APIから返されたテキストと
                  参照されたURIから取得したHTMLをマークダウン化したもの。
              - search_entry_point (List[str]): 検索結果ページへのリンクのリスト。
              - uris (List[str]): 参照されたURIのリスト。
    Examples:
        >>> google_search_tool("東京スカイツリーの高さ")
        GoogleSearchResult(
            result="東京スカイツリーの高さは634mです。",
            search_entry_point=["https://www.tokyo-skytree.jp/"],
            uris=["https://ja.wikipedia.org/wiki/東京スカイツリー"]
        )
    """
    return googleSearchAgent(input_query)


@mcp.tool()
async def tts_and_upload_drive_tool(input_message: str, file_name: str) -> str:
    """音声合成を行い、生成した音声ファイルをGoogle Driveにアップロードします。

    Args:
        input_message (str): 音声合成するテキストメッセージ。
        file_name (str): Google Driveに保存する際のファイル名。

    Returns:
        str: アップロード結果を示すメッセージまたはファイルURL。
    """
    return tts_and_upload_drive(input_message, file_name)


@mcp.tool()
async def getMarkdown_tool(input_url: str) -> str:
    """指定されたURLからHTMLを取得し、マークダウン形式に変換します。
    Args:
        url (str): 変換するURL。
    Returns:
        str: マークダウン形式に変換されたテキスト。
    """
    markdown = getMarkdown(input_url)
    if not isinstance(markdown, str):
        raise ValueError("getMarkdown must return a string")
    return markdown


if __name__ == "__main__":
    mcp.run(transport="stdio")
