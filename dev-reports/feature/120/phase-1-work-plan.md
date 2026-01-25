# Phase 1 作業計画: 自然言語ジョブ作成UI

**Issue**: #120
**Phase**: Phase 1
**作成日**: 2025-01-30
**ブランチ**: feature/issue/120
**担当**: Claude Code

---

## 📋 作業計画概要

### 目的

自然言語チャット対話を通じたジョブ作成機能の基盤実装

### 成果物

- ✅ myAgentDesk: チャットUIコンポーネント（4ファイル）
- ✅ myAgentDesk: expertAgentClient（1ファイル）
- ✅ expertAgent: Chat API（2エンドポイント）
- ✅ expertAgent: 会話管理サービス（1ファイル）
- ✅ expertAgent: プロンプトテンプレート（1ファイル）
- ✅ テストコード（単体 + 結合）

### 工数見積もり

**合計**: 26-28時間

---

## 🗓️ タスク分解

### Step 1: expertAgent バックエンド実装（13-14時間）

#### タスク1.1: プロジェクト基盤準備（1時間）

**実装内容**:
- ✅ 依存関係追加（`sse-starlette`）
- ✅ ディレクトリ構成作成
- ✅ 型定義・スキーマ作成

**作業詳細**:
```bash
cd expertAgent

# 1. 依存関係追加
uv add sse-starlette

# 2. ディレクトリ作成
mkdir -p app/api/v1/chat
mkdir -p app/services/conversation
mkdir -p aiagent/langgraph/jobTaskGeneratorAgents/prompts/requirement_clarification

# 3. 型定義ファイル作成
touch app/schemas/chat.py
```

**成果物**:
- `pyproject.toml` (sse-starlette追加)
- `app/schemas/chat.py` (RequirementState, RequirementChatRequest等)

**完了条件**:
- [ ] `uv sync` が成功する
- [ ] ディレクトリ構成が作成される
- [ ] 型定義がインポート可能

---

#### タスク1.2: 会話状態管理サービス実装（1時間）

**実装内容**:
- ✅ `ConversationStore` クラス実装
- ✅ TTL管理（7日間）
- ✅ 会話履歴の保存・取得

**作業詳細**:
```python
# expertAgent/app/services/conversation/conversation_store.py

from typing import Dict, List
from datetime import datetime, timedelta

class ConversationStore:
    """インメモリ会話ストア"""

    def __init__(self, ttl_days: int = 7):
        self._conversations: Dict[str, Dict] = {}
        self._ttl = timedelta(days=ttl_days)

    def save_message(self, conversation_id: str, role: str, content: str):
        """メッセージを保存"""
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = {
                'messages': [],
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }

        self._conversations[conversation_id]['messages'].append({
            'role': role,
            'content': content,
            'timestamp': datetime.now()
        })
        self._conversations[conversation_id]['updated_at'] = datetime.now()

    def get_conversation(self, conversation_id: str) -> Dict | None:
        """会話履歴を取得"""
        self._cleanup_expired()
        return self._conversations.get(conversation_id)

    def _cleanup_expired(self):
        """期限切れ会話を削除"""
        now = datetime.now()
        expired = [
            cid for cid, conv in self._conversations.items()
            if now - conv['updated_at'] > self._ttl
        ]
        for cid in expired:
            del self._conversations[cid]

# シングルトンインスタンス
conversation_store = ConversationStore()
```

**成果物**:
- `app/services/conversation/conversation_store.py`
- `app/services/conversation/__init__.py`

**完了条件**:
- [ ] `ConversationStore` が正しく動作する
- [ ] 7日後に自動削除される

---

#### タスク1.3: 要件明確化プロンプトテンプレート作成（2時間）

**実装内容**:
- ✅ システムプロンプト定義
- ✅ ユーザープロンプト生成関数
- ✅ `RequirementState` Pydanticモデル

