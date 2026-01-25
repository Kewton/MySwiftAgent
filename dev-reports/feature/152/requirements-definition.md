# Issue #152: 要件定義エージェントへのMLOps導入 - 要件定義書

## 📋 概要

本ドキュメントは、Issue #152「要件定義エージェントへのMLOpsの導入」の要件定義を記載します。
expertAgent の `/v1/chat/requirement-definition` API（要件定義エージェント）に対し、MLOps の手法を導入することで、
品質の継続的改善サイクルを実現します。

**作成日**: 2025-11-11
**更新日**: 2025-11-11 (対象API修正、デフォルトモデル変更)
**対象Issue**: #152
**対象API**: `POST /v1/chat/requirement-definition`
**関連プロジェクト**: expertAgent
**優先度**: Medium（feature ラベル）

---

## 🎯 ビジネス要求

### ユーザーストーリー

Issue #152 に記載された6つのユーザーストーリーを整理します：

#### 1. 複数候補提示機能
**As a** ユーザー
**I want to** 要件定義エージェントに複数の候補（2パターン）を提示して欲しい
**So that** 複数の観点で比較する方が実際に欲しいものが明確になる

#### 2. 品質評価（フィードバック）機能
**As a** ユーザー
**I want to** 要件定義エージェントの品質評価（フィードバック）をしたい
**So that** ユーザーとしての考えを品質に反映したい

#### 3. 品質可視化機能
**As a** 管理者
**I want to** 要件定義エージェントの品質を可視化したい
**So that** 性能改善の要否を効率的に見極めたい

#### 4. 診断情報取得機能
**As a** 管理者
**I want to** 要件定義エージェントで利用されたプロンプトとLLMからのレスポンスを確認したい
**So that** 性能を低下させている根本原因の調査を効率化したい

#### 5. プロンプト外部管理機能
**As a** 管理者
**I want to** 要件定義エージェントのプロンプトを外部ファイルで管理可能にしたい
**So that** 改善を効率化したい

#### 6. ABテスト機能
**As a** 管理者
**I want to** 要件定義エージェントをABテストしたい
**So that** 遺伝アルゴリズム的に要件定義エージェントを改善していきたい

---

## 🔍 現状分析

### 対象API: `/v1/chat/requirement-definition`

#### API概要

- **エンドポイント**: `POST /v1/chat/requirement-definition`
- **実装ファイル**: `expertAgent/app/api/v1/chat_endpoints.py`
- **機能**: チャット形式で要件を明確化し、ジョブ作成に必要な4つの観点を収集
  - データソース（25%）
  - 処理内容（35% - 最重要）
  - 出力形式（25%）
  - スケジュール（15%）
- **レスポンス形式**: Server-Sent Events (SSE) によるストリーミング
- **完了条件**: completeness ≥ 0.8 (80%) でジョブ作成可能

#### プロンプト構成

1. **システムプロンプト**: `REQUIREMENT_CLARIFICATION_SYSTEM_PROMPT`
   - ファイル: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/prompts/requirement_clarification.py`
   - 役割: 要件明確化の方針・形式を定義
   - 特徴:
     - 仮説駆動型アプローチ（初回で4観点すべての仮説を提示）
     - 選択肢提示による誘導
     - JSON形式での構造化出力

2. **ユーザープロンプト**: `create_requirement_clarification_prompt()`
   - 対話履歴、現在の要件状態、ユーザーメッセージを組み込み
   - 動的に生成

3. **要件抽出プロンプト**: `extract_requirement_with_llm()`
   - 対話内容から RequirementState を構造化出力で抽出
   - 環境変数 `REQUIREMENT_EXTRACTION_MODEL` でモデル指定可能（デフォルト: gemini-2.0-flash）

#### LLM呼び出し

- **メインモデル**: 環境変数 `CHAT_CLARIFICATION_MODEL` で指定（**デフォルト: gemini-2.5-flash** ※今回の対応で変更）
- **最大トークン数**: 環境変数 `CHAT_CLARIFICATION_MAX_TOKENS` で指定（デフォルト: 8192）
- **Temperature**: 0.7（会話的な自然さを重視）
- **ストリーミング**: LangChain の `model.astream()` を使用
- **パフォーマンストラッキング**: `create_llm_with_fallback()` 経由で実装済み
- **備考**: 本Issue #152 の実装では、デフォルトモデルを gemini-2.0-flash から gemini-2.5-flash に変更する

### 既存実装の確認

#### ✅ 実装済み機能

1. **Langfuse統合（Observability基盤）**
   - ファイル: `expertAgent/app/api/v1/observability_endpoints.py`
   - 機能:
     - トレース一覧取得 (`GET /observability/traces`)
     - トレース詳細取得 (`GET /observability/traces/{trace_id}`)
     - フィードバックスコア投稿 (`POST /observability/scores`)
   - 備考: Issue #113 で実装済み

2. **LLM呼び出し基盤**
   - ファイル: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/utils/llm_factory.py`
   - 機能:
     - `create_llm_with_fallback()`: LLM生成 + パフォーマンストラッキング
     - フォールバック機構（プライマリモデル失敗時）
   - 備考: `/requirement-definition` API で既に使用中

