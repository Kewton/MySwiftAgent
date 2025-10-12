def isChatGptAPI(_selected_model):
    # gpt-oss は Ollama のローカルモデルなので除外
    if "gpt-oss" in _selected_model:
        return False
    # OpenAI の公式モデル名のみマッチ
    if "gpt" in _selected_model:
        return True
    return False


def isChatGPT_o(_selected_model):
    if "o1" in _selected_model:
        return True
    elif "o3" in _selected_model:
        return True
    else:
        return False


def isChatGPTImageAPI(_selected_model):
    if "gpt-4o" in _selected_model:
        return True
    elif "o1" in _selected_model:
        return True
    elif "o3" in _selected_model:
        return True
    else:
        return False


def isGemini(_selected_model):
    if "gemini" in _selected_model:
        return True
    else:
        return False


def isClaude(_selected_model):
    if "claude" in _selected_model:
        return True
    else:
        return False