**作業詳細**:
```python
# expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/prompts/requirement_clarification.py

from pydantic import BaseModel, Field
from typing import List, Dict

class RequirementState(BaseModel):
    """要件明確化の状態"""
    data_source: str | None = Field(None, description="データソース")
    process_description: str | None = Field(None, description="処理内容")
    output_format: str | None = Field(None, description="出力形式")
    schedule: str | None = Field(None, description="実行スケジュール")
    completeness: float = Field(0.0, description="明確化率（0.0-1.0）")

REQUIREMENT_CLARIFICATION_SYSTEM_PROMPT = """
あなたはドメインエキスパート向けのジョブ作成アシスタントです。

## あなたの役割
1. ユーザーの曖昧な要求を段階的に明確化する
2. 技術的な詳細ではなく、ビジネス上の目的（What）に焦点を当てる
3. 必要最小限の情報を収集し、実装方法（How）は自動で決定する

## 明確化すべき要件
- データソース: どのデータを使うか
- 処理内容: 何をしたいか（分析、レポート生成、通知等）
- 出力形式: どのような形式で結果が欲しいか
- スケジュール: いつ実行するか（オンデマンド、定期実行）

## 対話のガイドライン
- 一度に1つの質問をする（複数質問は避ける）
- 専門用語を避け、わかりやすい言葉を使う
- ユーザーが迷っている場合は選択肢を提示する
- 要件が十分に明確になったら、ジョブ作成を提案する

## completeness計算ルール
- data_source明確: +0.25
- process_description明確: +0.35（最重要）
- output_format明確: +0.25
- schedule明確: +0.15
- 合計0.8以上でジョブ作成可能
"""

def create_requirement_clarification_prompt(
    user_message: str,
    previous_messages: List[Dict],
    current_requirements: RequirementState
) -> str:
    """要件明確化プロンプトを生成"""

    # 対話履歴をフォーマット
    history = "\n".join([
        f"{msg['role']}: {msg['content']}"
        for msg in previous_messages[-10:]  # 直近10メッセージのみ
    ])

    # 現在の要件状態をフォーマット
    requirements_status = f"""
現在の要件明確化状態:
- データソース: {current_requirements.data_source or '未定'}
- 処理内容: {current_requirements.process_description or '未定'}
- 出力形式: {current_requirements.output_format or '未定'}
- スケジュール: {current_requirements.schedule or '未定'}
- 明確化率: {int(current_requirements.completeness * 100)}%
"""

    return f"""
{requirements_status}

## 対話履歴
{history}

## ユーザーの最新メッセージ
user: {user_message}

## あなたのタスク
1. ユーザーの最新メッセージから要件を抽出
2. 不明な点があれば1つ質問を返す
3. 要件が十分明確（80%以上）なら、ジョブ作成を提案
4. 更新された RequirementState を返す

応答してください。
"""
```

**成果物**:
- `aiagent/langgraph/jobTaskGeneratorAgents/prompts/requirement_clarification.py`

**完了条件**:
- [ ] プロンプトが生成される
- [ ] `RequirementState` が正しく動作する

---

#### タスク1.4: LLMストリーミング統合（2時間）

**実装内容**:
- ✅ `stream_requirement_clarification` 関数実装
- ✅ LLM APIストリーミング呼び出し
- ✅ `RequirementState` 抽出ロジック

**作業詳細**:
```python
# expertAgent/app/services/conversation/llm_service.py

from typing import AsyncGenerator, Dict
from aiagent.langgraph.jobTaskGeneratorAgents.prompts.requirement_clarification import (
    RequirementState,
    REQUIREMENT_CLARIFICATION_SYSTEM_PROMPT,
    create_requirement_clarification_prompt
)
from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import create_llm

async def stream_requirement_clarification(
    user_message: str,
    previous_messages: List[Dict],
    current_requirements: RequirementState
) -> AsyncGenerator[Dict, None]:
    """要件明確化チャット（ストリーミング）"""

    # プロンプト生成
    user_prompt = create_requirement_clarification_prompt(
        user_message,
        previous_messages,
        current_requirements
    )

    messages = [
        {"role": "system", "content": REQUIREMENT_CLARIFICATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    # LLMストリーミング呼び出し
    llm = create_llm(stream=True)
    full_response = ""

    async for chunk in llm.astream(messages):
        if hasattr(chunk, 'content'):
            content = chunk.content
            full_response += content
            yield {
                "type": "message",
                "data": {"content": content}
            }

    # 完全な応答から RequirementState を抽出
    updated_requirements = extract_requirement_state(full_response, current_requirements)

    yield {
        "type": "requirement_update",
        "data": {"requirements": updated_requirements.model_dump()}
    }

    # 要件が80%以上明確化されたら通知
    if updated_requirements.completeness >= 0.8:
        yield {
            "type": "requirements_ready",
            "data": {}
        }

def extract_requirement_state(llm_response: str, current: RequirementState) -> RequirementState:
    """LLM応答から要件状態を抽出"""

    # TODO: より高度な抽出ロジック（正規表現、LLM構造化出力等）
    # Phase 1では簡易実装

    updated = current.model_copy()

    # キーワードベースの簡易抽出
    if "CSV" in llm_response or "Excel" in llm_response or "データベース" in llm_response:
        if not updated.data_source:
            if "CSV" in llm_response:
                updated.data_source = "CSVファイル"
            elif "Excel" in llm_response:
                updated.data_source = "Excelファイル"
            elif "データベース" in llm_response:
                updated.data_source = "データベース"

    # completeness再計算
    updated.completeness = calculate_completeness(updated)

    return updated

def calculate_completeness(state: RequirementState) -> float:
    """明確化率を計算"""
    score = 0.0
    if state.data_source:
        score += 0.25
    if state.process_description:
        score += 0.35
    if state.output_format:
        score += 0.25
    if state.schedule:
        score += 0.15
    return score
```

