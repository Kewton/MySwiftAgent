import os
from typing import List
import google.generativeai as genai
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from mymcp.utils.html2markdown import getMarkdown
from core.config import settings
from mymcp.utils.extract_knowledge_from_text import extract_knowledge_from_text
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.logger import getlogger

logger = getlogger()


class GoogleSearchResult(BaseModel):
    text: str
    # result: List[dict] = Field(..., description="Gemini APIから返されたテキストと参照されたURIから取得したHTMLをマークダウンファイル化したもの")
    # search_entry_point: List[str] = Field(..., description="検索結果ページへのリンクのリスト")
    # uris: List[str] = Field(..., description="参照されたURIのリスト")


# 各URIに対する処理をまとめた関数
def process_uri_task(uri: str) -> str:
    """
    単一のURIに対する処理（getMarkdownとextract_knowledge_from_text）を実行する。
    スレッドプールで実行されるタスク。
    """
    try:
        markdown_content = getMarkdown(uri, False)
        knowledge = extract_knowledge_from_text(markdown_content)
        return knowledge
    except Exception as e:
        print(f"Error processing URI {uri}: {e}")
        return f"Error processing {uri}" # エラー時にも何らかの値を返すか、Noneを返すなど


def main_multithreaded(uris: List[str], max_workers: int) -> List[str]:
    """
    指定されたURIリストの処理をマルチスレッドで実行する。
    :param uris: 処理対象のURIのリスト
    :param max_workers: 同時実行する最大スレッド数
    :return: 処理結果のリスト
    """
    results = []
    # スレッドプールの作成 (最大ワーカー数を指定)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 各URIに対してタスクを投入
        # executor.submit は Future オブジェクトを返す
        future_to_uri = {executor.submit(process_uri_task, uri): uri for uri in uris}

        # as_completed を使うと、完了したタスクから順に結果を取得できる
        # (結果の順序は保証されないが、効率的)
        for future in as_completed(future_to_uri):
            uri = future_to_uri[future]
            try:
                result = future.result()  # タスクの結果を取得 (例外が発生した場合はここで再送出される)
                results.append({
                    "uri": uri,
                    "result": result
                })
            except Exception as exc:
                # エラー結果をリストに追加することも可能
                results.append(f"Failed: {uri} due to {exc}")
    return results


def googleSearchAgent(_input: str) -> str:
    """Google Searchを用いて情報を取得し、結果を返す。

    Gemini APIを使用してGoogle Searchを実行し、
    検索結果から必要な情報を抽出して返却する。

    Args:
        _input (str): 検索クエリ。

    Returns:
        GoogleSearchResult: 検索結果を含むpydanticモデル。
              - result (str): Gemini APIから返されたテキスト。
              - search_entry_point (List[str]): 検索結果ページへのリンクのリスト。
              - uris (List[str]): 参照されたURIのリスト。

    Examples:
        >>> googleSearchAgent("東京スカイツリーの高さ")
        GoogleSearchResult(
            text="東京スカイツリーの高さは634mです。"
        )
    """
    logger.info("Google Searchを実行します")
    # APIキーの取得と設定（環境変数から取得する）
    genai.configure(api_key=settings.GOOGLE_API_KEY)

    # Google Search (Grounding)機能を使用するモデル
    # 参考: https://ai.google.dev/gemini-api/docs/google-search?hl=ja
    # Gemini 2.0では generate_content_config で google_search を指定
    model = genai.GenerativeModel('models/gemini-2.0-flash-exp')

    _content = f"""
    # 命令指示書
    - 要求に対し前提条件と制約条件を満たす最高の成果物を生成してください。

    # 前提条件
    - あなたは検索AIエージェントです

    # 制約条件
    - 参照したサイト情報を返却に含めること

    # 要求
    {_input}
    """

    try:
        # Google Search機能はモデル側の機能なのでtoolsパラメータは使用しない
        # 単純にgenerate_contentを呼び出す
        response = model.generate_content(contents=_content)

        # レスポンス構造のデバッグ (MCPサーバーなのでprintを使用)
        print(f"[DEBUG] Response type: {type(response)}")
        print(f"[DEBUG] Has text attr: {hasattr(response, 'text')}")
        print(f"[DEBUG] Has _result attr: {hasattr(response, '_result')}")

        if hasattr(response, 'text'):
            text = response.text
            print(f"[DEBUG] Search result text: {text}")
        elif hasattr(response, '_result') and response._result.candidates:
            text = response._result.candidates[0].content.parts[0].text
            print(f"[DEBUG] Search result text (from _result): {text}")
        else:
            print("[ERROR] Unable to extract text from response")
            return GoogleSearchResult(text="検索結果の取得に失敗しました").model_dump_json()
    except Exception as e:
        print(f"[ERROR] Google Search failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return GoogleSearchResult(text=f"検索に失敗しました: {str(e)}").model_dump_json()


    # # BeautifulSoupを用いてレンダリングされたHTMLからリンクを抽出
    # soup = BeautifulSoup(
    #     response._result.candidates[0].grounding_metadata.search_entry_point.rendered_content,
    #     'html.parser'
    # )
    # links = []
    # links = [a['href'] for a in soup.find_all('a') if a.has_attr('href')]

    uris = []
    markdowns = []
    for chunk in response._result.candidates[0].grounding_metadata.grounding_chunks:
        # chunk.web.uriが存在することを確認して追加
        if hasattr(chunk.web, 'uri'):
            uris.append(chunk.web.uri)

    print(len(uris))
    markdowns.append({"GoogleApiResponse": text})
    # for uri in uris:
    #     _k = extract_knowledge_from_text(getMarkdown(uri, False))
    #     markdowns.append(_k)
    # max_concurrent_threads = 4
    # processed_markdowns = main_multithreaded(uris, max_concurrent_threads)
    # for result_item in processed_markdowns:
    #     markdowns.append(result_item)

    # logger.info("Google Searchの結果を取得しました。")
    logger.info(f"Google Searchのテキスト: {text}")
    # logger.info(f"Google Searchの結果: {markdowns}")
    # logger.info(f"Google Searchのリンク: {links}")
    # logger.info(f"Google SearchのURI: {uris}")
    # pydanticモデルで結果を生成
    result_model = GoogleSearchResult(
        text=text
        # result=markdowns,
        # search_entry_point=links,
        # uris=uris
    )

    # print(result_model.model_dump_json())

    return result_model.model_dump_json()
