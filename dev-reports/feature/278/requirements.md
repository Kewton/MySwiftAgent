# 要件定義書: Job/Workflow GeneratorへのLangfuseトレース統合

> Issue: [#278](https://github.com/kewton/MySwiftAgent/issues/278)
> 作成日: 2025-12-13
> ステータス: 要件定義完了

---

## 現状調査サマリ

### 対象プロジェクト
- **プロジェクト名**: expertAgent
- **技術スタック**: FastAPI + LangGraph + LangChain
- **関連モジュール**:
  - `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/` - Job Task Generator
  - `expertAgent/aiagent/langgraph/workflowGeneratorAgents/` - Workflow Generator
  - `expertAgent/app/services/langfuse_service.py` - Langfuse統合サービス

### 既存の類似機能

| 機能 | 場所 | Langfuse統合状況 |
|------|------|-----------------|
| **LangfuseService** | `langfuse_service.py` | ✅ 実装済み（CallbackHandler生成、trace_id抽出） |
| **Requirement Clarification Chat** | `llm_service.py:52-121` | ✅ CallbackHandler使用中 |
| **Expert AI Agent Service** | `ai_agent_service.py:52-82` | ✅ 直接Langfuse API使用 |
| **Job Task Generator** | `llm_invocation.py` | ❌ CallbackHandler未使用 |
| **Workflow Generator** | `generator.py` | ❌ CallbackHandler未使用 |

### 使用されている設計パターン

| パターン | 使用箇所 | 目的 |
|---------|---------|------|
| **Singleton** | `LangfuseService` | アプリケーション全体で1クライアント共有 |
| **Callback Pattern** | LangChain `RunnableConfig` | LLM呼び出し時のトレース注入 |
| **Fallback Pattern** | `create_llm_with_fallback()` | プライマリLLM失敗時の代替 |
| **Structured Output** | `with_structured_output()` | Pydanticモデルによる応答構造化 |

### 参照したドキュメント

| ドキュメント | 関連内容 |
|-------------|---------|
| `expertAgent/docs/API_REFERENCE.md` | Job Generator / Workflow Generator API仕様 |
| `docs/spec/job-generation-workflow.md` | LangGraphエージェント設計 |
| [Langfuse LangChain Integration](https://langfuse.com/docs/integrations/langchain/tracing) | CallbackHandler使用方法 |

### 制約事項

1. **Langfuse無効時の動作保証**: APIキー未設定時でも正常動作必須
2. **非同期処理**: すべてのLLM呼び出しは`ainvoke()`による非同期
3. **構造化出力**: `with_structured_output()`ラッパーを通じたCallback伝播
4. **既存パフォーマンストラッキング**: `ModelPerformanceTracker`との共存

---

## ユーザーストーリー

### 主要ストーリー
```
As a 開発者/運用担当者
I want to Job/Workflow Generatorの全LLM呼び出しをLangfuseでトレースしたい
So that AIエージェントの動作を可視化し、品質改善・デバッグ・コスト分析ができる
```

### サブストーリー
```
As a 開発者
I want to trace_idをAPI応答で受け取りたい
So that 特定のジョブ生成をLangfuse UIで追跡できる

As a 運用担当者
I want to Langfuse無効時も既存機能が動作してほしい
So that APIキー未設定の環境でもシステムが利用できる

As a 開発者
I want to 各ノード（評価、タスク分割、検証等）のLLM呼び出しを個別にトレースしたい
So that ボトルネックや問題箇所を特定できる
```

---

## 受入条件（Acceptance Criteria）

### AC1: Job Task Generator のトレース統合
- **Given**: Job Task Generatorが起動される
- **When**: LLM呼び出し（`invoke_structured_llm()`）が実行される
- **Then**:
  - Langfuse CallbackHandlerが`ainvoke()`に渡される
  - LLM呼び出しがLangfuseにトレースとして記録される
  - `trace_id`が抽出可能になる

### AC2: Workflow Generator のトレース統合
- **Given**: Workflow Generatorが起動される
- **When**: ワークフロー生成LLM呼び出しが実行される
- **Then**:
  - Langfuse CallbackHandlerが使用される
  - 生成されたワークフローと`trace_id`が紐付けられる

### AC3: trace_idのAPI応答への追加
- **Given**: `/v1/job-generator`または`/v1/workflow-generator`を呼び出す
- **When**: ジョブ/ワークフロー生成が完了する
- **Then**:
  - API応答に`langfuse_trace_id`フィールドが含まれる（Langfuse有効時）
  - Langfuse無効時は`langfuse_trace_id: null`

### AC4: Langfuse無効時の正常動作
- **Given**: Langfuse APIキーが未設定
- **When**: Job/Workflow Generatorを実行する
- **Then**:
  - 既存の全機能が正常に動作する
  - エラーやワーニングが発生しない
  - `langfuse_trace_id`は`null`で返却される

### AC5: 既存テストの維持
- **Given**: 既存の単体テスト・結合テストスイート
- **When**: 全テストを実行する
- **Then**:
  - すべてのテストがパスする
  - 新規テスト（Langfuse統合）が追加される

---

## 機能要件

### Must Have（必須）

| ID | 機能 | 詳細 |
|----|------|------|
| F1 | `invoke_structured_llm()`のCallback対応 | オプショナルなcallbacks引数追加、`ainvoke()`へのconfig渡し |
| F2 | trace_id抽出・返却 | `StructuredCallResult`に`trace_id`フィールド追加 |
| F3 | Job Generator APIでのtrace_id返却 | `JobGeneratorResponse`に`langfuse_trace_id`追加 |
| F4 | Workflow Generator APIでのtrace_id返却 | `WorkflowGeneratorResponse`に`langfuse_trace_id`追加 |
| F5 | Langfuse無効時のフォールバック | handler=Noneの場合、callbacksなしで動作 |

### Nice to Have（推奨）

| ID | 機能 | 詳細 |
|----|------|------|
| F6 | ノード別トレース名 | 各LangGraphノード（evaluator, task_breakdown等）に識別名を付与 |
| F7 | メタデータ付与 | model_name, max_tokens等のパラメータをトレースメタデータに記録 |
| F8 | エラートレース | LLM呼び出し失敗時もエラー情報をトレースに記録 |

### Future Enhancement（将来拡張）

| ID | 機能 |
|----|------|
| F9 | ユーザーフィードバック統合（trace_idによるスコアリング） |
| F10 | コスト分析ダッシュボード連携 |
| F11 | A/Bテスト用のトレースタグ付け |

---

## 非機能要件

### パフォーマンス要件
- Langfuse CallbackHandler追加によるオーバーヘッド: < 50ms
- トレース送信は非同期（ユーザー応答をブロックしない）
- 既存の`ModelPerformanceTracker`との共存（二重計測許容）

### セキュリティ要件
- Langfuse APIキーはmyVault経由で管理（平文保存禁止）
- trace_idはUUID形式（推測困難）
- LLM入出力データはLangfuseサーバーに送信されることをユーザーに明示

### ユーザビリティ要件
- Langfuse無効時は設定不要で動作
- trace_idはオプショナルフィールドとしてAPI応答に含める
- ドキュメントにLangfuse統合の有効化手順を記載

### 互換性要件
- 既存のAPI応答スキーマに追加フィールドのみ（破壊的変更なし）
- 既存のテストスイートがすべてパス
- Python 3.11+互換

---

## 技術的制約

### 使用する技術スタック

| 領域 | 技術 |
|------|------|
| フレームワーク | FastAPI |
| LLMオーケストレーション | LangGraph, LangChain |
| Observability | Langfuse Self-hosted |
| シークレット管理 | myVault |
| 非同期処理 | asyncio, httpx |

### 既存システムとの連携

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  API Endpoint    │────▶│  LangGraph Agent │────▶│     LLM API     │
│  (FastAPI)       │     │  (Job/Workflow)  │     │  (Claude/GPT)   │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │    Langfuse     │
                        │  (Self-hosted)  │
                        └─────────────────┘
```

### 変更対象ファイル

| ファイル | 変更内容 |
|---------|---------|
| `aiagent/langgraph/jobTaskGeneratorAgents/utils/llm_invocation.py` | callbacks引数追加、trace_id抽出 |
| `aiagent/langgraph/jobTaskGeneratorAgents/utils/llm_factory.py` | 必要に応じてcallback対応 |
| `aiagent/langgraph/workflowGeneratorAgents/nodes/generator.py` | CallbackHandler使用 |
| `app/api/v1/job_generator_endpoints.py` | langfuse_trace_id返却 |
| `app/api/v1/workflow_generator_endpoints.py` | langfuse_trace_id返却 |
| `app/schemas/job_generator.py` | `langfuse_trace_id`フィールド追加 |
| `app/schemas/workflow_generator.py` | `langfuse_trace_id`フィールド追加 |

### コード変更例

#### `invoke_structured_llm()` の変更

```python
# Before
async def invoke_structured_llm(
    messages: list,
    response_model: type[T],
    context_label: str,
    ...
) -> StructuredCallResult[T]:
    ...
    structured_response = await structured_model.ainvoke(messages)
    ...

# After
from langfuse.langchain import CallbackHandler

async def invoke_structured_llm(
    messages: list,
    response_model: type[T],
    context_label: str,
    langfuse_handler: CallbackHandler | None = None,  # 追加
    ...
) -> StructuredCallResult[T]:
    ...
    config = {"callbacks": [langfuse_handler]} if langfuse_handler else {}
    structured_response = await structured_model.ainvoke(messages, config=config)

    # trace_id抽出
    trace_id = LangfuseService.extract_trace_id(langfuse_handler)
    ...
```

#### `StructuredCallResult` の変更

```python
@dataclass
class StructuredCallResult(Generic[T]):
    response: T | None
    error_message: str | None
    model_used: str
    performance_metrics: PerformanceMetrics | None
    trace_id: str | None = None  # 追加
```

---

## リスクと対策

### 技術的リスク

| リスク | 影響度 | 発生確率 | 対策 |
|--------|--------|---------|------|
| Langfuse SDK互換性問題 | 中 | 低 | SDKバージョン固定、E2Eテスト追加 |
| CallbackHandler伝播失敗（構造化出力） | 中 | 中 | 単体テストで伝播確認 |
| trace_id取得タイミング不整合 | 低 | 中 | `ainvoke()`完了後に即抽出 |
| 既存パフォーマンストラッキングとの競合 | 低 | 低 | 両方独立動作、二重計測許容 |

### ビジネスリスク

| リスク | 影響度 | 対策 |
|--------|--------|------|
| LLM入出力がLangfuseに送信される | 低 | ドキュメントに明示、Self-hosted推奨 |
| Langfuse障害時の影響 | 低 | フェイルオープン設計（Langfuse障害でもメイン機能継続） |

---

## 影響範囲

### 変更対象ファイル

| ファイル | 変更内容 |
|---------|---------|
| `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/utils/llm_invocation.py` | callbacks引数追加 |
| `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/*.py` | CallbackHandler渡し |
| `expertAgent/aiagent/langgraph/workflowGeneratorAgents/nodes/generator.py` | CallbackHandler使用 |
| `expertAgent/app/api/v1/job_generator_endpoints.py` | trace_id返却 |
| `expertAgent/app/api/v1/workflow_generator_endpoints.py` | trace_id返却 |
| `expertAgent/app/schemas/job_generator.py` | langfuse_trace_id追加 |
| `expertAgent/app/schemas/workflow_generator.py` | langfuse_trace_id追加 |

### テスト追加

| テスト種別 | 対象 | 件数（目安） |
|-----------|------|--------------|
| 単体テスト | `invoke_structured_llm()` callback注入 | 5件 |
| 単体テスト | trace_id抽出 | 3件 |
| 結合テスト | API応答のtrace_id確認 | 4件 |
| 結合テスト | Langfuse無効時の動作 | 2件 |

---

## 関連Issue/PR

- #194 (Langfuse Trace not found - 根本原因調査で発見)
- #113 (Langfuse Self-hosted統合)
- #263 (CallbackHandler にAPIキーを明示的に渡す対応)

---

## 推奨アプローチ

### Phase 1: `invoke_structured_llm()` のCallback対応（F1, F2）
1. `langfuse_handler`引数を追加
2. `ainvoke()`にconfig渡し
3. `StructuredCallResult`にtrace_id追加
4. 単体テスト追加

### Phase 2: Job Task Generator統合（F3）
1. 各ノードでCallbackHandler取得・渡し
2. `JobGeneratorResponse`にtrace_id追加
3. エンドポイントでtrace_id返却

### Phase 3: Workflow Generator統合（F4）
1. `generator_node()`でCallbackHandler使用
2. `WorkflowGeneratorResponse`にtrace_id追加

### Phase 4: ドキュメント・テスト整備（F5, F6）
1. Langfuse無効時のフォールバックテスト
2. E2Eテスト追加
3. ドキュメント更新

---

## 参照ドキュメント

- [expertAgent API Reference](../../../expertAgent/docs/API_REFERENCE.md)
- [Job Generation Workflow Spec](../../../docs/spec/job-generation-workflow.md)
- [Langfuse LangChain Integration](https://langfuse.com/docs/integrations/langchain/tracing)
- [Issue #194 Design Documents](../issue/194/)