**成果物**:
- `app/services/conversation/llm_service.py`

**完了条件**:
- [ ] LLMストリーミングが動作する
- [ ] `RequirementState` が抽出される

---

#### タスク1.5: Chat API エンドポイント実装（3-4時間）

**実装内容**:
- ✅ `/chat/requirement-definition` エンドポイント（SSE）
- ✅ `/chat/create-job` エンドポイント
- ✅ エラーハンドリング

**作業詳細**:
```python
# expertAgent/app/api/v1/chat_endpoints.py

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from typing import List, Dict
import json

from app.services.conversation.conversation_store import conversation_store
from app.services.conversation.llm_service import stream_requirement_clarification
from app.schemas.chat import RequirementChatRequest, CreateJobRequest

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/requirement-definition")
async def requirement_definition(request: RequirementChatRequest):
    """要件明確化チャット（SSE）"""

    async def event_generator():
        try:
            # 会話履歴を保存
            conversation_store.save_message(
                request.conversation_id,
                'user',
                request.user_message
            )

            # LLMストリーミング呼び出し
            from aiagent.langgraph.jobTaskGeneratorAgents.prompts.requirement_clarification import RequirementState

            current_requirements = RequirementState(**request.context['current_requirements'])

            full_response = ""
            async for chunk in stream_requirement_clarification(
                user_message=request.user_message,
                previous_messages=request.context['previous_messages'],
                current_requirements=current_requirements
            ):
                if chunk['type'] == 'message':
                    full_response += chunk['data']['content']

                yield {
                    "event": "message",
                    "data": json.dumps(chunk, ensure_ascii=False)
                }

            # 応答を保存
            conversation_store.save_message(
                request.conversation_id,
                'assistant',
                full_response
            )

            yield {
                "event": "message",
                "data": json.dumps({"type": "done"}, ensure_ascii=False)
            }

        except Exception as e:
            logger.error(f"Error in requirement_definition: {e}")
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "error",
                    "data": {"message": "エラーが発生しました。もう一度お試しください。"}
                }, ensure_ascii=False)
            }

    return EventSourceResponse(event_generator())

@router.post("/create-job")
async def create_job(request: CreateJobRequest):
    """要件からジョブ作成"""

    try:
        # 要件を Job Generator リクエストに変換
        job_generator_request = convert_requirements_to_job_request(request.requirements)

        # 既存 Job Generator API呼び出し
        from app.api.v1.job_generator_endpoints import job_generator_endpoint

        result = await job_generator_endpoint(job_generator_request)

        return {
            "job_id": result["job_id"],
            "job_master_id": result["job_master_id"],
            "status": "success",
            "message": "ジョブを作成しました"
        }

    except Exception as e:
        logger.error(f"Error in create_job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def convert_requirements_to_job_request(requirements: Dict) -> Dict:
    """要件を Job Generator リクエストに変換"""

    user_requirement = f"""
## データソース
{requirements.get('data_source', '未指定')}

## 処理内容
{requirements.get('process_description', '未指定')}

## 出力形式
{requirements.get('output_format', '未指定')}

## スケジュール
{requirements.get('schedule', 'オンデマンド')}
"""

    return {
        "user_requirement": user_requirement,
        "available_capabilities": []
    }
```

**成果物**:
- `app/api/v1/chat_endpoints.py`
- `app/schemas/chat.py` (Request/Responseスキーマ)

