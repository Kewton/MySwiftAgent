import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from core.logger import getlogger
from mymcp.googleapis.googleapi_services import get_googleapis_service

logger = getlogger()
SERVICE_NAME = "gmail"


def send_email(to_email: str, subject: str, body: str) -> str:
    """
    指定された宛先にメールを送信し、結果を示すメッセージを返します。

    Args:
        to_email: 送信先のメールアドレス。
        subject: メールの件名。
        body: メールの本文。

    Returns:
        str: 成功時は成功メッセージ、失敗時はエラーメッセージ。
    """
    if not to_email:
        return "エラー: 送信先のメールアドレスが指定されていません。"

    try:
        logger.info(f"Sending email to '{to_email}' with subject '{subject}'")
        service = get_googleapis_service(SERVICE_NAME)
        if not service:
            return f"エラー: {SERVICE_NAME} API サービスを取得できませんでした。認証を確認してください。"

        # MIMEメッセージを作成
        message = MIMEMultipart()
        message["To"] = to_email
        # From は Gmail API が自動的に認証ユーザーのアドレスを設定するので "me" で良い
        message["From"] = "me"
        message["Subject"] = subject

        # 本文中の \n を改行に変換 (念のため)
        body_processed = body.replace("\\n", "\n")

        # メール本文を設定 (プレーンテキスト、UTF-8)
        msg_body = MIMEText(body_processed, "plain", "utf-8")
        message.attach(msg_body)

        # メッセージをエンコード
        raw_msg = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        message_body = {"raw": raw_msg}

        # メールを送信 (send API呼び出し)
        sent_message = (
            service.users().messages().send(userId="me", body=message_body).execute()
        )

        logger.info(f"Email sent successfully. Message ID: {sent_message.get('id')}")
        return f"メールを {to_email} に正常に送信しました。件名: '{subject}'"  # 成功メッセージ

    except RefreshError as e:
        error_msg = f"エラー: Gmail API の認証トークンのリフレッシュに失敗しました。再認証が必要かもしれません。詳細: {e}"
        logger.error(f"Token refresh failed: {e}", exc_info=True)
        return error_msg  # エラーメッセージ
    except HttpError as e:
        # HttpErrorから詳細な情報を取得
        error_details = (
            f"ステータスコード: {e.resp.status}, 内容: {e.content.decode('utf-8')}"
        )
        error_msg = (
            f"エラー: Gmail API リクエストでエラーが発生しました。{error_details}"
        )
        logger.error(f"Gmail API request error: {error_details}", exc_info=True)
        return error_msg  # エラーメッセージ
    except Exception as e:
        # その他の予期せぬエラー
        error_msg = f"エラー: メール送信中に予期せぬエラーが発生しました: {e}"
        logger.error(f"Unexpected error during email sending: {e}", exc_info=True)
        return error_msg  # エラーメッセージ


def send_email_old(to_email, subject, body):
    try:
        logger.info("Starting email send (old implementation)")
        service = get_googleapis_service(SERVICE_NAME)

        # MIMEメッセージを作成
        message = MIMEMultipart()
        message["To"] = to_email
        message["From"] = "me"
        message["Subject"] = subject

        body_processed = body.replace("\\n", "\n")

        # メール本文を設定
        msg_body = MIMEText(body_processed, "plain", "utf-8")
        message.attach(msg_body)

        # メッセージをbase64エンコード
        raw_msg = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        message_body = {"raw": raw_msg}

        # メールを送信
        service.users().messages().send(userId="me", body=message_body).execute()

        logger.info("Email sent successfully (old implementation)")
        return True
    except RefreshError as e:
        logger.error(f"Error refreshing the token: {e}", exc_info=True)
        logger.debug(f"Error details: {e.args}")
        return False
    except HttpError as e:
        logger.error(f"Standard HttpError: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Exception occurred: {e}", exc_info=True)
        return False
