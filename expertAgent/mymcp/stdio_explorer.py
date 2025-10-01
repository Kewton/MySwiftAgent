from typing import List

from mcp.server.fastmcp import FastMCP

from mymcp.tool.google_search_by_serper import get_overview_by_google_serper

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
    return get_overview_by_google_serper(input_query)


if __name__ == "__main__":
    mcp.run(transport="stdio")