**完了条件**:
- [ ] エンドポイントが動作する
- [ ] SSEでストリーミング応答が返る
- [ ] ジョブ作成が成功する

---

#### タスク1.6: expertAgent テスト実装（4時間）

**実装内容**:
- ✅ 単体テスト: `ConversationStore`
- ✅ 単体テスト: プロンプト生成
- ✅ 結合テスト: Chat endpoints

**作業詳細**:
```python
# expertAgent/tests/unit/test_conversation_store.py

import pytest
from datetime import datetime, timedelta
from app.services.conversation.conversation_store import ConversationStore

def test_save_and_retrieve_message():
    store = ConversationStore(ttl_days=7)

    store.save_message('conv_001', 'user', 'Hello')
    conv = store.get_conversation('conv_001')

    assert conv is not None
    assert len(conv['messages']) == 1
    assert conv['messages'][0]['role'] == 'user'
    assert conv['messages'][0]['content'] == 'Hello'

def test_ttl_cleanup():
    store = ConversationStore(ttl_days=7)

    # 8日前の会話を作成
    store.save_message('conv_old', 'user', 'Old message')
    store._conversations['conv_old']['updated_at'] = datetime.now() - timedelta(days=8)

    # 新しい会話を作成
    store.save_message('conv_new', 'user', 'New message')

    # cleanup実行
    store._cleanup_expired()

    assert store.get_conversation('conv_old') is None
    assert store.get_conversation('conv_new') is not None

# expertAgent/tests/integration/test_chat_endpoints.py

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_requirement_definition_sse(client: AsyncClient):
    request = {
        "conversation_id": "test_conv_001",
        "user_message": "売上データを分析したい",
        "context": {
            "previous_messages": [],
            "current_requirements": {
                "data_source": None,
                "process_description": None,
                "output_format": None,
                "schedule": None,
                "completeness": 0.0
            }
        }
    }

    async with client.stream(
        "POST",
        "/aiagent-api/v1/chat/requirement-definition",
        json=request
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"

        events = []
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

        assert len(events) > 0
        assert any(e['type'] == 'message' for e in events)
```

**成果物**:
- `tests/unit/test_conversation_store.py`
- `tests/unit/test_requirement_clarification.py`
- `tests/integration/test_chat_endpoints.py`

**完了条件**:
- [ ] 全テストが合格する
- [ ] カバレッジ90%以上（単体）
- [ ] カバレッジ80%以上（結合）

---

### Step 2: myAgentDesk フロントエンド実装（13-14時間）

#### タスク2.1: プロジェクト基盤準備（1時間）

**実装内容**:
- ✅ 依存関係追加（`@microsoft/fetch-event-source`）
- ✅ 型定義作成
- ✅ ディレクトリ構成作成

**作業詳細**:
```bash
cd myAgentDesk

# 1. 依存関係追加
npm install @microsoft/fetch-event-source

# 2. ディレクトリ作成
mkdir -p src/lib/types
mkdir -p src/lib/services
mkdir -p src/lib/components/chat
mkdir -p src/routes/jobs/create

# 3. 型定義ファイル作成
touch src/lib/types/chat.ts
```

**成果物**:
- `package.json` (fetch-event-source追加)
- `src/lib/types/chat.ts`

**完了条件**:
- [ ] `npm install` が成功する
- [ ] TypeScript型定義がインポート可能

---

#### タスク2.2: TypeScript型定義作成（1時間）

**実装内容**:
- ✅ `Message`, `RequirementState`, `StreamEvent` 型定義

**作業詳細**:
```typescript
// src/lib/types/chat.ts

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface RequirementState {
  data_source: string | null;
  process_description: string | null;
  output_format: string | null;
  schedule: string | null;
  completeness: number;  // 0.0 - 1.0
}

export interface RequirementChatRequest {
  conversation_id: string;
  user_message: string;
  context: {
    previous_messages: Message[];
    current_requirements: RequirementState;
  };
}

export interface StreamEvent {
  type: 'message' | 'requirement_update' | 'requirements_ready' | 'done' | 'error';
  data?: any;
}

export interface CreateJobRequest {
  conversation_id: string;
  requirements: RequirementState;
}

export interface CreateJobResponse {
  job_id: string;
  job_master_id: string;
  status: string;
  message: string;
}
```

**成果物**:
- `src/lib/types/chat.ts`

**完了条件**:
- [ ] 型定義がコンパイルエラーなし

---

#### タスク2.3: expertAgentClient実装（3-4時間）

