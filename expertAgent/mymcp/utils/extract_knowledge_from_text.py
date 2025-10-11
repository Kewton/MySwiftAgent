from core.logger import getlogger
from core.secrets import resolve_runtime_value
from mymcp.utils.execllm import execLlmApi

logger = getlogger()


def extract_knowledge_from_text(
    _text: str,
    _model: str | None = None,
):
    _query = f"""
    # 命令指示書
    入力情報と制約条件に従って最高の成果物を日本語で生成してください。
    なお、「429エラー」の場合は、"429エラーのため情報なし"と返却してください。

    ---
    # 制約条件
    - ナレッジを抽出し、箇条書きで端的に表現すること
    - 重要な情報を優先すること
    - 日本語で返却すること
    - 重要度の低い情報は削除すること

    ---
    # 入力情報
    {_text}

    ---

    /no_think
    """

    _messages = []
    _messages.append({"role": "user", "content": _query})

    resolved_model = _model or resolve_runtime_value("EXTRACT_KNOWLEDGE_MODEL")
    if not resolved_model:
        raise ValueError("EXTRACT_KNOWLEDGE_MODEL is not configured")

    result = execLlmApi(str(resolved_model), _messages)

    logger.info("Knowledge extraction completed")
    snippet = result[:200] if result and len(result) > 200 else result
    logger.debug(
        "Extracted knowledge (length: %s): %s",
        len(result) if result else 0,
        snippet,
    )

    return result
