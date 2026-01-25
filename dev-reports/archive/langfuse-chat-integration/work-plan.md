# 作業計画: llm_service.py へのLangfuse統合

## 概要

**目的**: 要件定義チャット (`llm_service.py`) にLangfuse Observability統合を追加し、LLMトレースを記録可能にする

**背景**:
- `ai_agent_service.py` には既にLangfuse統合が実装済み
- `llm_service.py` はLangfuse統合 (Issue #135) より前に作成されたため、未対応のまま残っていた

## 変更対象ファイル

| ファイル | 変更内容 |
|----------|---------|
| `expertAgent/app/services/conversation/llm_service.py` | Langfuse CallbackHandler統合 |
| `expertAgent/tests/unit/test_llm_service_langfuse.py` | 単体テスト追加 (新規) |

## 実装計画

### Phase 1: llm_service.py の修正

#### 1.1 インポート追加

```python
from app.services.langfuse_service import langfuse_service
```

#### 1.2 関数シグネチャ変更

`stream_requirement_clarification()` と `non_streaming_clarification()` に以下のパラメータを追加:
- `conversation_id: str | None = None` - 会話ID（セッションID相当）
- `user_id: str | None = None` - ユーザーID

#### 1.3 Langfuse CallbackHandler 統合パターン

`ai_agent_service.py` の実装パターンを参考に:

```python
# Langfuse CallbackHandler生成
langfuse_handler = langfuse_service.get_callback_handler(
    trace_name="requirement_clarification",
    user_id=user_id,
    session_id=conversation_id,
    tags=["chat", "requirement_clarification"],
    metadata={
        "model": model_name,
    },
)

# LLM呼び出し時にcallbacksを渡す
config = {}
if langfuse_handler:
    config["callbacks"] = [langfuse_handler]

# astream/ainvoke にconfigを渡す
async for chunk in model.astream(messages, config=config):
    ...

# 処理完了後にフラッシュ
finally:
    if langfuse_handler:
        langfuse_service.flush()
```

### Phase 2: 呼び出し元の更新

`chat_endpoints.py` から `conversation_id` を `llm_service` に渡すよう修正:

```python
# stream_requirement_clarification 呼び出し時
async for event in stream_requirement_clarification(
    user_message=request.user_message,
    previous_messages=request.context.previous_messages,
    current_requirements=RequirementState(**request.context.current_requirements),
    conversation_id=request.conversation_id,  # 追加
):
```

### Phase 3: テスト作成

#### 3.1 単体テスト

- `langfuse_service.get_callback_handler()` が呼び出されることを確認
- `langfuse_service.flush()` が適切に呼び出されることを確認
- Langfuse無効時でも正常動作することを確認

### Phase 4: 動作確認

1. myVaultにLangfuse APIキーが設定されていることを確認
2. expertAgentを再起動
3. http://localhost:8000/create_job で要件定義チャットを実行
4. Langfuse UI (http://localhost:3001) でトレースが登録されていることを確認

## チェックリスト

- [ ] `llm_service.py` にLangfuse統合を実装
- [ ] `chat_endpoints.py` から `conversation_id` を渡すよう修正
- [ ] 単体テスト作成・実行
- [ ] Ruff/MyPy エラーなし
- [ ] 実際にLangfuseにトレースが登録されることを確認

## 参照実装

- `expertAgent/app/services/ai_agent_service.py`: 110-161行 (Langfuse統合パターン)
- `expertAgent/app/services/langfuse_service.py`: Langfuseサービスシングルトン