**実装内容**:
- ✅ SSEクライアント実装
- ✅ ストリーミングメッセージハンドリング
- ✅ エラーハンドリング・リトライ

**作業詳細**:
```typescript
// src/lib/services/expertAgentClient.ts

import { fetchEventSource } from '@microsoft/fetch-event-source';
import type {
  Message,
  RequirementState,
  RequirementChatRequest,
  StreamEvent,
  CreateJobRequest,
  CreateJobResponse
} from '$lib/types/chat';

class FatalError extends Error {}

class ExpertAgentClient {
  private baseUrl: string;
  private timeout: number;

  constructor(baseUrl: string = 'http://localhost:8104', timeout: number = 60000) {
    this.baseUrl = baseUrl;
    this.timeout = timeout;
  }

  async streamRequirementChat(params: {
    conversationId: string;
    userMessage: string;
    previousMessages: Message[];
    currentRequirements: RequirementState;
    onMessage: (chunk: string) => void;
    onRequirementUpdate: (state: RequirementState) => void;
  }): Promise<void> {
    const request: RequirementChatRequest = {
      conversation_id: params.conversationId,
      user_message: params.userMessage,
      context: {
        previous_messages: params.previousMessages,
        current_requirements: params.currentRequirements
      }
    };

    let retryCount = 0;
    const maxRetries = 3;

    const timeoutId = setTimeout(() => {
      throw new Error('Stream timeout');
    }, this.timeout);

    try {
      while (retryCount < maxRetries) {
        try {
          await fetchEventSource(`${this.baseUrl}/aiagent-api/v1/chat/requirement-definition`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(request),

            onopen: async (response) => {
              if (response.ok) {
                return;
              }
              if (response.status >= 500) {
                throw new Error('Server error');
              } else {
                throw new FatalError(`Client error: ${response.status}`);
              }
            },

            onmessage: (event) => {
              if (event.data === '[DONE]') {
                return;
              }

              try {
                const streamEvent: StreamEvent = JSON.parse(event.data);

                switch (streamEvent.type) {
                  case 'message':
                    params.onMessage(streamEvent.data.content);
                    break;

                  case 'requirement_update':
                    params.onRequirementUpdate(streamEvent.data.requirements);
                    break;

                  case 'requirements_ready':
                    console.log('Requirements ready for job creation');
                    break;

                  case 'error':
                    throw new Error(streamEvent.data.message);
                }
              } catch (error) {
                console.error('Failed to parse SSE event:', error);
              }
            },

            onerror: (error) => {
              retryCount++;
              if (retryCount >= maxRetries) {
                throw error;
              }
              // 指数バックオフ
              return Math.min(1000 * Math.pow(2, retryCount), 10000);
            }
          });
          break;  // 成功したらループ終了
        } catch (error) {
          if (error instanceof FatalError) {
            throw error;
          }
          if (retryCount >= maxRetries) {
            throw error;
          }
        }
      }
    } finally {
      clearTimeout(timeoutId);
    }
  }

  async createJobFromRequirements(params: CreateJobRequest): Promise<CreateJobResponse> {
    const response = await fetch(`${this.baseUrl}/aiagent-api/v1/chat/create-job`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params)
    });

    if (!response.ok) {
      throw new Error(`Failed to create job: ${response.status}`);
    }

    return await response.json();
  }
}

export const expertAgentClient = new ExpertAgentClient();
```

**成果物**:
- `src/lib/services/expertAgentClient.ts`

**完了条件**:
- [ ] SSE接続が成功する
- [ ] ストリーミングメッセージが受信できる
- [ ] エラー時にリトライする

---

#### タスク2.4: Svelteコンポーネント実装（5時間）

**4つのコンポーネントを実装**:

##### 2.4.1 ChatInput.svelte（1時間）

```typescript
<script lang="ts">
  export let onSend: (content: string) => void;
  export let disabled: boolean = false;

  let inputValue = '';

  function handleSubmit() {
    if (inputValue.trim() && !disabled) {
      onSend(inputValue.trim());
      inputValue = '';
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }
</script>

<div class="p-4 border-t border-gray-200 dark:border-gray-700">
  <div class="flex gap-2">
    <textarea
      bind:value={inputValue}
      on:keydown={handleKeydown}
      placeholder="メッセージを入力... (Shift+Enterで改行)"
      class="flex-1 px-4 py-2 border rounded-lg resize-none"
      rows="3"
      {disabled}
    />
    <button
      on:click={handleSubmit}
      disabled={disabled || !inputValue.trim()}
      class="px-6 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50"
    >
      送信
    </button>
  </div>
</div>
```

