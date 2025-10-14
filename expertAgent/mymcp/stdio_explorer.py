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
async def gmail_search_search_tool(keyword: str, top: int = 5) -> Any:
    """gmailからキーワード検索した結果をtopに指定した件数文返却します。"""
    return get_emails_by_keyword(keyword, top)


if __name__ == "__main__":
    mcp.run(transport="stdio")