3. **構造化LLM呼び出し**
   - ファイル: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/utils/llm_invocation.py`
   - 機能: `invoke_structured_llm()` による統一的な構造化出力
   - 備考: `extract_requirement_with_llm()` で使用中

4. **会話履歴管理**
   - ファイル: `expertAgent/app/services/conversation/conversation_store.py`
   - 機能: 対話履歴の保存・取得
   - 備考: インメモリストア（現状）

#### ❌ 未実装機能

1. **複数候補（2パターン）提示機能** - ユーザーストーリー #1
2. **要件定義API固有のフィードバック機能** - ユーザーストーリー #2
3. **品質可視化ダッシュボード** - ユーザーストーリー #3
4. **診断情報取得機能（要件定義API専用）** - ユーザーストーリー #4
5. **プロンプト全体の外部ファイル管理** - ユーザーストーリー #5（現在はPythonコード内に埋め込み）
6. **ABテスト機構** - ユーザーストーリー #6

---

## 📝 機能要件

### FR-1: 複数候補提示機能

**優先度**: High
**対応ユーザーストーリー**: #1

#### 要件詳細

- **FR-1.1**: 初回ユーザーメッセージに対し、2つの異なる要件解釈パターンを提示すること
  - パターンA: シンプル型（最小限の要件で実現）
  - パターンB: 機能豊富型（拡張機能を含む）
- **FR-1.2**: 各候補には以下の情報を含むこと：
  - データソース仮説
  - 処理内容仮説
  - 出力形式仮説
  - スケジュール仮説
  - completeness（初回は仮説なので暫定値）
  - 推奨レベル（recommended / alternative）
- **FR-1.3**: ユーザーが候補を選択できるSSEイベントを送信すること
  - イベント例: `{"type": "candidate_selection", "data": {"candidates": [...]}}`
- **FR-1.4**: 選択された候補に基づいて、後続の対話を継続すること

#### 実装方針

1. `stream_requirement_clarification()` を拡張し、初回メッセージ時に2パターン生成
2. 新規プロンプト `MULTI_CANDIDATE_GENERATION_PROMPT` を作成
3. SSEイベントに `candidate_selection` タイプを追加
4. フロントエンド（myAgentDesk）で候補選択UIを実装（Phase 2）

**設計ドキュメント**: `design-policy-candidate-selection.md` で詳細化予定

---

### FR-2: 品質評価（フィードバック）機能

**優先度**: High
**対応ユーザーストーリー**: #2

#### 要件詳細

- **FR-2.1**: 既存の Langfuse フィードバック機能を活用すること
- **FR-2.2**: 要件定義API固有のスコアタイプを定義すること：
  - `requirement_clarity`: 要件明確化の分かりやすさ（1-5）
  - `hypothesis_accuracy`: 仮説の精度（1-5）
  - `response_naturalness`: 応答の自然さ（1-5）
  - `overall_satisfaction`: 総合満足度（1-5）
- **FR-2.3**: 会話完了後（completeness ≥ 0.8）にフィードバックUIを表示すること
- **FR-2.4**: フィードバック投稿時に conversation_id を紐付けること

#### 実装方針

1. 既存の `POST /observability/scores` を活用
2. conversation_id から Langfuse の trace_id へのマッピング機能を追加
3. `conversation_store` に trace_id を保存
4. フィードバック投稿用の新規エンドポイント `POST /chat/feedback` を追加（ラッパー）

**設計ドキュメント**: `design-policy-feedback-requirement-definition.md` で詳細化予定

---

### FR-3: 品質可視化機能

**優先度**: Medium
**対応ユーザーストーリー**: #3

#### 要件詳細

- **FR-3.1**: 要件定義APIの品質メトリクスを可視化すること
- **FR-3.2**: 表示する情報：
  - 平均スコア（requirement_clarity, hypothesis_accuracy 等）
  - 平均対話ターン数（completeness ≥ 0.8 に到達するまで）
  - 完了率（completeness ≥ 0.8 に到達した割合）
  - 平均完了時間
  - モデル使用率（gemini-2.0-flash vs gemini-1.5-pro 等）
  - エラー率
- **FR-3.3**: フィルタ機能を提供すること：
  - 期間指定（last 7 days, last 30 days, custom range）
  - モデル指定

#### 実装方針

1. 新規エンドポイント `GET /observability/requirement-definition-metrics` を追加
2. Langfuse のトレース・スコアデータを集計
3. 会話履歴（conversation_store）から対話ターン数を計算
4. レスポンスは JSON 形式

**設計ドキュメント**: `design-policy-quality-dashboard-requirement-definition.md` で詳細化予定

---

### FR-4: 診断情報取得機能

**優先度**: High
**対応ユーザーストーリー**: #4

#### 要件詳細

- **FR-4.1**: conversation_id を指定して、使用されたプロンプトとLLMレスポンスを取得できること
- **FR-4.2**: 以下の情報を含むこと：
  - システムプロンプト全文
  - 各ターンのユーザープロンプト
  - 各ターンのLLMレスポンス（生データ）
  - 抽出された RequirementState
  - 使用モデル名
  - トークン使用量（input/output）
  - 実行時間
  - エラー情報（存在する場合）
- **FR-4.3**: Langfuse のトレースビューへのリンクを含むこと

#### 実装方針

1. `stream_requirement_clarification()` で Langfuse トレーシングを追加
2. conversation_id と trace_id のマッピングを `conversation_store` に保存
3. 新規エンドポイント `GET /chat/diagnostics/{conversation_id}` を追加
4. Langfuse API を使用してトレース詳細を取得
5. 会話履歴（conversation_store）と結合して返却

**設計ドキュメント**: `design-policy-diagnostic-info-requirement-definition.md` で詳細化予定

---

### FR-5: プロンプト外部管理機能

**優先度**: Medium
**対応ユーザーストーリー**: #5

#### 要件詳細

- **FR-5.1**: 全てのプロンプトを外部ファイル（YAML）で管理すること
- **FR-5.2**: 以下のプロンプトをYAML化すること：
  - `REQUIREMENT_CLARIFICATION_SYSTEM_PROMPT` (requirement_clarification.py)
  - 要件抽出用システムプロンプト (extract_requirement_with_llm)
  - マルチ候補生成プロンプト（FR-1 で新規作成）
- **FR-5.3**: YAMLファイルの変更のみでプロンプトを更新できること（コード変更不要）
- **FR-5.4**: バージョン管理を可能にすること（例: `prompts/v1/`, `prompts/v2/`）

#### 実装方針

1. 新規ディレクトリ: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/prompts/templates/requirement_clarification/`
2. プロンプトをYAML化:
   - `system_prompt.yaml`
   - `extraction_prompt.yaml`
   - `multi_candidate_prompt.yaml`