##### 2.4.2 ChatMessageList.svelte（1時間）

```typescript
<script lang="ts">
  import ChatBubble from '$lib/components/ChatBubble.svelte';
  import type { Message } from '$lib/types/chat';

  export let messages: Message[];
  export let isStreaming: boolean;

  let messagesContainer: HTMLDivElement;

  $: if (messages.length > 0) {
    setTimeout(() => {
      messagesContainer?.scrollTo({
        top: messagesContainer.scrollHeight,
        behavior: 'smooth'
      });
    }, 100);
  }
</script>

<div bind:this={messagesContainer} class="flex-1 overflow-y-auto p-4 space-y-4">
  {#each messages as message}
    <ChatBubble
      role={message.role}
      message={message.content}
      timestamp={message.timestamp.toLocaleTimeString()}
    />
  {/each}

  {#if isStreaming}
    <div class="flex items-center gap-2 text-gray-400">
      <div class="animate-pulse">💭</div>
      <span>AI is thinking...</span>
    </div>
  {/if}
</div>
```

##### 2.4.3 RequirementPanel.svelte（2時間）

```typescript
<script lang="ts">
  import type { RequirementState } from '$lib/types/chat';

  export let requirementState: RequirementState;
  export let onCreateJob: () => void;
  export let createDisabled: boolean;

  $: completenessPercent = Math.round(requirementState.completeness * 100);
  $: requiredFields = [
    { label: 'データソース', value: requirementState.data_source },
    { label: '処理内容', value: requirementState.process_description },
    { label: '出力形式', value: requirementState.output_format },
    { label: 'スケジュール', value: requirementState.schedule }
  ];
</script>

<div class="p-4 border-l border-gray-200 dark:border-gray-700 overflow-y-auto">
  <h2 class="text-xl font-bold mb-4">📋 要件サマリー</h2>

  <div class="space-y-4 mb-6">
    {#each requiredFields as field}
      <div>
        <div class="flex items-center gap-2 mb-1">
          {#if field.value}
            <span class="text-green-500">✓</span>
          {:else}
            <span class="text-gray-400">○</span>
          {/if}
          <span class="font-semibold">{field.label}</span>
        </div>
        <p class="ml-6 text-sm text-gray-600 dark:text-gray-400">
          {field.value || '未定'}
        </p>
      </div>
    {/each}
  </div>

  <div class="mb-6">
    <div class="flex items-center justify-between mb-2">
      <span class="text-sm font-semibold">🎯 明確化率</span>
      <span class="text-sm">{completenessPercent}%</span>
    </div>
    <div class="w-full bg-gray-200 rounded-full h-2">
      <div
        class="bg-primary-500 h-2 rounded-full transition-all"
        style="width: {completenessPercent}%"
      />
    </div>
  </div>

  <button
    on:click={onCreateJob}
    disabled={createDisabled}
    class="w-full py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
  >
    {#if createDisabled}
      要件を明確にしてください ({completenessPercent}% / 80%必要)
    {:else}
      ジョブを作成
    {/if}
  </button>
</div>
```

##### 2.4.4 JobCreationChat.svelte（1時間）

