from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

import google.generativeai as genai
from pydantic import BaseModel

from core.config import settings
from core.logger import getlogger
from mymcp.utils.extract_knowledge_from_text import extract_knowledge_from_text
from mymcp.utils.html2markdown import getMarkdown

logger = getlogger()


class GroundingChunk(BaseModel):
    """Grounding情報の各チャンク（ウェブソース）"""

    uri: str
    title: str | None = None


class GroundingSupport(BaseModel):
    """回答セグメントとソースチャンクの対応関係"""

    segment_text: str
    segment_start_index: int
    segment_end_index: int
    grounding_chunk_indices: List[int]


class GroundingMetadata(BaseModel):
    """Google Searchのgrounding metadata"""

    web_search_queries: List[str] | None = None
    grounding_chunks: List[GroundingChunk] | None = None
    grounding_supports: List[GroundingSupport] | None = None


class GoogleSearchResult(BaseModel):
    text: str
    grounding_metadata: GroundingMetadata | None = None


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
        return (
            f"Error processing {uri}"  # エラー時にも何らかの値を返すか、Noneを返すなど
        )


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
                result = (
                    future.result()
                )  # タスクの結果を取得 (例外が発生した場合はここで再送出される)
                results.append({"uri": uri, "result": result})
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
    # NOTE: Google Search groundingは一部モデルでサポートされています
    # Gemini 2.5では grounding_metadata が空になる問題があるため、
    # テキスト内のURLを参照情報として利用します
    model = genai.GenerativeModel("models/gemini-2.5-flash")

    # Google Search toolの設定
    google_search_tool = genai.protos.Tool(
        google_search=genai.protos.Tool.GoogleSearch()
    )

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
        # Google Search機能を有効化してgenerate_contentを呼び出す
        response = model.generate_content(
            contents=_content,
            tools=[google_search_tool],
        )

        # レスポンス構造のデバッグ (MCPサーバーなのでprintを使用)
        print(f"[DEBUG] Response type: {type(response)}")
        print(f"[DEBUG] Has text attr: {hasattr(response, 'text')}")
        print(f"[DEBUG] Has _result attr: {hasattr(response, '_result')}")

        # grounding_metadata構造の詳細確認
        if hasattr(response, "_result") and response._result.candidates:
            candidate = response._result.candidates[0]
            print(f"[DEBUG] Has grounding_metadata: {hasattr(candidate, 'grounding_metadata')}")
            if hasattr(candidate, "grounding_metadata"):
                gm = candidate.grounding_metadata
                print(f"[DEBUG] grounding_metadata type: {type(gm)}")
                print(f"[DEBUG] grounding_metadata dir: {[x for x in dir(gm) if not x.startswith('_')]}")
                print(f"[DEBUG] grounding_metadata: {gm}")

        if hasattr(response, "text"):
            text = response.text
            print(f"[DEBUG] Search result text: {text}")
        elif hasattr(response, "_result") and response._result.candidates:
            text = response._result.candidates[0].content.parts[0].text
            print(f"[DEBUG] Search result text (from _result): {text}")
        else:
            print("[ERROR] Unable to extract text from response")
            return GoogleSearchResult(
                text="検索結果の取得に失敗しました"
            ).model_dump_json()
    except Exception as e:
        print(f"[ERROR] Google Search failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return GoogleSearchResult(
            text=f"検索に失敗しました: {str(e)}"
        ).model_dump_json()

    # grounding_metadataを抽出
    grounding_metadata = None
    if (
        hasattr(response, "_result")
        and response._result.candidates
        and hasattr(response._result.candidates[0], "grounding_metadata")
    ):
        gm = response._result.candidates[0].grounding_metadata

        # webSearchQueriesを取得
        web_search_queries = None
        if hasattr(gm, "web_search_queries"):
            web_search_queries = list(gm.web_search_queries)

        # groundingChunksを取得
        grounding_chunks = []
        if hasattr(gm, "grounding_chunks"):
            for chunk in gm.grounding_chunks:
                if hasattr(chunk, "web"):
                    grounding_chunks.append(
                        GroundingChunk(
                            uri=chunk.web.uri if hasattr(chunk.web, "uri") else "",
                            title=(
                                chunk.web.title if hasattr(chunk.web, "title") else None
                            ),
                        )
                    )

        # groundingSupportsを取得
        grounding_supports = []
        if hasattr(gm, "grounding_supports"):
            for support in gm.grounding_supports:
                if hasattr(support, "segment"):
                    segment = support.segment
                    grounding_supports.append(
                        GroundingSupport(
                            segment_text=(
                                segment.text if hasattr(segment, "text") else ""
                            ),
                            segment_start_index=(
                                segment.start_index
                                if hasattr(segment, "start_index")
                                else 0
                            ),
                            segment_end_index=(
                                segment.end_index
                                if hasattr(segment, "end_index")
                                else 0
                            ),
                            grounding_chunk_indices=(
                                list(support.grounding_chunk_indices)
                                if hasattr(support, "grounding_chunk_indices")
                                else []
                            ),
                        )
                    )

        grounding_metadata = GroundingMetadata(
            web_search_queries=web_search_queries,
            grounding_chunks=grounding_chunks if grounding_chunks else None,
            grounding_supports=grounding_supports if grounding_supports else None,
        )

        logger.info(f"Google Searchのテキスト: {text}")
        logger.info(
            f"Grounding chunks: {len(grounding_chunks) if grounding_chunks else 0}"
        )
        logger.info(
            f"Web search queries: {web_search_queries if web_search_queries else 'N/A'}"
        )

    # pydanticモデルで結果を生成
    result_model = GoogleSearchResult(text=text, grounding_metadata=grounding_metadata)

    return result_model.model_dump_json()
