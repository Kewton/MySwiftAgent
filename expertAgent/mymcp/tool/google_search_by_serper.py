import http.client
import json
from mymcp.utils.html2markdown import getMarkdown
from mymcp.utils.chatollama import (
    extract_knowledge_from_text
)  # この関数のシグネチャが変わることを想定
import concurrent.futures
from typing import List, Union, Tuple  # Tupleを追加
from pydantic import BaseModel, Field
# from mymcp.utils.html2markdown import getMarkdown # 重複インポートなのでコメントアウト
from core.config import settings
from core.logger import getlogger

logger = getlogger()


class SerperSearchResult(BaseModel):
    text: str | None = Field(None, description="")
    result: List[Union[dict, str]] = Field(..., description="")


async def google_search_by_serper_list(queries: List[str], num: int = 3) -> str:
    """Google Searchを用いて情報を取得し、結果を返す。

    Serper APIを使用してGoogle Searchを実行し、
    検索結果から必要な情報を抽出して返却する。

    Args:
        queries (List[str]): 検索クエリのリスト。
        num (int): 各クエリに対する検索結果の取得数。

    Returns:
        str: SerperSearchResultモデルをJSON文字列化したもの。
    """
    logger.info("Google Search_by_serper_listを実行します")
    # 変更点: 各オーガニック検索結果と元のクエリをタプルで保持するリスト
    _serperresults_with_queries: List[Tuple[str, dict]] = []
    for _query in queries:
        conn = http.client.HTTPSConnection("google.serper.dev")
        payload = json.dumps({
            "q": _query,
            "location": "Japan",
            "gl": "jp",
            "hl": "ja",
            "num": num
        })
        headers = {
            'X-API-KEY': settings.SERPER_API_KEY,
            'Content-Type': 'application/json'
        }
        try:
            conn.request("POST", "/search", payload, headers)
            res = conn.getresponse()
            data = res.read()
            jsondata = json.loads(data.decode("utf-8"))
            # organicキーが存在しない場合も考慮
            for organic_result in jsondata.get('organic', []):
                _serperresults_with_queries.append((_query, organic_result))
        except Exception as e:
            logger.error(f"Serper APIリクエスト中にエラーが発生しました (query: {_query}): {e}")
        finally:
            conn.close()

    results = []
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=num * 2
    ) as executor:
        futures = [
            executor.submit(
                get_entry_summary,
                organic_item_with_query[1],
                organic_item_with_query[0]
            )
            for organic_item_with_query in _serperresults_with_queries
        ]
        for f in concurrent.futures.as_completed(futures):
            try:
                results.append(f.result())
            except Exception as e:
                logger.error(f"get_entry_summaryの実行中にエラーが発生しました: {e}")

    result_model = SerperSearchResult(
        text="ok",  # または処理結果に応じたステータス
        result=results,
    )

    return result_model.model_dump_json()


async def get_overview_by_google_serper(
        queries: List[str], num: int = 3) -> str:
    """Google Searchを用いて情報を取得し、結果を返す。

    Serper APIを使用してGoogle Searchを実行し、
    検索結果から必要な情報を抽出して返却する。

    Args:
        queries (List[str]): 検索クエリのリスト
        num (int): 各クエリに対する検索結果の取得数。

    Returns:
        SerperSearchResult: 検索結果を含むpydanticモデル。
            - text (str): Gemini APIから返されたテキスト。
            - result (List[dict]): 検索結果から抽出したナレッジのリスト
    """
    logger.info("get_overview_by_google_serperを実行します")
    _serperresults = []
    for _query in queries:
        conn = http.client.HTTPSConnection("google.serper.dev")
        payload = json.dumps({
            "q": _query,
            "location": "Japan",
            "gl": "jp",
            "hl": "ja",
            "num": num
        })
        headers = {
            'X-API-KEY': settings.SERPER_API_KEY,
            'Content-Type': 'application/json'
        }
        try:
            conn.request("POST", "/search", payload, headers)
            res = conn.getresponse()
            data = res.read()
            jsondata = json.loads(data.decode("utf-8"))
            for key in [
                "searchParameters", "images", "relatedSearches", "credits",
                "answerBox", "knowledgeGraph", "peopleAlsoAsk",
                "relatedSearches"
            ]:
                jsondata.pop(key, None)
            _serperresults.append(jsondata)
        except Exception as e:
            logger.error(f"Serper APIリクエスト中にエラーが発生しました (query: {_query}): {e}")
        finally:
            conn.close()

    result_model = SerperSearchResult(
        text="ok",
        result=_serperresults,
    )
    return result_model.model_dump_json()


