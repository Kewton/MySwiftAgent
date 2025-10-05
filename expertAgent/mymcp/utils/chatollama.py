from datetime import datetime
from typing import List

import requests

from app.schemas.standardAiAgent import ChatMessage
from core.config import settings


def chatOllama(
    _messages: List[ChatMessage],
    _model: str = settings.OLLAMA_DEF_SMALL_MODEL,
    _stream: bool = False,
) -> str:
    """
    Ollama APIを使用してチャットを行う関数
    Args:
        _messages (list): チャットメッセージのリスト。各メッセージは辞書形式で、"role"と"content"を含む。
        _model (str): 使用するモデルの名前。デフォルトは"gemma3:27b-it-qat"。
    """
    # APIエンドポイント（ローカル）
    url = settings.OLLAMA_URL + "/api/chat"

    # 128000
    # 32,768

    if "gemma3" in _model:
        _num_ctx = 128000
    elif "qwen3" in _model:
        _num_ctx = 32768
    else:
        _num_ctx = 4096

    # リクエストボディ
    payload = {
        "model": _model,
        "messages": _messages,
        "stream": _stream,  # Trueにするとストリームレスポンスになる
        "options": {"num_ctx": _num_ctx},
    }

    # リクエスト送信
    response = requests.post(url, json=payload, timeout=60)

    # 結果出力
    if response.ok:
        return response.json()["message"]["content"]
    else:
        print("Error:", response.status_code, response.text)
        return "Error occurred"


def chatMlx(_messages: List[ChatMessage]) -> str:
    """
    MLX APIを使用してチャットを行う関数
    Args:
        _messages (list): チャットメッセージのリスト。各メッセージは辞書形式で、"role"と"content"を含む。
        _model (str): 使用するモデルの名前。デフォルトは"gemma3:27b-it-qat"。
    """
    # APIエンドポイント（ローカル）
    url = f"{settings.MLX_LLM_SERVER_URL}/v1/chat/completions"
    HEADERS = {"Content-Type": "application/json"}

    # リクエストボディ
    payload = {"messages": _messages}

    # リクエスト送信
    response = requests.post(url, json=payload, headers=HEADERS, timeout=60)

    # 結果出力
    if response.ok:
        return response.json()["choices"][0]["message"]["content"]
    else:
        print("Error:", response.status_code, response.text)
        return "Error occurred"


def extract_knowledge_from_text(_question, _text, _model: str = "gemma3:27b-it-qat"):
    _query = f"""

        # 命令指示書
        あなたは優れたリサーチャーでコンテンツを作成するために収集した情報を整理しています。
        前提条件と制約条件に従いユーザーの興味と収集した情報を元に下記手順で最高の成果物を生成してください。

        1. ユーザーの興味を整理するための質問を出力すること
        2. 1で出力した質問に対する回答を収集した情報から抽出し、成果物フォーマットの「FAQ」に列挙すること。回答不可の場合は「回答不可」とすること。
        3. 収集した情報から最大3つの事実を抽出し、成果物フォーマットの「事実」に列挙すること。可能な限り5W2Hを明らかにし定量的に表現すること。


        # 前提条件
        - 現在の時刻は「{datetime.now()}」です。

        # 制約条件
        - 日本語で出力すること
        - 成果物フォーマットに従うこと

        # ユーザーの興味
        ```
        {_question}
        ```

        # 収集した情報
        ```
        {_text}
        ```

        # 成果物フォーマット
        ```
        ## FAQ:
            - "質問1": "回答1"
            - "質問2": "回答2"
            - "質問3": "回答3"
            ・・・
        ## 事実:
            - "事実1"
            - "事実2"
            ・・・
        ```
    """

    _messages = []
    _messages.append({"role": "user", "content": _query})

    # result = chatMlx(_messages)
    if _model == "mlx-community":
        print("chatMlx")
        result = chatMlx(_messages)
    else:
        print("chatOllama")
        result = chatOllama(_messages, _model)

    print("============================")
    print("extract_knowledge_from_text:")
    print("============================")
    print(result)
    print("============================")
    print("============================")

    return result