3. プロンプトローダー関数 `load_requirement_clarification_prompt(prompt_type: str, version: str = "v1")` を実装
4. 環境変数 `REQUIREMENT_CLARIFICATION_PROMPT_VERSION` でバージョンを切り替え

**設計ドキュメント**: `design-policy-prompt-externalization-requirement-definition.md` で詳細化予定

---

### FR-6: ABテスト機能

**優先度**: Low（Phase 2 以降）
**対応ユーザーストーリー**: #6

#### 要件詳細

- **FR-6.1**: 2つ以上のプロンプトバージョンを並行運用できること
- **FR-6.2**: リクエストごとにランダムまたは指定したバージョンを使用すること
- **FR-6.3**: 各バージョンの品質メトリクスを独立して集計できること
- **FR-6.4**: バージョン間の統計的有意差を検定できること（例: t検定）

#### 実装方針

1. `RequirementChatRequest` に `prompt_version: Optional[str]` を追加
2. 未指定時はランダム選択（A/Bテスト）
3. Langfuse の tags に `prompt_version=v1` 等を記録
4. 新規エンドポイント `GET /observability/requirement-definition-ab-test` で比較レポート取得
5. 統計検定機能を実装（scipy.stats.ttest_ind 等）

**設計ドキュメント**: Phase 2 で詳細化予定