```typescript
<script lang="ts">
  import { goto } from '$app/navigation';
  import ChatMessageList from '$lib/components/chat/ChatMessageList.svelte';
  import ChatInput from '$lib/components/chat/ChatInput.svelte';
  import RequirementPanel from '$lib/components/chat/RequirementPanel.svelte';
  import { expertAgentClient } from '$lib/services/expertAgentClient';
  import type { Message, RequirementState } from '$lib/types/chat';

  let messages: Message[] = [];
  let requirementState: RequirementState = {
    data_source: null,
    process_description: null,
    output_format: null,
    schedule: null,
    completeness: 0
  };
  let isStreaming = false;
  let conversationId = crypto.randomUUID();

  async function handleSendMessage(content: string) {
    messages = [...messages, { role: 'user', content, timestamp: new Date() }];

    isStreaming = true;
    let assistantMessage: Message = { role: 'assistant', content: '', timestamp: new Date() };
    messages = [...messages, assistantMessage];

    try {
      await expertAgentClient.streamRequirementChat({
        conversationId,
        userMessage: content,
        previousMessages: messages.slice(0, -1),
        currentRequirements: requirementState,
        onMessage: (chunk) => {
          assistantMessage.content += chunk;
          messages = [...messages];
        },
        onRequirementUpdate: (newState) => {
          requirementState = newState;
        }
      });
    } catch (error) {
      console.error('Chat error:', error);
      assistantMessage.content = 'エラーが発生しました。もう一度お試しください。';
      messages = [...messages];
    } finally {
      isStreaming = false;
    }
  }

  async function handleCreateJob() {
    try {
      const result = await expertAgentClient.createJobFromRequirements({
        conversationId,
        requirements: requirementState
      });
      goto(`/jobs/${result.job_id}`);
    } catch (error) {
      console.error('Job creation error:', error);
      alert('ジョブの作成に失敗しました');
    }
  }
</script>

<div class="grid grid-cols-[1fr_400px] gap-4 h-screen">
  <div class="flex flex-col">
    <ChatMessageList {messages} {isStreaming} />
    <ChatInput onSend={handleSendMessage} disabled={isStreaming} />
  </div>
  <RequirementPanel
    {requirementState}
    onCreateJob={handleCreateJob}
    createDisabled={requirementState.completeness < 0.8}
  />
</div>
```

**成果物**:
- `src/lib/components/chat/ChatInput.svelte`
- `src/lib/components/chat/ChatMessageList.svelte`
- `src/lib/components/chat/RequirementPanel.svelte`
- `src/routes/jobs/create/+page.svelte` (JobCreationChat)

**完了条件**:
- [ ] 全コンポーネントがビルドエラーなし
- [ ] チャットUIが正しく表示される

---

#### タスク2.5: myAgentDesk テスト実装（3時間）

**実装内容**:
- ✅ expertAgentClient単体テスト
- ✅ コンポーネント単体テスト（4ファイル）

**作業詳細**:
```typescript
// src/lib/services/expertAgentClient.test.ts

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { expertAgentClient } from './expertAgentClient';

describe('expertAgentClient', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should handle streaming messages', async () => {
    const mockOnMessage = vi.fn();
    const mockOnRequirementUpdate = vi.fn();

    // fetchEventSource をモック
    // ... (モック実装)

    await expertAgentClient.streamRequirementChat({
      conversationId: 'test_123',
      userMessage: 'Test message',
      previousMessages: [],
      currentRequirements: {
        data_source: null,
        process_description: null,
        output_format: null,
        schedule: null,
        completeness: 0
      },
      onMessage: mockOnMessage,
      onRequirementUpdate: mockOnRequirementUpdate
    });

    expect(mockOnMessage).toHaveBeenCalled();
  });

  it('should retry on server error', async () => {
    // リトライロジックのテスト
  });

  it('should timeout after 60 seconds', async () => {
    // タイムアウトテスト
  });
});

// src/lib/components/chat/ChatInput.test.ts

import { render, fireEvent } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import ChatInput from './ChatInput.svelte';

describe('ChatInput', () => {
  it('should call onSend when submit button clicked', async () => {
    const mockOnSend = vi.fn();
    const { getByRole, getByPlaceholderText } = render(ChatInput, {
      props: { onSend: mockOnSend, disabled: false }
    });

    const textarea = getByPlaceholderText('メッセージを入力...');
    await fireEvent.input(textarea, { target: { value: 'Test message' } });

    const button = getByRole('button', { name: '送信' });
    await fireEvent.click(button);

    expect(mockOnSend).toHaveBeenCalledWith('Test message');
  });

  it('should submit on Enter key', async () => {
    const mockOnSend = vi.fn();
    const { getByPlaceholderText } = render(ChatInput, {
      props: { onSend: mockOnSend, disabled: false }
    });

    const textarea = getByPlaceholderText('メッセージを入力...');
    await fireEvent.input(textarea, { target: { value: 'Test' } });
    await fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });

    expect(mockOnSend).toHaveBeenCalledWith('Test');
  });

  it('should be disabled when disabled prop is true', () => {
    const { getByRole } = render(ChatInput, {
      props: { onSend: vi.fn(), disabled: true }
    });

    const button = getByRole('button', { name: '送信' });
    expect(button).toBeDisabled();
  });
});

// RequirementPanel, ChatMessageList も同様にテスト実装
```

