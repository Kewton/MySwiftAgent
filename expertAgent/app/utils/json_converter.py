"""
JSON Conversion Utility

LLM レスポンスを確実に JSON 形式に変換するためのユーティリティ。
jsonOutput_agent.py のロジックを再利用し、全エンドポイントで共通化。

主要機能:
1. to_parse_json(): 文字列を JSON に変換（```json``` ブロック対応）
2. force_to_json_response(): 最終手段として必ず JSON を返却
"""

import json
import logging
import re
from typing import Any, cast

from langchain_core.output_parsers import JsonOutputParser

logger = logging.getLogger(__name__)


def to_parse_json(content: str) -> dict | list[Any]:
    """
    文字列を JSON に変換（jsonOutput_agent.toParseJson と同等）

    変換ルール:
    1. JSON として直接パース可能ならそのまま返却
    2. ```json ... ``` ブロックがあれば抽出してパース
    3. どちらも失敗したら ValueError を raise

    Args:
        content: 変換対象の文字列

    Returns:
        dict or list: パースされた JSON オブジェクト

    Raises:
        ValueError: JSON 変換に失敗した場合

    Example:
        >>> to_parse_json('{"result": "success"}')
        {'result': 'success'}

        >>> to_parse_json('```json\\n{"result": "success"}\\n```')
        {'result': 'success'}

        >>> to_parse_json('[1, 2, 3]')
        [1, 2, 3]
    """
    parser = JsonOutputParser()

    try:
        # 1. 直接 JSON としてパース
        parsed_json: dict[Any, Any] | list[Any] = cast(
            dict[Any, Any] | list[Any], parser.parse(content)
        )
        logger.info("Successfully parsed JSON directly")
        return parsed_json
    except Exception as e:
        logger.warning(f"Direct JSON parsing failed: {e}, trying regex extraction")

        # 2. ```json ... ``` ブロックから抽出（配列とオブジェクト両対応）
        match = re.search(r"```json\s*(\[.*?\]|\{.*?\})\s*```", content, re.DOTALL)

        if match:
            json_content = match.group(1)
            try:
                parsed_json = cast(dict[Any, Any] | list[Any], json.loads(json_content))
                logger.info("Successfully parsed JSON from code block")
                return parsed_json
            except json.JSONDecodeError as json_err:
                logger.error(f"JSONDecodeError after regex extraction: {json_err}")
                raise ValueError(
                    f"Failed to parse extracted JSON: {json_err}"
                ) from json_err
        else:
            logger.error("Could not extract JSON block using regex")
            raise ValueError(
                "Failed to extract JSON block from content. "
                "Content must be valid JSON or contain ```json...``` block"
            ) from e


def force_to_json_response(
    content: str, error_context: str = "", error_detail: str = ""
) -> dict[str, Any]:
    """
    どんな内容でも JSON レスポンス形式に変換（最終手段）

    この関数は to_parse_json() が失敗した場合の最終防衛線として機能します。
    必ず JSON 形式のレスポンスを返却することを保証します。

    Args:
        content: 変換対象の文字列
        error_context: エラー発生時のコンテキスト情報
        error_detail: エラーの詳細情報

    Returns:
        dict: JSON レスポンスオブジェクト（必ず is_json_guaranteed=True）

    Example:
        >>> force_to_json_response("plain text", "test context")
        {
            'result': 'plain text',
            'error': 'Failed to convert to JSON format',
            'error_context': 'test context',
            'is_json_guaranteed': True
        }
    """
    try:
        # まず to_parse_json で変換を試みる
        parsed = to_parse_json(content)

        # dict または list が返ってきた場合
        if isinstance(parsed, dict):
            # 既に正しい形式なら result キーがあるか確認
            if "result" in parsed:
                # is_json_guaranteed フラグを追加
                return {**parsed, "is_json_guaranteed": True}
            else:
                # result キーがなければラップ
                return {
                    "result": parsed,
                    "is_json_guaranteed": True,
                }
        elif isinstance(parsed, list):
            # list の場合は result に格納
            return {
                "result": parsed,
                "is_json_guaranteed": True,
            }
        else:
            # その他の型（通常発生しない）
            logger.warning(f"Unexpected parsed type: {type(parsed)}")
            return {
                "result": str(parsed),
                "is_json_guaranteed": True,
            }

    except ValueError as e:
        # JSON 変換に完全に失敗した場合
        logger.error(f"Complete JSON conversion failure: {e}")
        response: dict[str, Any] = {
            "result": content,  # 元の文字列をそのまま返す
            "error": "Failed to convert to JSON format",
            "is_json_guaranteed": True,
        }

        # オプション情報を追加
        if error_detail:
            response["error_detail"] = error_detail
        else:
            response["error_detail"] = str(e)

        if error_context:
            response["error_context"] = error_context

        return response


def ensure_json_structure(data: Any, default_type: str | None = None) -> dict[str, Any]:
    """
    任意のデータを ExpertAiAgentResponse 互換の JSON 構造に変換

    Args:
        data: 変換対象のデータ（任意の型）
        default_type: type フィールドのデフォルト値

    Returns:
        dict: ExpertAiAgentResponse 互換の構造

    Example:
        >>> ensure_json_structure("simple text", "test")
        {'result': 'simple text', 'type': 'test', 'is_json_guaranteed': True}

        >>> ensure_json_structure({"result": "data"}, "test")
        {'result': 'data', 'type': 'test', 'is_json_guaranteed': True}
    """
    if isinstance(data, dict):
        # 既に dict の場合
        result = data.copy()
        if "is_json_guaranteed" not in result:
            result["is_json_guaranteed"] = True
        if default_type and "type" not in result:
            result["type"] = default_type
        return result
    elif isinstance(data, str):
        # 文字列の場合
        return {
            "result": data,
            "type": default_type,
            "is_json_guaranteed": True,
        }
    elif isinstance(data, list):
        # リストの場合
        return {
            "result": data,
            "type": default_type,
            "is_json_guaranteed": True,
        }
    else:
        # その他の型
        return {
            "result": str(data),
            "type": default_type,
            "is_json_guaranteed": True,
        }