def get_entry_summary(_organic: dict, _original_query: str):
    """
    個別の検索結果から要約を取得する。

    Args:
        _organic (dict): Serperのオーガニック検索結果の1アイテム。
        _original_query (str): この検索結果を得るために使用された元のクエリ。

    Returns:
        dict: タイトル、リンク、抽出されたナレッジを含む辞書。
    """
    if not isinstance(_organic, dict):
        logger.warning(f"Warning: _organic is not dict: {_organic}")
        return {
            "title": "Invalid data",
            "link": "",
            "knowledge": "Invalid data provided to get_entry_summary"
        }

    title = _organic.get('title', 'タイトルなし')
    link = _organic.get('link', '')

    logger.info(
        f"get_entry_summary start: '{title}' (Query: '{_original_query}')"
    )

    md_content = getMarkdown(link, False)
    kl = "情報なし"
    result_text = ""
    markdown_extraction_successful = False

    if isinstance(md_content, dict):
        if md_content.get("state") == "success":
            result_text = md_content.get("result", "")
            markdown_extraction_successful = bool(result_text)
        else:
            logger.warning(
                "getMarkdown failed for link %s: State was %s" % (
                    link, md_content.get('state'))
            )
    elif isinstance(md_content, str):
        result_text = md_content
        markdown_extraction_successful = bool(result_text)
    else:
        logger.warning(
            "getMarkdown returned unexpected type for link %s: %s" % (
                link, type(md_content))
        )

    if result_text.startswith("JavaScript"):
        logger.warning(
            "'%s' (%s) content starts with 'JavaScript'. "
            "Skipping knowledge extraction."
            % (title, link)
        )
    elif markdown_extraction_successful:
        window_size = 2000
        overlap = 200
        snippets = []
        start = 0
        while start < len(result_text):
            end = min(start + window_size, len(result_text))
            snippets.append(result_text[start:end])
            if end == len(result_text):
                break
            start += window_size - overlap
        knowledges = []

        print(f"Extracting knowledge from {len(snippets)} snippets for query: {_original_query}")
        print(f"Snippets: {snippets}")

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=4
        ) as executor:
            _model_name = "mlx-community"
            futures_extraction = [
                executor.submit(
                    extract_knowledge_from_text,
                    _original_query,
                    snippet,
                    _model_name
                )
                for snippet in snippets
            ]
            for i, future in enumerate(
                concurrent.futures.as_completed(futures_extraction)
            ):
                try:
                    k = future.result()
                    if k:
                        knowledges.append(str(k))
                except Exception as e:
                    snippet_preview = (
                        snippets[i][:50] if i < len(snippets) else ''
                    )
                    logger.error(
                        "extract_knowledge_from_textの実行中にエラーが発生しました "
                        "(Query: %s, Snippet: %s...): %s"
                        % (_original_query, snippet_preview, e)
                    )
        if knowledges:
            kl = "\n".join(knowledges)
        else:
            kl = "ナレッジ抽出結果なし"
    else:
        kl = "Markdown取得失敗または内容なし"

    return {
        "title": title,
        "link": link,
        "knowledge": kl,
        "original_query": _original_query
    }