**成果物**:
- `src/lib/services/expertAgentClient.test.ts`
- `src/lib/components/chat/ChatInput.test.ts`
- `src/lib/components/chat/RequirementPanel.test.ts`
- `src/lib/components/chat/ChatMessageList.test.ts`

**完了条件**:
- [ ] 全テストが合格する
- [ ] カバレッジ80%以上（expertAgentClient）
- [ ] カバレッジ70%以上（コンポーネント）

---

## 🧪 統合テスト・E2Eテスト（手動）

### E2Eテストシナリオ（1時間）

**シナリオ1: 基本フロー**

1. ユーザーが `/jobs/create` にアクセス
2. 「売上データを分析したい」と入力
3. AIが「どのような形式の売上データですか？」と質問
4. ユーザーが「CSVファイルです」と回答
5. AIが「どのような分析をしたいですか？」と質問
6. ユーザーが「月別の売上推移を見たい」と回答
7. AIが「出力形式は？」と質問
8. ユーザーが「Excelレポート」と回答
9. 要件パネルが更新される（明確化率80%以上）
10. 「ジョブを作成」ボタンが有効化
11. ボタンをクリック
12. ジョブ詳細ページへ遷移

**確認項目**:
- [ ] ストリーミング応答がリアルタイム表示される
- [ ] 要件パネルが各応答で更新される
- [ ] 明確化率が正しく計算される
- [ ] 80%到達でボタンが有効化される
- [ ] ジョブ作成が成功する

**シナリオ2: エラーハンドリング**

1. expertAgentを停止
2. メッセージを送信
3. リトライが3回実行される
4. エラーメッセージが表示される

**確認項目**:
- [ ] リトライが実行される
- [ ] ユーザーフレンドリーなエラーメッセージ

---

## 📊 進捗管理

### Phase 1 チェックリスト

**expertAgent (Backend)**:
- [ ] タスク1.1: プロジェクト基盤準備（1h）
- [ ] タスク1.2: 会話状態管理サービス（1h）
- [ ] タスク1.3: プロンプトテンプレート（2h）
- [ ] タスク1.4: LLMストリーミング統合（2h）
- [ ] タスク1.5: Chat API エンドポイント（3-4h）
- [ ] タスク1.6: expertAgent テスト（4h）

**myAgentDesk (Frontend)**:
- [ ] タスク2.1: プロジェクト基盤準備（1h）
- [ ] タスク2.2: TypeScript型定義（1h）
- [ ] タスク2.3: expertAgentClient（3-4h）
- [ ] タスク2.4: Svelteコンポーネント（5h）
- [ ] タスク2.5: myAgentDesk テスト（3h）

**統合テスト**:
- [ ] E2Eテスト（手動）（1h）

### 完了条件

**機能要件**:
- [ ] チャット対話でジョブ要件を明確化できる
- [ ] 要件が80%以上明確化されたらジョブを作成できる
- [ ] ストリーミング応答がリアルタイム表示される
- [ ] エラー時に適切にリトライする

**品質要件**:
- [ ] expertAgent単体テスト: カバレッジ90%以上
- [ ] expertAgent結合テスト: カバレッジ80%以上
- [ ] myAgentDesk単体テスト: カバレッジ80%以上（Client）、70%以上（Component）
- [ ] Ruff linting: 0 errors
- [ ] ESLint: 0 errors
- [ ] TypeScript type checking: 0 errors
- [ ] pre-push-check-all.sh: 全チェック合格

**ドキュメント**:
- [ ] phase-1-progress.md 作成
- [ ] 実装時の技術的決定事項を記録

---

## 🚨 リスクと対策

### リスク1: LLMストリーミングの実装難易度

**対策**: タスク1.4で十分な時間（2時間）を確保、必要に応じて非ストリーミングフォールバック実装

### リスク2: SSE実装の複雑さ

**対策**: タスク2.3で段階的に実装（基本接続 → リトライ → タイムアウト）

### リスク3: 要件抽出精度の低さ

**対策**: Phase 1では簡易実装（キーワードマッチング）、Phase 2以降で高度化

---

## 📝 レビュー観点

- [ ] **タスク分解**: 各タスクは1-4時間で完了可能か
- [ ] **依存関係**: タスクの順序は適切か
- [ ] **工数見積もり**: 26-28時間で完了可能か
- [ ] **完了条件**: 明確で測定可能か
- [ ] **リスク対策**: 十分か

---

**レビューをお願いします。修正・追加要望があればお知らせください。**