---

## 🏗️ 非機能要件

### NFR-1: パフォーマンス

- **NFR-1.1**: 複数候補提示機能は、既存の単一候補生成と比較して2倍以内の実行時間で完了すること
- **NFR-1.2**: SSEストリーミング中の応答遅延は500ms以内であること（初回チャンク）
- **NFR-1.3**: 品質可視化APIのレスポンスタイムは1秒以内であること（データ量が1000会話以下の場合）

### NFR-2: 可用性

- **NFR-2.1**: Langfuse が一時的に利用不可でも、要件定義API本体の動作に影響しないこと（フォールバック機構）
- **NFR-2.2**: 会話履歴は最低24時間保持すること（conversation_store）

### NFR-3: 保守性

- **NFR-3.1**: プロンプトのYAML化により、エンジニア以外でもプロンプト改善が可能であること
- **NFR-3.2**: 全ての新機能は単体テストカバレッジ90%以上を満たすこと

### NFR-4: セキュリティ

- **NFR-4.1**: Langfuse API キーは myVault で管理すること
- **NFR-4.2**: 会話履歴には個人情報を含めないこと（ユーザーIDのみ記録）

---

## 📐 システムアーキテクチャ

### コンポーネント構成図

```
┌─────────────────────────────────────────────────────────────┐
│                    expertAgent                               │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Chat API (chat_endpoints.py)                          │ │
│  │                                                          │ │
│  │  POST /chat/requirement-definition (SSE)               │ │
│  │  ├─ stream_requirement_clarification()                 │ │
│  │  │  ├─ LLM streaming (astream)                        │ │
│  │  │  ├─ extract_requirement_with_llm()                 │ │
│  │  │  └─ SSE events: message, requirement_update,       │ │
│  │  │                 requirements_ready, done            │ │
│  │  │                                                      │ │
│  │  POST /chat/create-job                                 │ │
│  │  └─ Convert RequirementState -> JobGeneratorRequest   │ │
│  │                                                          │ │
│  │  POST /chat/feedback (新規)                            │ │
│  │  └─ conversation_id -> Langfuse score                 │ │
│  │                                                          │ │
│  │  GET /chat/diagnostics/{conversation_id} (新規)        │ │
│  │  └─ conversation_id -> Langfuse trace + 会話履歴      │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Conversation Services                                  │ │
│  │                                                          │ │
│  │  conversation_store.py (会話履歴管理)                  │ │
│  │  ├─ save_message()                                     │ │
│  │  ├─ get_conversation()                                 │ │
│  │  └─ save_trace_id() (新規)                            │ │
│  │                                                          │ │
│  │  llm_service.py (LLM呼び出し)                          │ │
│  │  ├─ stream_requirement_clarification()                 │ │
│  │  └─ non_streaming_clarification()                      │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Prompts (requirement_clarification.py)                │ │
│  │                                                          │ │
│  │  REQUIREMENT_CLARIFICATION_SYSTEM_PROMPT               │ │
│  │  create_requirement_clarification_prompt()             │ │
│  │  extract_requirement_with_llm()                        │ │
│  │                                                          │ │
│  │  → YAML化予定 (FR-5)                                   │ │
│  │    prompts/templates/requirement_clarification/        │ │
│  │    ├─ system_prompt.yaml                               │ │
│  │    ├─ extraction_prompt.yaml                           │ │
│  │    └─ multi_candidate_prompt.yaml                      │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Observability API (observability_endpoints.py)        │ │
│  │                                                          │ │
│  │  GET /observability/traces                             │ │
│  │  GET /observability/traces/{trace_id}                  │ │
│  │  POST /observability/scores (拡張)                     │ │
│  │  GET /observability/requirement-definition-metrics (新)│ │
│  │  GET /observability/requirement-definition-ab-test (新)│ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                         ↓ ↑
                 (Trace / Score)
                         ↓ ↑
┌─────────────────────────────────────────────────────────────┐
│                    Langfuse (Self-hosted)                    │
│                                                               │
│  ・Trace データ管理                                          │
│  ・Score データ管理                                          │
│  ・Web UI (トレース閲覧)                                     │
└─────────────────────────────────────────────────────────────┘
```

