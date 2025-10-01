from typing import Any
from typing import Dict
from mymcp.googleapis.gmail.send import send_email
from mymcp.utils.generate_subject_from_text import generate_subject_from_text
from mymcp.tool.tts_and_upload_drive import tts_and_upload_drive
from mcp.server.fastmcp import FastMCP
from core.config import settings


mcp = FastMCP("myMcp")


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
    return send_email(settings.MAIL_TO, subject, body)


# @mcp.tool()
# async def generate_subject_from_text_tool(text_body: str, max_length: int = 20) -> str:
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


if __name__ == "__main__":
    mcp.run(transport='stdio')
