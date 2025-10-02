from typing import Dict

from mcp.server.fastmcp import FastMCP

from core.config import settings
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

PODCAST_SCRIPT_DEFAULT_MODEL = settings.PODCAST_SCRIPT_DEFAULT_MODEL
mcp = FastMCP("myMcp")


@mcp.tool()
async def gmail_search_search_tool(keywrod: str, top: int = 5) -> Dict:
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
    return send_email(settings.MAIL_TO, subject, body)


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
        urls (list): メルマガを生成するためのURLのリスト。例）['https://sportsbull.jp/p/2047296/', 'https://www.expo2025.or.jp/']

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
    return generate_melmaga_script(input_info, PODCAST_SCRIPT_DEFAULT_MODEL)


@mcp.tool()
async def generate_podcast_script_tool(
    topic_details: str, model_name: str = PODCAST_SCRIPT_DEFAULT_MODEL
) -> str:
    """与えられたトピック詳細情報からポッドキャストの台本を生成します。

    Args:
        topic_details (str): ポッドキャストのトピック、キーポイント、構成案などの詳細情報。
        model_name (str): 台本生成に使用するOpenAIモデル名 (デフォルト: gpt-4o-mini)。

    Returns:
        str: 生成されたポッドキャスト台本テキスト。
    """
    return generate_podcast_script(topic_details, model_name)


@mcp.tool()
async def generate_podcast_mp3_and_upload_tool(
    topic_details: str,
    model_name: str = PODCAST_SCRIPT_DEFAULT_MODEL,
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
    return generate_podcast_mp3_and_upload(
        topic_details, model_name, subject_max_length
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
              - result (str): Gemini APIから返されたテキストと参照されたURIから取得したHTMLをマークダウンファイル化したもの。
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
    return getMarkdown(input_url)


if __name__ == "__main__":
    mcp.run(transport="stdio")