### データフロー

#### 1. 要件定義フロー（既存）

```
User
  │
  ├─ POST /v1/chat/requirement-definition
  │  { "conversation_id": "conv_001",
  │    "user_message": "売上データを分析したい",
  │    "context": { "current_requirements": {...}, "previous_messages": [] } }
  │
  v
stream_requirement_clarification()
  │
  ├─ create_requirement_clarification_prompt() (システム + ユーザープロンプト生成)
  ├─ model.astream() (SSEストリーミング)
  │
  v
SSE Events (リアルタイム配信)
  ├─ type='message': {"content": "かしこまりました..."}
  ├─ type='message': {"content": "どのような..."}
  ├─ type='requirement_update': {"requirements": {...}}
  ├─ type='requirements_ready': {} (completeness ≥ 0.8)
  └─ type='done'
  │
  v
extract_requirement_with_llm() (構造化出力で要件抽出)
  │
  v
RequirementState (completeness計算)
  │
  v
User (completeness ≥ 0.8 で「ジョブを作成」ボタン表示)
  │
  ├─ POST /v1/chat/create-job
  │  { "conversation_id": "conv_001", "requirements": {...} }
  │
  v
_convert_requirements_to_job_request()
  │
  v
POST /v1/job-generator (既存API)
  │
  v
Job 作成完了
```

#### 2. 複数候補提示フロー（FR-1: 新規）

```
User
  │
  ├─ POST /v1/chat/requirement-definition
  │  { "conversation_id": "conv_001",
  │    "user_message": "売上データを分析したい",
  │    "context": { "current_requirements": null, "previous_messages": [] },
  │    "enable_multi_candidate": true }  ← 新規パラメータ
  │
  v
stream_requirement_clarification() (拡張)
  │
  ├─ 初回メッセージを検知
  ├─ MULTI_CANDIDATE_GENERATION_PROMPT を使用
  ├─ 2パターンの要件解釈を生成
  │
  v
SSE Events
  ├─ type='message': {"content": "2つの解釈パターンをご提案します..."}
  ├─ type='candidate_selection': {
  │    "candidates": [
  │      { "id": "A", "label": "シンプル型",
  │        "data_source": "CSVファイル",
  │        "process_description": "売上データを月別に集計",
  │        "output_format": "Excelレポート",
  │        "schedule": "毎日",
  │        "completeness": 0.8,
  │        "recommended": true },
  │      { "id": "B", "label": "機能豊富型",
  │        "data_source": "データベース（PostgreSQL）",
  │        "process_description": "売上データを月別・商品別に集計し、トレンド分析",
  │        "output_format": "インタラクティブダッシュボード（Web）",
  │        "schedule": "リアルタイム更新",
  │        "completeness": 0.9,
  │        "recommended": false }
  │    ]
  │  }
  │
  v
User (候補を選択)
  │
  ├─ POST /v1/chat/requirement-definition
  │  { "conversation_id": "conv_001",
  │    "user_message": "パターンAでお願いします",
  │    "context": { "selected_candidate_id": "A", ... } }
  │
  v
stream_requirement_clarification() (選択された候補で継続)
  │
  v
... (以降は通常フロー)
```

#### 3. フィードバック・品質可視化フロー（FR-2, FR-3: 新規）

