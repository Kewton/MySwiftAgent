# Issue #152: 要件定義エージェントMLOps導入 - 設計方針書

## 📋 ドキュメント情報

**作成日**: 2025-11-11
**更新日**: 2025-11-11
**対象Issue**: #152
**対象プロジェクト**: expertAgent
**優先度**: Medium (feature)
**採用UIパターン**: パターンD（革新的・実験的）

---

## 🎯 設計方針サマリー

本ドキュメントは、Issue #152「要件定義エージェントへのMLOps導入」の実装設計方針を定義します。

### 設計の基本方針

1. **段階的実装**: Phase 1（基盤強化）→ Phase 2（可視化・管理）→ Phase 3（ABテスト）の3段階で実装
2. **既存基盤の活用**: Langfuse統合（Issue #113）、LLM基盤、会話履歴管理を最大限活用
3. **非破壊的拡張**: 既存APIとの互換性を保ちながら、オプション機能として追加
4. **UI/UX優先**: パターンD（革新的・実験的）を採用し、AIアシスト・リアルタイム性を重視
5. **テスタビリティ**: 全機能で単体テストカバレッジ90%以上、結合テスト50%以上を確保

---

## 🏗️ システムアーキテクチャ

### 全体構成図

```
┌─────────────────────────────────────────────────────────────────────┐
│                         myAgentDesk (SvelteKit)                      │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Pattern D UI (革新的・実験的)                               │   │
│  │                                                                │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │   │
│  │  │ AI候補選択   │  │ スマート     │  │ リアルタイム │      │   │
│  │  │ (FR-1)       │  │ フィードバック│  │ ダッシュボード│      │   │
│  │  │              │  │ (FR-2)       │  │ (FR-3)       │      │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │   │
│  │                                                                │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │   │
│  │  │ 診断情報     │  │ プロンプト   │  │ ABテスト     │      │   │
│  │  │ (FR-4)       │  │ 管理 (FR-5)  │  │ (FR-6)       │      │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                   ↓ ↑ (HTTP/SSE)
┌─────────────────────────────────────────────────────────────────────┐
│                         expertAgent (FastAPI)                        │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Chat API (chat_endpoints.py)                                │   │
│  │                                                                │   │
│  │  POST /v1/chat/requirement-definition (SSE) ← 拡張           │   │
│  │  ├─ enable_multi_candidate: bool (新規パラメータ)           │   │
│  │  ├─ prompt_version: Optional[str] (新規パラメータ)          │   │
│  │  └─ ai_recommendation: bool (新規パラメータ)                │   │
│  │                                                                │   │
│  │  POST /v1/chat/feedback (新規エンドポイント)                │   │
│  │  └─ conversation_id → Langfuse score                         │   │
│  │                                                                │   │
│  │  GET /v1/chat/diagnostics/{conversation_id} (新規)           │   │
│  │  └─ Langfuse trace + conversation_store                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Observability API (observability_endpoints.py) ← 拡張      │   │
│  │                                                                │   │
│  │  GET /v1/observability/requirement-definition-metrics (新規)│   │
│  │  └─ Langfuse データ + conversation_store 統計               │   │
│  │                                                                │   │
│  │  GET /v1/observability/requirement-definition-ab-test (新規)│   │
│  │  └─ 統計検定（t検定）+ バージョン比較                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Conversation Services (拡張)                                │   │
│  │                                                                │   │
│  │  conversation_store.py                                        │   │
│  │  ├─ save_trace_id(conversation_id, trace_id) (新規)         │   │
│  │  ├─ get_trace_id(conversation_id) (新規)                    │   │
│  │  ├─ save_prompt_version(conversation_id, version) (新規)    │   │
│  │  └─ get_statistics(days: int) (新規)                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Prompt Management (新規)                                    │   │
│  │                                                                │   │
│  │  prompts/templates/requirement_clarification/                │   │
│  │  ├── v1/                                                      │   │
│  │  │   ├── system_prompt.yaml                                  │   │
│  │  │   ├── extraction_prompt.yaml                              │   │
│  │  │   └── multi_candidate_prompt.yaml                         │   │
│  │  ├── v2/ (ABテスト用)                                        │   │
│  │  │   └── ...                                                  │   │
│  │  └── loader.py (プロンプトローダー)                         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  AI Recommendation Service (新規)                            │   │
│  │                                                                │   │
│  │  ai_recommendation.py                                         │   │
│  │  ├─ analyze_user_message(message: str) → CandidateRec       │   │
│  │  └─ calculate_confidence(factors: dict) → float             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  AB Test Service (新規)                                      │   │
│  │                                                                │   │
│  │  ab_test.py                                                   │   │
│  │  ├─ assign_version(conversation_id) → str (v1/v2)           │   │
│  │  ├─ collect_metrics(version: str, days: int) → dict         │   │
│  │  └─ statistical_test(v1_data, v2_data) → dict               │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                   ↓ ↑ (API)
┌─────────────────────────────────────────────────────────────────────┐
│                       Langfuse (Self-hosted)                         │
│                                                                       │
│  ・Trace データ管理（プロンプト、LLMレスポンス、メタデータ）       │
│  ・Score データ管理（4種類のフィードバックスコア）                 │
│  ・Tags（prompt_version, ai_recommendation など）                   │
│  ・Web UI（トレース閲覧）                                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📐 詳細設計

### Phase 1: 基盤強化（優先度 High）

#### 1.1 診断情報取得機能（FR-4）

**目的**: conversation_id から プロンプト・LLMレスポンス・トークン使用量などの診断情報を取得

**新規エンドポイント**:
```python
GET /v1/chat/diagnostics/{conversation_id}
```

**レスポンススキーマ**:
```python
class DiagnosticInfo(BaseModel):
    conversation_id: str
    trace_id: str
    langfuse_trace_url: str
    system_prompt: str
    turns: List[DiagnosticTurn]
    total_input_tokens: int
    total_output_tokens: int
    total_execution_time_ms: float
    error: Optional[str] = None

class DiagnosticTurn(BaseModel):
    turn_number: int
    timestamp: str
    user_message: str
    llm_response: str
    extracted_state: RequirementState
    model: str
    input_tokens: int
    output_tokens: int
    execution_time_ms: float
    temperature: float
```

**実装方針**:
1. `stream_requirement_clarification()` で Langfuse トレーシングを開始
2. `conversation_store.save_trace_id(conversation_id, trace_id)` でマッピング保存
3. 各ターンのメタデータを `conversation_store` に保存
4. `GET /chat/diagnostics/{conversation_id}` で Langfuse API + conversation_store を統合して返却

---

#### 1.2 フィードバック機能（FR-2）

**目的**: 要件定義API固有のスコアタイプでフィードバックを投稿

**新規エンドポイント**:
```python
POST /v1/chat/feedback
```

**リクエストスキーマ**:
```python
class RequirementFeedbackRequest(BaseModel):
    conversation_id: str
    scores: RequirementScores
    comment: Optional[str] = None

