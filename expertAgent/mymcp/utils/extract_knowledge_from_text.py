from mymcp.utils.execllm import execLlmApi
from core.config import settings


def extract_knowledge_from_text(_text: str, _model: str = settings.EXTRACT_KNOWLEDGE_MODEL):
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
    _messages.append(
        {"role": "user", "content": _query}
    )

    result = execLlmApi(_model, _messages)

    print("@extract_knowledge_from_text:")
    print(result)

    return result