```
User (会話完了後)
  │
  ├─ POST /v1/chat/feedback
  │  { "conversation_id": "conv_001",
  │    "scores": {
  │      "requirement_clarity": 4,
  │      "hypothesis_accuracy": 5,
  │      "response_naturalness": 3,
  │      "overall_satisfaction": 4
  │    },
  │    "comment": "仮説が的確でした" }
  │
  v
conversation_store.get_trace_id(conversation_id) → trace_id
  │
  v
POST /observability/scores (既存API)
  │  { "trace_id": "...",
  │    "name": "requirement_clarity",
  │    "value": 4,
  │    "comment": "..." }
  │
  v
Langfuse (Score 保存)

---

Admin
  │
  ├─ GET /observability/requirement-definition-metrics?days=30
  │
  v
ObservabilityService (拡張)
  │
  ├─ Langfuse.fetch_traces() (tag='requirement-definition', 過去30日分)
  ├─ Langfuse.fetch_scores() (過去30日分)
  ├─ conversation_store.get_statistics() (対話ターン数など)
  │
  v
データ集計
  │
  ├─ 平均スコア計算
  ├─ 平均対話ターン数計算
  ├─ 完了率計算（completeness ≥ 0.8 到達率）
  ├─ 平均完了時間計算
  ├─ モデル使用率計算
  │
  v
Response (JSON)
  { "average_scores": { "requirement_clarity": 4.2, ... },
    "average_turns": 3.5,
    "completion_rate": 0.87,
    "average_completion_time_seconds": 120,
    "model_usage": { "gemini-2.0-flash": 0.85, "gemini-1.5-pro": 0.15 },
    "error_rate": 0.02
  }
```

---

## 🛠️ 実装計画

### Phase 1: 基盤強化（優先度 High）

#### Milestone 1.1: 診断情報取得機能（FR-4）
- **期間**: 1週間
- **タスク**:
  1. `stream_requirement_clarification()` に Langfuse トレーシング追加
  2. `conversation_store` に `save_trace_id()` / `get_trace_id()` 追加
  3. 新規エンドポイント `GET /chat/diagnostics/{conversation_id}` 実装
  4. 単体テスト・結合テスト作成
- **成果物**:
  - 実装コード
  - テストコード（カバレッジ90%以上）
  - 設計ドキュメント `design-policy-diagnostic-info-requirement-definition.md`

#### Milestone 1.2: フィードバック機能（FR-2）
- **期間**: 1週間
- **タスク**:
  1. 要件定義API固有のスコアタイプ定義
  2. 新規エンドポイント `POST /chat/feedback` 実装（ラッパー）
  3. conversation_id → trace_id マッピング活用
  4. 単体テスト・結合テスト作成
- **成果物**:
  - 実装コード
  - テストコード
  - 設計ドキュメント `design-policy-feedback-requirement-definition.md`

#### Milestone 1.3: 複数候補提示機能（FR-1）
- **期間**: 2週間
- **タスク**:
  1. `RequirementChatRequest` に `enable_multi_candidate: bool` 追加
  2. `MULTI_CANDIDATE_GENERATION_PROMPT` 作成
  3. `stream_requirement_clarification()` を拡張（初回時2パターン生成）
  4. SSE イベント `candidate_selection` 追加
  5. 単体テスト・結合テスト作成
- **成果物**:
  - 実装コード
  - テストコード（カバレッジ90%以上）
  - 設計ドキュメント `design-policy-candidate-selection.md`

### Phase 2: 品質可視化・プロンプト管理（優先度 Medium）

#### Milestone 2.1: 品質可視化機能（FR-3）
- **期間**: 2週間
- **タスク**:
  1. 新規エンドポイント `GET /observability/requirement-definition-metrics` 実装
  2. Langfuse データ + conversation_store データの集計ロジック実装
  3. 単体テスト・結合テスト作成
- **成果物**:
  - 実装コード
  - テストコード
  - 設計ドキュメント `design-policy-quality-dashboard-requirement-definition.md`

#### Milestone 2.2: プロンプト外部管理機能（FR-5）
- **期間**: 2週間
- **タスク**:
  1. プロンプトテンプレート用ディレクトリ作成
  2. 全プロンプトのYAML化
  3. プロンプトローダー `load_requirement_clarification_prompt()` 実装
  4. 環境変数 `REQUIREMENT_CLARIFICATION_PROMPT_VERSION` サポート
  5. 単体テスト・結合テスト作成
- **成果物**:
  - YAMLファイル群
  - 実装コード
  - テストコード
  - 設計ドキュメント `design-policy-prompt-externalization-requirement-definition.md`

### Phase 3: ABテスト機能（優先度 Low）

#### Milestone 3.1: ABテスト機能（FR-6）
- **期間**: 3週間
- **タスク**:
  1. `RequirementChatRequest` に `prompt_version: Optional[str]` 追加
  2. 未指定時のランダム選択機能実装
  3. Langfuse tags に `prompt_version` 記録
  4. 新規エンドポイント `GET /observability/requirement-definition-ab-test` 実装
  5. 統計検定機能実装（scipy.stats.ttest_ind 等）
  6. 単体テスト・結合テスト作成