class RequirementScores(BaseModel):
    requirement_clarity: int = Field(ge=1, le=5, description="要件明確化の分かりやすさ")
    hypothesis_accuracy: int = Field(ge=1, le=5, description="仮説の精度")
    response_naturalness: int = Field(ge=1, le=5, description="応答の自然さ")
    overall_satisfaction: int = Field(ge=1, le=5, description="総合満足度")
```

**レスポンススキーマ**:
```python
class RequirementFeedbackResponse(BaseModel):
    status: str  # "success" or "error"
    trace_id: str
    scores_submitted: List[str]  # ["requirement_clarity", "hypothesis_accuracy", ...]
```

**実装方針**:
1. `conversation_store.get_trace_id(conversation_id)` で trace_id を取得
2. 各スコアタイプごとに `POST /observability/scores` を呼び出し
3. Langfuse に4つのスコアを個別に投稿
4. レスポンスで投稿結果を返却

---

#### 1.3 複数候補提示機能（FR-1）

**目的**: 初回メッセージに対し、2つの異なる要件解釈パターンを提示

**拡張パラメータ**:
```python
class RequirementChatRequest(BaseModel):
    conversation_id: str
    user_message: str
    context: RequirementContext
    enable_multi_candidate: bool = True  # ← 新規（デフォルトTrue）
    ai_recommendation: bool = True  # ← 新規（AI推奨システム）
```

**新規SSEイベント**:
```python
# type='candidate_selection'
{
    "type": "candidate_selection",
    "data": {
        "candidates": [
            {
                "id": "A",
                "label": "シンプル型",
                "data_source": "...",
                "process_description": "...",
                "output_format": "...",
                "schedule": "...",
                "completeness": 0.8,
                "recommended": true,
                "ai_confidence": 0.92  # ← AI推奨の信頼度
            },
            {
                "id": "B",
                "label": "機能豊富型",
                "data_source": "...",
                "process_description": "...",
                "output_format": "...",
                "schedule": "...",
                "completeness": 0.9,
                "recommended": false,
                "ai_confidence": 0.68
            }
        ],
        "ai_reasoning": "ユーザーメッセージから「シンプル」「迅速」などのキーワードを検出しました。"
    }
}
```

**実装方針**:
1. `stream_requirement_clarification()` で初回メッセージを検知
2. `MULTI_CANDIDATE_GENERATION_PROMPT` を使用してLLMに2パターンを生成させる
3. `AIRecommendationService.analyze_user_message()` でAI推奨を計算
4. SSE イベント `candidate_selection` を送信
5. ユーザーが候補を選択後、`context.selected_candidate_id` で後続対話を継続

**AI推奨サービス詳細設計**:
```python
# app/services/ai_recommendation_service.py
from typing import List, Tuple, Dict
import re
from enum import Enum

