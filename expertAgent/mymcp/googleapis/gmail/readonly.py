import base64
import logging

from mymcp.googleapis.googleapi_services import get_googleapis_service
from mymcp.utils.extract_knowledge_from_text import extract_knowledge_from_text
from mymcp.utils.html_operation import convert_html_to_markdown

logger = logging.getLogger(__name__)

SERVICE_NAME = "gmail"


# 件名に指定されたキーワードが含まれるメールを検索し、本文を取得する関数
def get_emails_by_keyword(subject_keyword: str, top: int = 5):
    """
    指定された件名キーワードを含むメールを検索し、本文を取得します。
    件名キーワードは部分一致で検索されます。
    検索結果は最大で指定された件数まで取得されます。
    Args:
        subject_keyword (str): 検索する件名のキーワード。
        top (int): 取得するメールの最大件数。
    Returns:
        list: 検索結果のメール本文のリスト。
    """
    service = get_googleapis_service(SERVICE_NAME)

    # メールを検索 (件名にキーワードを含む)
    # query = f'subject:{subject_keyword}'
    query = f"{subject_keyword}"
    results = service.users().messages().list(userId="me", q=query).execute()

    messages = results.get("messages", [])
    if not messages:
        logger.warning(f"No emails found with keyword '{subject_keyword}'")
        return []

    email_bodies = []

    cnt = 0

    # メッセージIDを使ってメールの詳細を取得し、本文を抽出
    for message in messages:
        cnt += 1
        if cnt > top:
            break

        msg = service.users().messages().get(userId="me", id=message["id"]).execute()
        payload = msg["payload"]

        # メール本文のパートを探す
        body_data = None
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":  # "text/html" "text/plain"
                    body_data = part["body"]["data"]
                    break
        else:
            body_data = payload["body"]["data"]

        if body_data:
            # Base64でエンコードされたデータをデコード
            body_decoded = base64.urlsafe_b64decode(body_data.encode("ASCII")).decode(
                "utf-8"
            )
            email_bodies.append({"email_body": convert_html_to_markdown(body_decoded)})
        else:
            logger.warning(f"Could not extract body from email with ID {message['id']}")

    return {"result": extract_knowledge_from_text(email_bodies)}