- **成果物**:
  - 実装コード
  - テストコード
  - 設計ドキュメント `design-policy-ab-testing-requirement-definition.md`

---

## ✅ 受入基準

### Phase 1

- [ ] **FR-1**: 複数候補提示機能が動作し、2パターンの要件解釈が返却される
- [ ] **FR-1**: ユーザーが候補を選択でき、後続対話が継続される
- [ ] **FR-2**: 要件定義API固有のスコアタイプ（4種類）でフィードバックを投稿できる
- [ ] **FR-2**: conversation_id から Langfuse score が正しく紐付けられる
- [ ] **FR-4**: `GET /chat/diagnostics/{conversation_id}` でプロンプト・LLMレスポンスが取得できる
- [ ] **FR-4**: Langfuse トレースビューへのリンクが正しく生成される
- [ ] 全ての新機能で単体テストカバレッジ90%以上を達成
- [ ] 全ての新機能で結合テストが作成され、成功する
- [ ] 静的解析（Ruff, MyPy）でエラーが0件

### Phase 2

- [ ] **FR-3**: `GET /observability/requirement-definition-metrics` で品質メトリクスが取得できる
- [ ] **FR-3**: 平均対話ターン数、完了率、平均完了時間が正しく計算される
- [ ] **FR-5**: 全プロンプトがYAMLファイルで管理されている
- [ ] **FR-5**: 環境変数 `REQUIREMENT_CLARIFICATION_PROMPT_VERSION` でバージョン切り替えができる
- [ ] 全ての新機能で単体テストカバレッジ90%以上を達成
- [ ] 静的解析（Ruff, MyPy）でエラーが0件

### Phase 3

- [ ] **FR-6**: 複数のプロンプトバージョンを並行運用できる
- [ ] **FR-6**: `GET /observability/requirement-definition-ab-test` でバージョン間比較レポートが取得できる
- [ ] **FR-6**: 統計検定（t検定）が正しく実行される
- [ ] 全ての新機能で単体テストカバレッジ90%以上を達成
- [ ] 静的解析（Ruff, MyPy）でエラーが0件

---

## 📚 参照ドキュメント

### 既存ドキュメント

- `CLAUDE.md`: 開発フロー・品質基準
- `docs/claude/04-quality-standards.md`: テストカバレッジ要件
- `expertAgent/README.md`: expertAgent の概要
- `expertAgent/app/api/v1/chat_endpoints.py`: 要件定義API実装

### 関連Issue

- Issue #113: Langfuse Self-hosted統合（既に実装済み）
- Issue #152: 本Issue（要件定義エージェントへのMLOps導入）

### 外部リンク

- [Langfuse Documentation](https://langfuse.com/docs)
- [LangChain Streaming](https://python.langchain.com/docs/how_to/streaming)
- [Server-Sent Events (SSE) Specification](https://html.spec.whatwg.org/multipage/server-sent-events.html)

---

## 🔄 変更履歴

| 日付       | バージョン | 変更内容                                    | 担当者 |
|------------|------------|---------------------------------------------|--------|
| 2025-11-11 | 1.0        | 初版作成                                    | Claude |
| 2025-11-11 | 1.1        | 対象を `/requirement-definition` API に修正 | Claude |
| 2025-11-11 | 1.2        | デフォルトモデルを gemini-2.5-flash に変更  | Claude |

---

## 📋 補足事項

### 技術的制約

- Langfuse は self-hosted 環境で運用（Issue #113 で構築済み）
- LLM は Gemini モデルを使用
  - **要件定義API**: gemini-2.5-flash（デフォルト）※本Issue #152 で変更
  - その他: gemini-2.0-flash, gemini-1.5-pro 等
- 会話履歴は現在インメモリ（conversation_store）で管理（将来的にDBへ移行検討）
- SSE ストリーミングを使用（HTTP/2 必須ではない）

### 将来的な拡張

- 会話履歴の永続化（Redis または PostgreSQL）
- myAgentDesk での Web UI 実装（候補選択、フィードバック投稿）
- プロンプト自動最適化機能（DSPy 等の導入検討）
- 多言語対応（英語プロンプトの作成）

---

**END OF DOCUMENT**
