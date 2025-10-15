from typing import Any, List

from mcp.server.fastmcp import FastMCP

from mymcp.googleapis.gmail.readonly import get_emails_by_keyword
from mymcp.tool.google_search_by_serper import get_overview_by_google_serper
from mymcp.utils.html2markdown import getMarkdown

mcp = FastMCP("explorer")


@mcp.tool()
async def google_search_tool(input_query: List[str]) -> str:
    """Google Searchを用いて情報を取得し、結果を返す。

    Google Searchを実行し、webサイトからナレッジを抽出して返却する。

    Args:
        _query (List[str]): 検索クエリ。

    Returns:
        - text (str): 取得結果。成功時はOKが返却されます
        - result (List[dict]): 検索結果から抽出したナレッジ
    """
    return await get_overview_by_google_serper(input_query)


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


@mcp.tool()
async def gmail_search_search_tool(
    keyword: str,
    top: int = 5,
    search_in: str = "all",
    unread_only: bool = False,
    has_attachment: bool | None = None,
    date_after: str | None = None,
    date_before: str | None = None,
    labels: list[str] | None = None,
    include_summary: bool = False,
) -> Any:
    """Gmailから条件に合致するメールを検索し、詳細情報を返却します。

    このツールは、Gmailの高度な検索機能を提供します。
    キーワード検索だけでなく、日付範囲、未読状態、添付ファイル有無など、
    多様な条件でメールをフィルタリングできます。

    Args:
        keyword (str): 検索キーワード。必須。
            - 例: "会議", "meeting", "invoice"

        top (int): 取得するメールの最大件数。デフォルト: 5
            - 最大100件まで指定可能
            - 例: 10（最新10件を取得）

        search_in (str): 検索対象フィールド。デフォルト: "all"
            - "subject": 件名のみ検索
            - "body": 本文のみ検索
            - "from": 送信者のみ検索
            - "to": 宛先のみ検索
            - "all": 全フィールドを検索（デフォルト）
            - 例: "subject"（件名のみを検索したい場合）

        unread_only (bool): 未読メールのみ取得。デフォルト: False
            - True: 未読メールのみ
            - False: 既読・未読両方
            - 例: True（未読メールのみ取得したい場合）

        has_attachment (bool | None): 添付ファイル有無でフィルタ。デフォルト: None
            - True: 添付ファイルがあるメールのみ
            - False: 添付ファイルがないメールのみ
            - None: 添付ファイルの有無を問わない（デフォルト）
            - 例: True（請求書PDFなどの添付ファイル付きメールを探す場合）

        date_after (str | None): 指定日以降のメールを検索。デフォルト: None
            - 絶対日付: "2025/10/01" または "2025-10-01"
            - 相対日付: "7d"（7日前から）, "2w"（2週間前から）, "3m"（3ヶ月前から）, "1y"（1年前から）
            - None: 日付制限なし（デフォルト）
            - 例: "7d"（過去1週間のメールを検索）
            - 例: "2025/10/01"（2025年10月1日以降のメールを検索）

        date_before (str | None): 指定日以前のメールを検索。デフォルト: None
            - 絶対日付: "2025/10/15" または "2025-10-15"
            - None: 日付制限なし（デフォルト）
            - 例: "2025/10/15"（2025年10月15日以前のメールを検索）
            - 注意: date_afterと組み合わせて期間指定が可能

        labels (list[str] | None): ラベルでフィルタ。デフォルト: None
            - Gmailのラベル名のリスト
            - None: ラベルフィルタなし（デフォルト）
            - 例: ["important", "work"]（重要かつ仕事ラベル付きメールを検索）

        include_summary (bool): AIによるメール要約を含めるか。デフォルト: False
            - True: メール内容のAI要約を生成して含める
            - False: 要約を生成しない（デフォルト）
            - 注意: Trueにすると処理時間が増加します
            - 例: True（複数メールの内容を要約して把握したい場合）

    Returns:
        dict: 検索結果とメール詳細情報を含む辞書
            - total_count (int): 検索でヒットしたメールの総数
            - returned_count (int): 実際に返却されたメール数（top以下）
            - emails (list): メール詳細情報のリスト
                各メールには以下の情報が含まれます：
                - id (str): メールID
                - thread_id (str): スレッドID
                - subject (str): 件名
                - from (str): 送信者メールアドレス
                - to (list[str]): 宛先メールアドレスのリスト
                - cc (list[str]): CCメールアドレスのリスト
                - date (str): 送信日時
                - snippet (str): メールのプレビュー
                - body_text (str): プレーンテキスト本文
                - body_html (str): HTML本文
                - body_markdown (str): Markdown形式本文（読みやすい）
                - has_attachments (bool): 添付ファイル有無
                - attachments (list): 添付ファイル情報のリスト
                    - filename (str): ファイル名
                    - mimeType (str): MIMEタイプ
                    - size (int): ファイルサイズ（バイト）
                    - attachmentId (str): 添付ファイルID
                - labels (list[str]): ラベルのリスト
                - is_unread (bool): 未読フラグ
            - summary (str): AI生成の要約（include_summary=Trueの場合のみ）
            - error (str): エラーメッセージ（エラー発生時のみ）

    Usage Examples:
        # 基本的な検索
        gmail_search_search_tool("会議")

        # 過去1週間の未読メールを検索
        gmail_search_search_tool("報告書", date_after="7d", unread_only=True)

        # 特定期間の添付ファイル付きメールを検索
        gmail_search_search_tool(
            "請求書",
            search_in="subject",
            date_after="2025/10/01",
            date_before="2025/10/31",
            has_attachment=True
        )

        # 過去3ヶ月の重要メールをAI要約付きで取得
        gmail_search_search_tool(
            "プロジェクト",
            top=20,
            date_after="3m",
            labels=["important"],
            include_summary=True
        )

        # 特定の送信者からのメールを検索
        gmail_search_search_tool(
            "john@example.com",
            search_in="from",
            top=10
        )

    Notes:
        - 日付検索では相対日付（"7d", "2w", "3m", "1y"）が便利です
        - 複数の条件を組み合わせることで、より精密な検索が可能です
        - include_summary=Trueは処理に時間がかかるため、必要な場合のみ使用してください
        - エラーが発生した場合、返却値の"error"キーにエラーメッセージが含まれます
        - 検索結果が0件の場合、emails=[]の空リストが返却されます
    """
    return get_emails_by_keyword(
        keyword=keyword,
        top=top,
        search_in=search_in,
        unread_only=unread_only,
        has_attachment=has_attachment,
        date_after=date_after,
        date_before=date_before,
        labels=labels,
        include_summary=include_summary,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