class ComplexityLevel(Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"

class AIRecommendationService:
    """候補選択のためのAI推奨システム"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.keyword_weights = {
            # シンプル型を推奨するキーワード
            "simple": {"シンプル": 3, "簡単": 3, "基本": 2, "最小": 2,
                      "手軽": 2, "すぐ": 3, "簡潔": 2},
            # 機能豊富型を推奨するキーワード
            "complex": {"詳細": 3, "高度": 3, "複雑": 3, "カスタム": 2,
                       "多機能": 3, "全て": 2, "網羅": 3, "分析": 2}
        }

    def analyze_user_message(self, message: str) -> Dict:
        """ユーザーメッセージを分析してAI推奨を生成"""

        # Step 1: キーワード分析による重み付けスコア計算
        keyword_score = self._calculate_keyword_score(message)

        # Step 2: メッセージ複雑度の推定
        complexity = self._estimate_complexity(message)

        # Step 3: LLM分析（高精度モード時のみ）
        llm_analysis = None
        if self.llm_client:
            llm_analysis = self._llm_deep_analysis(message)

        # Step 4: 総合スコアの計算と推奨候補の決定
        recommendation = self._calculate_recommendation(
            keyword_score, complexity, llm_analysis
        )

        return recommendation

    def _calculate_keyword_score(self, message: str) -> Dict[str, float]:
        """キーワードベースのスコア計算"""
        scores = {"simple": 0.0, "complex": 0.0}

        for category, keywords in self.keyword_weights.items():
            for keyword, weight in keywords.items():
                count = message.count(keyword)
                scores[category] += count * weight

        # 正規化（0-1の範囲に）
        total = sum(scores.values())
        if total > 0:
            scores = {k: v/total for k, v in scores.items()}

        return scores

    def _estimate_complexity(self, message: str) -> ComplexityLevel:
        """メッセージの複雑度を推定"""
        indicators = {
            "simple": [
                len(message) < 50,
                message.count("、") < 2,
                not re.search(r"複数|様々|各種|多[い数]", message)
            ],
            "complex": [
                len(message) > 100,
                message.count("、") > 3,
                bool(re.search(r"複数|様々|各種|多[い数]|詳細|高度", message)),
                bool(re.search(r"分析|予測|最適化|自動化", message))
            ]
        }

        simple_score = sum(indicators["simple"])
        complex_score = sum(indicators["complex"])

        if complex_score > simple_score:
            return ComplexityLevel.COMPLEX
        elif simple_score > complex_score:
            return ComplexityLevel.SIMPLE
        else:
            return ComplexityLevel.MODERATE

    def _llm_deep_analysis(self, message: str) -> Dict:
        """LLMを使用した深層分析（オプション）"""
        prompt = f"""
        以下のユーザーメッセージを分析し、要件の複雑さを評価してください:

        メッセージ: {message}

        評価基準:
        1. データソースの複雑さ (1-5)
        2. 処理ロジックの複雑さ (1-5)
        3. 出力形式の複雑さ (1-5)
        4. 非機能要件の有無 (yes/no)

        JSON形式で回答してください。
        """

        # LLM呼び出し（構造化出力）
        response = self.llm_client.generate_structured(
            prompt,
            response_format=AnalysisResult
        )

        return response

    def _calculate_recommendation(
        self,
        keyword_score: Dict,
        complexity: ComplexityLevel,
        llm_analysis: Optional[Dict]
    ) -> Dict:
        """総合的な推奨を計算"""

        # 基本スコア
        base_scores = {
            "A": keyword_score.get("simple", 0.5),
            "B": keyword_score.get("complex", 0.5)
        }

        # 複雑度による調整
        if complexity == ComplexityLevel.SIMPLE:
            base_scores["A"] *= 1.3
            base_scores["B"] *= 0.7
        elif complexity == ComplexityLevel.COMPLEX:
            base_scores["A"] *= 0.7
            base_scores["B"] *= 1.3

        # LLM分析による調整（利用可能な場合）
        if llm_analysis:
            avg_complexity = sum(llm_analysis["scores"].values()) / len(llm_analysis["scores"])
            if avg_complexity > 3:
                base_scores["B"] *= 1.2
            else:
                base_scores["A"] *= 1.2

        # 正規化と最終決定
        total = sum(base_scores.values())
        confidence_scores = {k: v/total for k, v in base_scores.items()}

        recommended = "A" if confidence_scores["A"] > confidence_scores["B"] else "B"

        return {
            "recommended_candidate": recommended,
            "confidence_scores": confidence_scores,
            "confidence": max(confidence_scores.values()),
            "reasoning": self._generate_reasoning(
                keyword_score, complexity, recommended
            )
        }

    def _generate_reasoning(
        self,
        keyword_score: Dict,
        complexity: ComplexityLevel,
        recommended: str
    ) -> str:
        """推奨理由の生成"""
        if recommended == "A":
            return (
                f"シンプルさを重視するキーワード（スコア: {keyword_score.get('simple', 0):.2f}）"
                f"と複雑度レベル（{complexity.value}）から、"
                "シンプル型の候補Aをお勧めします。"
            )
        else:
            return (
                f"高機能性を重視するキーワード（スコア: {keyword_score.get('complex', 0):.2f}）"
                f"と複雑度レベル（{complexity.value}）から、"
                "機能豊富型の候補Bをお勧めします。"
            )
```

---

### Phase 1.5: 永続化基盤強化（優先度 High）

#### 1.5.1 Valkey永続化層の実装

**目的**: 現在インメモリで管理している会話データを Valkey に永続化し、スケーラビリティと信頼性を向上

**背景**:
- 現在の `ConversationStore` はインメモリ（dict）で実装されているため、サーバー再起動時にデータが消失
- 複数インスタンス間でのデータ共有が不可能
- メモリ使用量が無制限に増加する可能性

**Valkey選定理由**:
- Redisのオープンソースフォーク（Linux Foundation管理）
- BSD 3-Clauseライセンスで商用利用も安心
- Redis互換APIで移行が容易
- 活発なコミュニティサポート

**実装設計**:
```python
# app/services/conversation_store_valkey.py
import valkey.asyncio as valkey  # valkey-py パッケージを使用
import json
from typing import Optional, Dict, List
from datetime import timedelta

class ConversationStoreValkey(ConversationStore):
    """Valkey を使用した永続化対応の会話ストア"""

    def __init__(self, valkey_client: valkey.Valkey, ttl: int = 86400):
        """
        Args:
            valkey_client: Valkey クライアントインスタンス
            ttl: データの有効期限（秒）、デフォルト24時間
        """
        self.valkey = valkey_client
        self.ttl = ttl  # 24時間でデータを自動削除
        self.key_prefix = "mlops:conversation:"

    async def save_message(self, conversation_id: str, role: str, content: str):
        """会話メッセージを保存"""
        key = f"{self.key_prefix}{conversation_id}:messages"
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.valkey.rpush(key, json.dumps(message))
        await self.valkey.expire(key, self.ttl)

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """会話履歴を取得"""
        key = f"{self.key_prefix}{conversation_id}:messages"
        messages = await self.valkey.lrange(key, 0, -1)
        if not messages:
            return None

        conversation = Conversation(
            conversation_id=conversation_id,
            messages=[json.loads(msg) for msg in messages]
        )
        return conversation

    async def save_trace_id(self, conversation_id: str, trace_id: str):
        """Langfuse trace_id を保存"""
        key = f"{self.key_prefix}{conversation_id}:trace_id"
        await self.valkey.set(key, trace_id, ex=self.ttl)

    async def get_trace_id(self, conversation_id: str) -> Optional[str]:
        """trace_id を取得"""
        key = f"{self.key_prefix}{conversation_id}:trace_id"
        return await self.valkey.get(key)

    async def save_prompt_version(self, conversation_id: str, version: str):
        """プロンプトバージョンを保存"""
        key = f"{self.key_prefix}{conversation_id}:prompt_version"
        await self.valkey.set(key, version, ex=self.ttl)

    async def get_statistics(self, days: int = 30) -> Dict:
        """統計情報を取得（Valkey Streams を活用）"""
        # 実装の詳細は省略
        pass
```

**設定変更**:
```python
# app/core/config.py
class Settings(BaseSettings):
    # 既存設定...

    # Valkey設定（新規追加）
    VALKEY_URL: str = Field(
        default="valkey://localhost:6379/0",
        description="Valkey接続URL（Redis互換プロトコル）"
    )
    CONVERSATION_TTL: int = Field(
        default=86400,  # 24時間
        description="会話データのTTL（秒）"
    )
    USE_VALKEY_STORE: bool = Field(
        default=False,  # 段階的移行のためデフォルトは False
        description="Valkey ストアを使用するかどうか"
    )
```

**段階的移行戦略**:
1. **Phase 1.5.1**: Valkey実装を追加（既存のインメモリ実装と並行）
2. **Phase 1.5.2**: 環境変数 `USE_VALKEY_STORE=true` で切り替え可能に
3. **Phase 1.5.3**: 本番環境でValkeyを有効化
4. **Phase 1.5.4**: インメモリ実装を非推奨化

**メリット**:
- ✅ サーバー再起動してもデータが保持される
- ✅ 複数インスタンス間でデータ共有可能（水平スケーリング対応）
- ✅ TTLによる自動データクリーンアップ
- ✅ Valkey Streams を使用した効率的な統計集計
- ✅ Valkey Pub/Sub を使用したリアルタイム通知基盤
- ✅ BSD 3-Clauseライセンスで商用利用も安心

---

### Phase 2: 品質可視化・プロンプト管理（優先度 Medium）

#### 2.1 品質可視化機能（FR-3）

**目的**: 要件定義APIの品質メトリクスを可視化

**新規エンドポイント**:
```python
GET /v1/observability/requirement-definition-metrics
    ?days=30
    &model=gemini-2.5-flash
```

**レスポンススキーマ**:
```python
class RequirementDefinitionMetrics(BaseModel):
    period: MetricsPeriod
    average_scores: AverageScores
    average_turns: float
    completion_rate: float  # completeness ≥ 0.8 到達率
    average_completion_time_seconds: float
    model_usage: Dict[str, float]  # {"gemini-2.5-flash": 0.85, ...}
    error_rate: float
    total_conversations: int

class MetricsPeriod(BaseModel):
    start_date: str  # ISO 8601
    end_date: str
    days: int

class AverageScores(BaseModel):
    requirement_clarity: float
    hypothesis_accuracy: float
    response_naturalness: float
    overall_satisfaction: float
```

**実装方針**:
1. Langfuse API で `tag='requirement-definition'` のトレースを取得
2. Langfuse API で対応するスコアを取得
3. `conversation_store.get_statistics(days)` で対話ターン数・完了率を計算
4. 平均値・集計値を計算してレスポンスを生成

**リアルタイムダッシュボード用SSEエンドポイント**:
```python
# app/api/v1/observability_endpoints.py
from fastapi import Response
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
from datetime import datetime, timedelta

@router.get("/v1/observability/requirement-definition-metrics-stream")
async def stream_requirement_metrics():
    """リアルタイムメトリクスのSSEストリーム"""

    async def generate_metrics_events():
        """メトリクスイベントの生成"""
        last_update = datetime.utcnow()

        while True:
            try:
                # 5秒ごとに最新メトリクスを取得
                current_time = datetime.utcnow()

                # 差分データのみ取得（効率化）
                delta_metrics = await get_delta_metrics(last_update)

                if delta_metrics:
                    # SSEイベントとして送信
                    yield {
                        "event": "metrics_update",
                        "data": json.dumps({
                            "timestamp": current_time.isoformat(),
                            "type": "delta",
                            "metrics": delta_metrics,
                            "current_values": await get_current_aggregates()
                        })
                    }

                    last_update = current_time

                # ハートビート（30秒ごと）
                elif (current_time - last_update).seconds > 30:
                    yield {
                        "event": "heartbeat",
                        "data": json.dumps({
                            "timestamp": current_time.isoformat()
                        })
                    }

                await asyncio.sleep(5)  # 5秒間隔で更新

            except asyncio.CancelledError:
                break
            except Exception as e:
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                }

    return EventSourceResponse(generate_metrics_events())

async def get_delta_metrics(since: datetime) -> Dict:
    """指定時刻以降の差分メトリクスを取得"""
    # Langfuse APIから最新のスコアを取得
    new_scores = await langfuse_client.get_scores(
        tag="requirement-definition",
        since=since
    )

    if not new_scores:
        return None

    # 差分計算
    delta = {
        "new_conversations": len(new_scores),
        "latest_scores": [
            {
                "conversation_id": score.trace_id,
                "timestamp": score.created_at,
                "scores": {
                    "requirement_clarity": score.requirement_clarity,
                    "hypothesis_accuracy": score.hypothesis_accuracy,
                    "response_naturalness": score.response_naturalness,
                    "overall_satisfaction": score.overall_satisfaction
                }
            }
            for score in new_scores[:5]  # 最新5件のみ
        ]
    }

    return delta

async def get_current_aggregates() -> Dict:
    """現在の集計値を取得"""
    # 直近1時間、24時間、7日間の集計
    periods = {
        "1h": timedelta(hours=1),
        "24h": timedelta(days=1),
        "7d": timedelta(days=7)
    }

    aggregates = {}
    for period_name, delta in periods.items():
        since = datetime.utcnow() - delta
        metrics = await calculate_metrics(since=since)

        aggregates[period_name] = {
            "average_score": metrics.average_overall_score,
            "completion_rate": metrics.completion_rate,
            "total_conversations": metrics.total_conversations,
            "error_rate": metrics.error_rate
        }

    return aggregates
```

**フロントエンド実装例（SvelteKit）**:
```typescript
// myAgentDesk/src/lib/services/realtimeMetrics.ts
import { readable, derived } from 'svelte/store';

export function createMetricsStream(apiUrl: string) {
    return readable(null, (set) => {
        const eventSource = new EventSource(
            `${apiUrl}/v1/observability/requirement-definition-metrics-stream`
        );

        eventSource.addEventListener('metrics_update', (event) => {
            const data = JSON.parse(event.data);
            set(data);
        });

        eventSource.addEventListener('error', (event) => {
            console.error('SSE Error:', event);
        });

        return () => eventSource.close();
    });
}

// リアルタイムチャート更新
export const metricsStore = createMetricsStream(API_BASE_URL);
export const chartData = derived(metricsStore, ($metrics) => {
    if (!$metrics) return null;

    return {
        labels: $metrics.timestamps,
        datasets: [{
            label: '完了率',
            data: $metrics.completion_rates,
            borderColor: 'rgb(75, 192, 192)',
            tension: 0.1
        }]
    };
});
```

---

#### 2.2 プロンプト外部管理機能（FR-5）

**目的**: プロンプトをYAMLファイルで管理し、バージョン切り替えを可能にする

**ディレクトリ構造**:
```
expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/prompts/templates/requirement_clarification/
├── v1/
│   ├── system_prompt.yaml
│   ├── extraction_prompt.yaml
│   └── multi_candidate_prompt.yaml
├── v2/  # ABテスト用
│   ├── system_prompt.yaml
│   ├── extraction_prompt.yaml
│   └── multi_candidate_prompt.yaml
└── loader.py
```

**YAML フォーマット例**:
```yaml
# system_prompt.yaml
version: "v1"
created_at: "2025-11-11"
description: "要件明確化システムプロンプト（仮説駆動型）"
model_compatibility:
  - "gemini-2.5-flash"
  - "gemini-2.0-flash"
prompt: |
  あなたは要件明確化のエキスパートです。
  ユーザーの曖昧な要求を以下の4つの観点で明確化してください:

  1. データソース（25%）: どのデータを使うか
  2. 処理内容（35%）: どのような処理を行うか
  3. 出力形式（25%）: どのような形式で出力するか
  4. スケジュール（15%）: いつ実行するか

  【重要】初回の応答では、4つの観点すべての仮説を提示してください。

  ...（以下略）
```

**プロンプトローダー実装（ホットリロード対応）**:
```python
# loader.py
from pathlib import Path
import yaml
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import hashlib
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging

class PromptLoader:
    """YAMLプロンプトローダー（ホットリロード機能付き）"""

    def __init__(self, base_path: Path, enable_hot_reload: bool = False):
        self.base_path = base_path
        self.enable_hot_reload = enable_hot_reload
        self._cache: Dict[str, Any] = {}
        self._file_hashes: Dict[str, str] = {}
        self._last_modified: Dict[str, datetime] = {}
        self.logger = logging.getLogger(__name__)

        # ホットリロード用のファイル監視
        if enable_hot_reload:
            self._start_file_watcher()

    def load(
        self,
        prompt_type: str,  # "system_prompt" / "extraction_prompt" / "multi_candidate_prompt"
        version: str = "v1",
        use_cache: bool = True
    ) -> str:
        """プロンプトの読み込み（キャッシュ対応）"""

        cache_key = f"{version}/{prompt_type}"

        # キャッシュの確認（ホットリロード時は無効化チェック）
        if use_cache and cache_key in self._cache:
            if not self.enable_hot_reload or self._is_cache_valid(cache_key):
                self.logger.debug(f"Using cached prompt: {cache_key}")
                return self._cache[cache_key]['prompt']

        # YAMLファイルの読み込み
        yaml_path = self.base_path / version / f"{prompt_type}.yaml"

        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            # キャッシュの更新
            self._cache[cache_key] = data
            self._update_file_hash(cache_key, yaml_path)
            self._last_modified[cache_key] = datetime.utcnow()

            self.logger.info(f"Loaded prompt: {cache_key}")
            return data['prompt']

        except FileNotFoundError:
            self.logger.error(f"Prompt file not found: {yaml_path}")
            raise
        except yaml.YAMLError as e:
            self.logger.error(f"Invalid YAML in {yaml_path}: {e}")
            raise

    def load_metadata(
        self,
        prompt_type: str,
        version: str = "v1"
    ) -> Dict[str, Any]:
        """プロンプトのメタデータ取得"""

        cache_key = f"{version}/{prompt_type}"

        # キャッシュから取得
        if cache_key in self._cache:
            data = self._cache[cache_key]
        else:
            # load()を呼んでキャッシュに格納
            self.load(prompt_type, version)
            data = self._cache[cache_key]

        return {
            "version": data.get("version"),
            "created_at": data.get("created_at"),
            "description": data.get("description"),
            "model_compatibility": data.get("model_compatibility", []),
            "last_modified": self._last_modified.get(cache_key)
        }

    def _is_cache_valid(self, cache_key: str) -> bool:
        """キャッシュの有効性チェック（ファイル変更検知）"""

        if cache_key not in self._file_hashes:
            return False

        version, prompt_type = cache_key.split('/')
        yaml_path = self.base_path / version / f"{prompt_type}.yaml"

        # ファイルハッシュの比較
        current_hash = self._calculate_file_hash(yaml_path)
        return current_hash == self._file_hashes[cache_key]

    def _calculate_file_hash(self, file_path: Path) -> str:
        """ファイルのハッシュ値計算"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except:
            return ""

    def _update_file_hash(self, cache_key: str, file_path: Path):
        """ファイルハッシュの更新"""
        self._file_hashes[cache_key] = self._calculate_file_hash(file_path)

    def _start_file_watcher(self):
        """ファイル変更監視の開始"""

        class PromptFileHandler(FileSystemEventHandler):
            def __init__(self, loader):
                self.loader = loader

            def on_modified(self, event):
                if event.src_path.endswith('.yaml'):
                    self.loader._invalidate_cache_for_file(event.src_path)

        event_handler = PromptFileHandler(self)
        observer = Observer()
        observer.schedule(event_handler, str(self.base_path), recursive=True)
        observer.start()

        self.logger.info(f"Hot reload enabled for: {self.base_path}")

    def _invalidate_cache_for_file(self, file_path: str):
        """特定ファイルのキャッシュ無効化"""

        # ファイルパスからキャッシュキーを生成
        path = Path(file_path)
        if path.suffix == '.yaml' and path.parent.parent == self.base_path:
            version = path.parent.name
            prompt_type = path.stem
            cache_key = f"{version}/{prompt_type}"

            if cache_key in self._cache:
                del self._cache[cache_key]
                self.logger.info(f"Cache invalidated due to file change: {cache_key}")

    def reload_all(self):
        """全プロンプトの強制リロード"""
        self._cache.clear()
        self._file_hashes.clear()
        self._last_modified.clear()
        self.logger.info("All prompt caches cleared")

    def get_available_versions(self) -> list:
        """利用可能なバージョン一覧を取得"""
        versions = []
        for path in self.base_path.iterdir():
            if path.is_dir() and path.name.startswith('v'):
                versions.append(path.name)
        return sorted(versions)

    def validate_all_prompts(self) -> Dict[str, bool]:
        """全プロンプトの妥当性検証"""
        results = {}

        for version in self.get_available_versions():
            for prompt_type in ["system_prompt", "extraction_prompt", "multi_candidate_prompt"]:
                key = f"{version}/{prompt_type}"
                try:
                    self.load(prompt_type, version, use_cache=False)
                    results[key] = True
                except Exception as e:
                    results[key] = False
                    self.logger.error(f"Validation failed for {key}: {e}")

        return results


# 環境変数でホットリロードを制御
import os

def create_prompt_loader() -> PromptLoader:
    """環境変数に基づいてプロンプトローダーを作成"""

    base_path = Path(__file__).parent / "templates" / "requirement_clarification"
    enable_hot_reload = os.getenv("ENABLE_PROMPT_HOT_RELOAD", "false").lower() == "true"

    loader = PromptLoader(base_path, enable_hot_reload)

    # 開発環境では起動時に全プロンプトを検証
    if enable_hot_reload:
        validation_results = loader.validate_all_prompts()
        for key, valid in validation_results.items():
            status = "✓" if valid else "✗"
            print(f"  {status} {key}")

    return loader

# シングルトンインスタンス
prompt_loader = create_prompt_loader()
```

**環境変数**:
```bash
REQUIREMENT_CLARIFICATION_PROMPT_VERSION=v1  # デフォルト: v1
```

---

### Phase 3: ABテスト機能（優先度 Low）

#### 3.1 ABテスト機能（FR-6）

**目的**: 2つ以上のプロンプトバージョンを並行運用し、統計的有意差を検定

**拡張パラメータ**:
```python
class RequirementChatRequest(BaseModel):
    conversation_id: str
    user_message: str
    context: RequirementContext
    enable_multi_candidate: bool = True
    ai_recommendation: bool = True
    prompt_version: Optional[str] = None  # ← 新規（未指定時はランダム選択）
```

**新規エンドポイント**:
```python
GET /v1/observability/requirement-definition-ab-test
    ?days=30
```

**レスポンススキーマ**:
```python
class ABTestResult(BaseModel):
    version_a: VersionMetrics
    version_b: VersionMetrics
    statistical_significance: StatisticalSignificance

class VersionMetrics(BaseModel):
    version: str  # "v1" / "v2"
    sample_size: int
    average_scores: AverageScores
    average_turns: float
    completion_rate: float
    average_completion_time_seconds: float

class StatisticalSignificance(BaseModel):
    requirement_clarity: SignificanceTest
    hypothesis_accuracy: SignificanceTest
    response_naturalness: SignificanceTest
    overall_satisfaction: SignificanceTest

class SignificanceTest(BaseModel):
    p_value: float
    significant: bool  # p_value < 0.05
    confidence_level: float  # 0.95
    effect_size: float  # Cohen's d
```

**実装方針**:
1. `ABTestService.assign_version(conversation_id)` でランダムにv1/v2を割り当て
2. `conversation_store.save_prompt_version(conversation_id, version)` で保存
3. Langfuse tags に `prompt_version=v1` を記録
4. `ABTestService.collect_metrics(version, days)` で各バージョンのメトリクスを集計
5. `scipy.stats.ttest_ind()` で統計検定を実行
6. Cohen's d で効果サイズを計算

---

## 💾 データモデル設計

### 1. Conversation Store 拡張

**既存**: インメモリストア（dict）

**拡張内容**:
```python
# conversation_store.py
from typing import Dict, List, Optional
from datetime import datetime

class ConversationStore:
    def __init__(self):
        self._conversations: Dict[str, Conversation] = {}
        self._trace_mappings: Dict[str, str] = {}  # conversation_id -> trace_id
        self._prompt_versions: Dict[str, str] = {}  # conversation_id -> version

    # 既存メソッド
    def save_message(self, conversation_id: str, role: str, content: str): ...
    def get_conversation(self, conversation_id: str) -> Conversation: ...

    # 新規メソッド
    def save_trace_id(self, conversation_id: str, trace_id: str):
        """Langfuse trace_id を保存"""
        self._trace_mappings[conversation_id] = trace_id

    def get_trace_id(self, conversation_id: str) -> Optional[str]:
        """conversation_id から trace_id を取得"""
        return self._trace_mappings.get(conversation_id)

    def save_prompt_version(self, conversation_id: str, version: str):
        """使用したプロンプトバージョンを保存"""
        self._prompt_versions[conversation_id] = version

    def get_prompt_version(self, conversation_id: str) -> Optional[str]:
        """conversation_id からプロンプトバージョンを取得"""
        return self._prompt_versions.get(conversation_id)

    def get_statistics(self, days: int) -> ConversationStatistics:
        """統計情報を集計"""
        cutoff_date = datetime.now() - timedelta(days=days)
        conversations = [
            c for c in self._conversations.values()
            if c.created_at >= cutoff_date
        ]

        total = len(conversations)
        completed = sum(1 for c in conversations if c.completeness >= 0.8)
        average_turns = sum(len(c.messages) for c in conversations) / total if total > 0 else 0

        return ConversationStatistics(
            total_conversations=total,
            completed_conversations=completed,
            completion_rate=completed / total if total > 0 else 0,
            average_turns=average_turns / 2  # ユーザー + アシスタントのペア
        )

class Conversation(BaseModel):
    conversation_id: str
    messages: List[Message]
    requirements: Optional[RequirementState] = None
    completeness: float = 0.0
    created_at: datetime
    updated_at: datetime

class Message(BaseModel):
    role: str  # "user" / "assistant"
    content: str
    timestamp: datetime
```

---

### 2. Langfuse タグ設計

**タグ戦略**:
```python
# Langfuse トレーシング時に付与するタグ
tags = [
    "requirement-definition",  # 要件定義APIを識別
    f"prompt_version={prompt_version}",  # ABテスト用（v1, v2, ...）
    f"multi_candidate={enable_multi_candidate}",  # 複数候補提示の有無
    f"ai_recommendation={ai_recommendation}",  # AI推奨の有無
    f"conversation_id={conversation_id}",  # 会話ID
]
```

**メタデータ**:
```python
metadata = {
    "conversation_id": conversation_id,
    "model": "gemini-2.5-flash",
    "temperature": 0.7,
    "max_tokens": 8192,
    "prompt_version": "v1",
    "enable_multi_candidate": True,
    "ai_recommendation": True,
    "selected_candidate_id": "A",  # ユーザーが選択した候補
}
```

---

## 🔀 データフロー設計

### 1. AI推奨付き複数候補提示フロー

```
User
  │
  ├─ POST /v1/chat/requirement-definition
  │  {
  │    "conversation_id": "conv_001",
  │    "user_message": "売上データを分析したい",
  │    "context": {"current_requirements": null, "previous_messages": []},
  │    "enable_multi_candidate": true,
  │    "ai_recommendation": true
  │  }
  │
  v
stream_requirement_clarification()
  │
  ├─ 初回メッセージ検知
  ├─ ABTestService.assign_version() → "v1"
  ├─ PromptLoader.load("multi_candidate_prompt", "v1")
  │
  v
LLM (gemini-2.5-flash)
  ├─ MULTI_CANDIDATE_GENERATION_PROMPT
  ├─ 構造化出力: [CandidateA, CandidateB]
  │
  v
AIRecommendationService.analyze_user_message()
  ├─ キーワード分析: ["売上", "データ", "分析"]
  ├─ 複雑度推定: "シンプル"
  ├─ 信頼度計算: CandidateA=0.92, CandidateB=0.68
  │
  v
SSE Event: candidate_selection
  {
    "type": "candidate_selection",
    "data": {
      "candidates": [
        {"id": "A", ..., "recommended": true, "ai_confidence": 0.92},
        {"id": "B", ..., "recommended": false, "ai_confidence": 0.68}
      ],
      "ai_reasoning": "キーワード「分析」から基本的な集計処理を想定。シンプル型を推奨します。"
    }
  }
  │
  v
conversation_store.save_trace_id(conversation_id, trace_id)
conversation_store.save_prompt_version(conversation_id, "v1")
  │
  v
Langfuse Trace
  tags: ["requirement-definition", "prompt_version=v1", "multi_candidate=true", "ai_recommendation=true"]
  metadata: {"selected_candidate_id": "A", "ai_confidence": 0.92, ...}
```

---

### 2. フィードバック投稿フロー

```
User (会話完了後)
  │
  ├─ POST /v1/chat/feedback
  │  {
  │    "conversation_id": "conv_001",
  │    "scores": {
  │      "requirement_clarity": 4,
  │      "hypothesis_accuracy": 5,
  │      "response_naturalness": 4,
  │      "overall_satisfaction": 5
  │    },
  │    "comment": "AI推奨が的確でした"
  │  }
  │
  v
conversation_store.get_trace_id("conv_001") → "trace_abc123"
  │
  v
For each score_type in ["requirement_clarity", "hypothesis_accuracy", ...]:
  POST /observability/scores
    {
      "trace_id": "trace_abc123",
      "name": score_type,
      "value": scores[score_type],
      "comment": "AI推奨が的確でした"
    }
  │
  v
Langfuse Score 保存
  ├─ trace_id: "trace_abc123"
  ├─ name: "requirement_clarity"
  ├─ value: 4.0
  ├─ comment: "AI推奨が的確でした"
```

---

### 3. ABテスト統計検定フロー

```
Admin
  │
  ├─ GET /v1/observability/requirement-definition-ab-test?days=30
  │
  v
ABTestService.collect_metrics("v1", 30)
ABTestService.collect_metrics("v2", 30)
  │
  ├─ Langfuse.fetch_traces(tag="prompt_version=v1", days=30)
  ├─ Langfuse.fetch_scores(tag="prompt_version=v1", days=30)
  ├─ conversation_store.get_statistics(days=30, version="v1")
  │
  v
統計検定
  ├─ scipy.stats.ttest_ind(v1_scores, v2_scores) → p_value
  ├─ Cohen's d 計算 → effect_size
  ├─ 有意性判定: p_value < 0.05
  │
  v
Response
  {
    "version_a": {
      "version": "v1",
      "sample_size": 120,
      "average_scores": {"requirement_clarity": 4.2, ...},
      "average_turns": 3.5,
      "completion_rate": 0.87
    },
    "version_b": {
      "version": "v2",
      "sample_size": 115,
      "average_scores": {"requirement_clarity": 4.4, ...},
      "average_turns": 3.2,
      "completion_rate": 0.91
    },
    "statistical_significance": {
      "requirement_clarity": {"p_value": 0.03, "significant": true, "effect_size": 0.25},
      "hypothesis_accuracy": {"p_value": 0.12, "significant": false, "effect_size": 0.15},
      ...
    }
  }
```

---

## 🧪 テスト戦略

### 単体テスト（目標カバレッジ90%以上）

**対象モジュール**:
1. `ai_recommendation.py`: AI推奨ロジック
2. `ab_test.py`: ABテスト・統計検定
3. `prompts/loader.py`: プロンプトローダー
4. `conversation_store.py` (拡張部分)

**テストケース例**:
```python
# tests/unit/test_ai_recommendation.py
def test_analyze_user_message_simple_case():
    service = AIRecommendationService()
    result = service.analyze_user_message("売上データを分析したい")

    assert result.recommended_candidate == "A"  # シンプル型
    assert result.confidence >= 0.8
    assert "シンプル" in result.reasoning

def test_analyze_user_message_complex_case():
    service = AIRecommendationService()
    result = service.analyze_user_message(
        "売上データを商品別・地域別に多次元分析し、トレンド予測とダッシュボード作成"
    )

    assert result.recommended_candidate == "B"  # 機能豊富型
    assert result.confidence >= 0.8
    assert "多次元" in result.reasoning or "トレンド" in result.reasoning
```

---

### 結合テスト（目標カバレッジ50%以上）

**対象フロー**:
1. 複数候補提示 → ユーザー選択 → 後続対話
2. フィードバック投稿 → Langfuse score 保存
3. メトリクス取得 → 統計集計
4. ABテスト → 統計検定

**テストケース例**:
```python
# tests/integration/test_requirement_definition_mlops.py
@pytest.mark.asyncio
async def test_multi_candidate_flow_with_ai_recommendation(client):
    # 1. 初回メッセージで複数候補提示
    response = client.post(
        "/v1/chat/requirement-definition",
        json={
            "conversation_id": "test_conv_001",
            "user_message": "売上データを分析したい",
            "context": {"current_requirements": None, "previous_messages": []},
            "enable_multi_candidate": True,
            "ai_recommendation": True
        }
    )

    # SSEイベントをパース
    events = parse_sse_events(response)

    # candidate_selection イベントを検証
    candidate_event = next(e for e in events if e["type"] == "candidate_selection")
    assert len(candidate_event["data"]["candidates"]) == 2
    assert any(c["recommended"] for c in candidate_event["data"]["candidates"])
    assert "ai_reasoning" in candidate_event["data"]

    # 2. 候補選択
    response2 = client.post(
        "/v1/chat/requirement-definition",
        json={
            "conversation_id": "test_conv_001",
            "user_message": "パターンAでお願いします",
            "context": {"selected_candidate_id": "A"},
            "enable_multi_candidate": True,
            "ai_recommendation": True
        }
    )

    # 後続対話が継続されることを確認
    events2 = parse_sse_events(response2)
    assert any(e["type"] == "message" for e in events2)

    # 3. フィードバック投稿
    response3 = client.post(
        "/v1/chat/feedback",
        json={
            "conversation_id": "test_conv_001",
            "scores": {
                "requirement_clarity": 4,
                "hypothesis_accuracy": 5,
                "response_naturalness": 4,
                "overall_satisfaction": 5
            },
            "comment": "AI推奨が的確"
        }
    )

    assert response3.status_code == 200
    assert response3.json()["status"] == "success"
```

---

## 🔐 非機能要件対応

### NFR-1: パフォーマンス

**対応策**:
1. **複数候補提示**: LLM呼び出しを1回に集約（2回呼び出しではなく、1回で2パターン生成）
2. **SSEストリーミング**: 初回チャンク500ms以内（既存実装で達成済み）
3. **品質可視化API**:
   - Langfuse APIのページネーション活用（1000件ずつ取得）
   - 集計処理の非同期化（`asyncio.gather()`）
   - キャッシュ機構（Redis、有効期限5分）

**パフォーマンス目標**:
- `POST /chat/requirement-definition` (複数候補): 既存の2倍以内（〜4秒）
- `GET /observability/requirement-definition-metrics`: 1秒以内
- `GET /observability/requirement-definition-ab-test`: 2秒以内

---

### NFR-2: 可用性

**対応策**:
1. **Langfuse障害時のフォールバック**:
   ```python
   try:
       trace = langfuse.trace(...)
   except Exception as e:
       logger.warning(f"Langfuse unavailable: {e}")
       # 要件定義API本体は継続動作
       trace = None
   ```

2. **会話履歴の保持期間**:
   - インメモリストアで24時間保持
   - 将来的にRedis/PostgreSQLへ移行予定

---

### NFR-3: 保守性

**対応策**:
1. **プロンプトYAML化**: エンジニア以外でも編集可能
2. **単体テストカバレッジ90%以上**: 全新機能で達成
3. **静的解析**: Ruff, MyPy でエラーゼロ
4. **ドキュメント**: 各機能の設計ドキュメント作成

---

### NFR-4: セキュリティ

**対応策**:
1. **Langfuse API キー**: myVault で管理
2. **会話履歴**: 個人情報を含めない（ユーザーIDのみ記録）
3. **APIエンドポイント**: 認証・認可（既存の仕組みを継承）

---

### NFR-5: エラーハンドリング（改善追加）

**MLOpsErrorHandler の実装**:
```python
# app/core/mlops_error_handler.py
from typing import Optional, Dict, Any, Callable
from functools import wraps
import logging
from enum import Enum
from datetime import datetime
import traceback

class ErrorSeverity(Enum):
    LOW = "low"        # ログのみ、処理は継続
    MEDIUM = "medium"  # 代替処理を実行
    HIGH = "high"      # エラーレスポンスを返却
    CRITICAL = "critical"  # サービス停止

class MLOpsError(Exception):
    """MLOps機能のカスタム例外クラス"""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity,
        error_code: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.severity = severity
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.utcnow()

class MLOpsErrorHandler:
    """統合エラーハンドリング管理"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.error_counts = {}  # エラータイプ別カウント
        self.circuit_breakers = {}  # サーキットブレーカー状態

    def handle_error(self, error: Exception, context: Dict[str, Any]) -> Dict:
        """エラーを処理し、適切なレスポンスを生成"""

        if isinstance(error, MLOpsError):
            return self._handle_mlops_error(error, context)
        else:
            return self._handle_generic_error(error, context)

    def _handle_mlops_error(self, error: MLOpsError, context: Dict) -> Dict:
        """MLOpsエラーの処理"""

        # エラーログ記録
        self.logger.error(
            f"MLOps Error: {error.error_code}",
            extra={
                "severity": error.severity.value,
                "details": error.details,
                "context": context,
                "traceback": traceback.format_exc()
            }
        )

        # エラーカウント更新
        self._increment_error_count(error.error_code)

        # 重要度に応じた処理
        if error.severity == ErrorSeverity.LOW:
            # 処理継続（デフォルト値使用）
            return {"action": "continue", "fallback": context.get("fallback")}

        elif error.severity == ErrorSeverity.MEDIUM:
            # 代替処理実行
            return {"action": "fallback", "alternative": self._get_alternative(error)}

        elif error.severity == ErrorSeverity.HIGH:
            # エラーレスポンス
            return {
                "action": "error_response",
                "status_code": 500,
                "error": {
                    "code": error.error_code,
                    "message": str(error),
                    "details": error.details
                }
            }

        else:  # CRITICAL
            # アラート送信とサーキットブレーカー発動
            self._trigger_alert(error)
            self._activate_circuit_breaker(error.error_code)
            return {"action": "service_degradation"}

    def _handle_generic_error(self, error: Exception, context: Dict) -> Dict:
        """一般的なエラーの処理"""

        self.logger.error(
            f"Unexpected Error: {str(error)}",
            extra={
                "context": context,
                "traceback": traceback.format_exc()
            }
        )

        return {
            "action": "error_response",
            "status_code": 500,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred"
            }
        }

    def _increment_error_count(self, error_code: str):
        """エラーカウントの更新"""
        if error_code not in self.error_counts:
            self.error_counts[error_code] = 0
        self.error_counts[error_code] += 1

    def _get_alternative(self, error: MLOpsError) -> Any:
        """代替処理の取得"""
        alternatives = {
            "LANGFUSE_UNAVAILABLE": {"use_local_logging": True},
            "LLM_TIMEOUT": {"use_cached_response": True},
            "VALKEY_CONNECTION_FAILED": {"use_memory_store": True}
        }
        return alternatives.get(error.error_code, {})

    def _trigger_alert(self, error: MLOpsError):
        """重大エラーのアラート送信"""
        # Slack/Email通知などの実装
        pass

    def _activate_circuit_breaker(self, error_code: str):
        """サーキットブレーカーの発動"""
        self.circuit_breakers[error_code] = {
            "status": "open",
            "opened_at": datetime.utcnow(),
            "retry_after": 60  # 60秒後に再試行
        }

# デコレーターパターンでの使用
def with_mlops_error_handling(
    fallback_value=None,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
):
    """エラーハンドリングデコレーター"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                handler = MLOpsErrorHandler(logging.getLogger(__name__))
                result = handler.handle_error(
                    e,
                    {"function": func.__name__, "fallback": fallback_value}
                )

                if result["action"] == "continue":
                    return result["fallback"]
                elif result["action"] == "fallback":
                    return result["alternative"]
                else:
                    raise

        return wrapper
    return decorator

# 使用例
@with_mlops_error_handling(fallback_value={"scores": {}}, severity=ErrorSeverity.MEDIUM)
async def get_langfuse_scores(conversation_id: str):
    """Langfuseからスコアを取得（エラー時は空の辞書を返却）"""
    try:
        return await langfuse_client.get_scores(conversation_id)
    except Exception as e:
        raise MLOpsError(
            message="Failed to fetch Langfuse scores",
            severity=ErrorSeverity.MEDIUM,
            error_code="LANGFUSE_FETCH_ERROR",
            details={"conversation_id": conversation_id}
        )
```

**エラー監視ダッシュボード**:
```python
GET /v1/observability/error-metrics

Response:
{
    "error_counts": {
        "LANGFUSE_UNAVAILABLE": 5,
        "LLM_TIMEOUT": 2,
        "VALKEY_CONNECTION_FAILED": 0
    },
    "circuit_breakers": {
        "LANGFUSE_API": {
            "status": "closed",
            "failure_rate": 0.02
        }
    },
    "recent_errors": [...]
}
```

---

## 📅 実装スケジュール

### Phase 1: 基盤強化（優先度 High）

| マイルストーン | 期間 | タスク | 担当 |
|---------------|------|--------|------|
| 1.1: 診断情報取得（FR-4） | 1週間 | Langfuseトレーシング、conversation_store拡張、診断API実装 | - |
| 1.2: フィードバック機能（FR-2） | 1週間 | スコアタイプ定義、フィードバックAPI実装、Langfuse統合 | - |
| 1.3: 複数候補提示（FR-1） | 2週間 | マルチ候補プロンプト作成、AI推奨サービス実装、SSEイベント拡張 | - |

**Phase 1 完了時期**: 4週間後

---

### Phase 1.5: 永続化基盤強化（優先度 High）

| マイルストーン | 期間 | タスク | 担当 |
|---------------|------|--------|------|
| 1.5.1: Valkey実装 | 1週間 | ConversationStoreValkey実装、設定追加 | - |
| 1.5.2: 切り替え機能 | 3日 | 環境変数による切り替え、テスト | - |
| 1.5.3: 本番移行 | 3日 | 段階的移行、監視設定 | - |

**Phase 1.5 完了時期**: 2週間後

---

### Phase 2: 品質可視化・プロンプト管理（優先度 Medium）

| マイルストーン | 期間 | タスク | 担当 |
|---------------|------|--------|------|
| 2.1: 品質可視化（FR-3） | 2週間 | メトリクスAPI実装、Langfuse統計集計、キャッシュ機構 | - |
| 2.2: プロンプト管理（FR-5） | 2週間 | YAML化、プロンプトローダー実装、バージョン切り替え | - |

**Phase 2 完了時期**: Phase 1完了後 + 4週間

---

### Phase 3: ABテスト機能（優先度 Low）

| マイルストーン | 期間 | タスク | 担当 |
|---------------|------|--------|------|
| 3.1: ABテスト（FR-6） | 3週間 | ABテストサービス実装、統計検定、バージョン比較API | - |

**Phase 3 完了時期**: Phase 2完了後 + 3週間

---

## ✅ 受入基準

### Phase 1

- [ ] FR-1: 複数候補提示機能が動作し、2パターンの要件解釈が返却される
- [ ] FR-1: AI推奨システムが信頼度92%以上で推奨候補を提示できる
- [ ] FR-2: 4種類のスコアタイプでフィードバックを投稿できる
- [ ] FR-2: Langfuse score が正しく紐付けられる
- [ ] FR-4: 診断情報APIでプロンプト・LLMレスポンスが取得できる
- [ ] FR-4: Langfuse トレースビューへのリンクが正しく生成される
- [ ] 単体テストカバレッジ90%以上
- [ ] 結合テストカバレッジ50%以上
- [ ] 静的解析エラーゼロ（Ruff, MyPy）

---

### Phase 2

- [ ] FR-3: 品質メトリクスAPIで平均スコア・対話ターン数・完了率が取得できる
- [ ] FR-3: レスポンスタイム1秒以内（1000会話以下）
- [ ] FR-5: 全プロンプトがYAMLファイルで管理されている
- [ ] FR-5: 環境変数でバージョン切り替えができる
- [ ] 単体テストカバレッジ90%以上
- [ ] 静的解析エラーゼロ

---

### Phase 3

- [ ] FR-6: 複数プロンプトバージョンを並行運用できる
- [ ] FR-6: 統計検定（t検定）が正しく実行される
- [ ] FR-6: ABテストAPIでバージョン間比較レポートが取得できる
- [ ] 単体テストカバレッジ90%以上
- [ ] 静的解析エラーゼロ

---

## 📚 参照ドキュメント

- [要件定義書](./requirements-definition.md)
- [UIモックアップサマリー](./ui-mockup-summary.md)
- [CLAUDE.md](../../../CLAUDE.md)
- [品質基準ドキュメント](../../../docs/claude/04-quality-standards.md)

---

## 🔄 変更履歴

| 日付 | バージョン | 変更内容 | 担当者 |
|------|-----------|---------|--------|
| 2025-11-11 | 1.0 | 初版作成（パターンD採用） | Claude |
| 2025-11-12 | 1.1 | 改善推奨事項を反映（Redis永続化、AI推奨詳細、SSE実装、エラーハンドリング、ホットリロード） | Claude |
| 2025-11-12 | 1.2 | RedisからValkeyへ変更（ライセンス懸念対応、BSD 3-Clause） | Claude |

---

**END OF DOCUMENT**
