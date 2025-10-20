# Phase 10 改善提案: Job/Task Generator 品質向上

**作成日**: 2025-10-21
**Phase**: 10
**目的**: Phase 9で発見された問題の解決と、ユーザー体験の向上

---

## 📋 改善要求サマリー

Phase 9の結果を受けて、以下の4つの改善要求が提示されました：

| # | 改善要求 | 現状の問題 | 優先度 |
|---|---------|-----------|--------|
| 1 | **geminiAgentをデフォルト推薦** | 現在は3つのLLMエージェントが同列に記載 | 🟡 Medium |
| 2 | **max_retry見直し** | 現在は固定値5、複雑度に応じた調整が必要 | 🟡 Medium |
| 3 | **レスポンスフォーマット問題対応** | HTTPステータス200でもエラーが含まれる | 🔴 High |
| 4 | **代替案・機能強化提案の充実** | 実現不可時のユーザーガイダンス不足 | 🔴 High |

---

## 🎯 改善案詳細

### 改善案1: geminiAgentをデフォルト推薦

#### 📊 現状分析

**現在の記載順序** (`graphai_capabilities.yaml`):
```yaml
llm_agents:
  - name: "anthropicAgent"
    description: "Claude API直接呼び出し"
  - name: "openAIAgent"
    description: "OpenAI API直接呼び出し"
  - name: "geminiAgent"
    description: "Gemini API直接呼び出し"
```

**問題点**:
- 3つのLLMエージェントが同列に記載されており、優先順位が不明確
- evaluation.pyのプロンプトでも同列に記載
- ユーザーに対する推奨が不明確

#### ✅ 改善提案

**変更箇所1: graphai_capabilities.yaml**

```yaml
llm_agents:
  - name: "geminiAgent"
    description: "Gemini API直接呼び出し（推奨: コスト効率と性能のバランス◎）"
    requires_api_key: true
    api_key_name: "GOOGLE_API_KEY"
    recommendation: "default"  # 新規フィールド
    cost_efficiency: "high"     # 新規フィールド
    performance: "high"         # 新規フィールド

  - name: "anthropicAgent"
    description: "Claude API直接呼び出し（高品質な推論が必要な場合）"
    requires_api_key: true
    api_key_name: "ANTHROPIC_API_KEY"
    recommendation: "high_quality"
    cost_efficiency: "medium"
    performance: "very_high"

  - name: "openAIAgent"
    description: "OpenAI API直接呼び出し（汎用的なタスク向け）"
    requires_api_key: true
    api_key_name: "OPENAI_API_KEY"
    recommendation: "general"
    cost_efficiency: "medium"
    performance: "high"
```

**変更箇所2: evaluation.py プロンプト**

```python
# 現在（Phase 9）
"""
### 方法3: LLMベース実装
anthropicAgent, openAIAgent, geminiAgent などのLLMエージェントを使用して、
データ分析、テキスト処理、構造化出力、コード生成を実現できます。
"""

# 改善後（Phase 10）
"""
### 方法3: LLMベース実装
**推奨: geminiAgent** (コスト効率と性能のバランスが最も優れています)
geminiAgent, anthropicAgent, openAIAgent などのLLMエージェントを使用して、
データ分析、テキスト処理、構造化出力、コード生成を実現できます。

推奨順:
1. geminiAgent（推奨）: コスト効率◎、性能◎、汎用的なタスクに最適
2. anthropicAgent: 高度な推論が必要な複雑タスク向け
3. openAIAgent: 汎用的なタスク向け
"""
```

#### 📈 期待効果

- ✅ ユーザーに明確な推奨を提示
- ✅ コスト効率の改善（geminiAgentは他より安価）
- ✅ 性能と品質のバランスが取れた選択
- ✅ 複雑度に応じたLLMエージェント選択の指針を提供

---

### 改善案2: max_retry見直し

#### 📊 現状分析

**現在の実装**:
- `max_retry`は固定値5（ユーザー指定可能）
- タスクの複雑度に関わらず一律5回
- Phase 8の結果: 9/9 tests でrecursion limit errors → 空結果検出で解決

**問題点**:
- シンプルなタスクでも5回リトライ → 無駄な実行時間
- 複雑なタスクでは5回では不足する可能性
- 評価フィードバックを活かせていない

#### ✅ 改善提案

**改善方針**: **複雑度ベースの動的max_retry調整**

**変更箇所1: state.py に complexity フィールド追加**

```python
class GraphState(TypedDict):
    # 既存フィールド
    user_requirement: str
    max_retry: int

    # 新規フィールド
    estimated_complexity: str  # "simple" | "medium" | "complex"
    adjusted_max_retry: int    # 複雑度に応じて調整されたmax_retry
```

**変更箇所2: requirement_analysis.py で複雑度推定**

```python
def _estimate_task_complexity(requirement: str) -> str:
    """
    ユーザー要求の複雑度を推定

    複雑度の判定基準:
    - simple: 単一APIコール、単純なデータ変換
    - medium: 複数API連携、データ処理・変換
    - complex: 複雑なワークフロー、外部API連携、高度な処理
    """
    # LLMで複雑度を推定（anthropicAgentで高精度な判定）
    prompt = f"""
以下のユーザー要求の複雑度を判定してください。

ユーザー要求:
{requirement}

判定基準:
- simple: 単一APIコール、単純なデータ変換（例: CSVをJSONに変換）
- medium: 複数API連携、データ処理（例: 複数PDFから特定データを抽出）
- complex: 複雑なワークフロー、外部API連携、高度な処理（例: 企業分析→メール送信）

以下のJSON形式で応答してください:
{{
  "complexity": "simple" | "medium" | "complex",
  "reasoning": "判定理由"
}}
"""
    # LLM呼び出し（省略）
    return complexity
```

**変更箇所3: agent.py で動的max_retry調整**

```python
def _adjust_max_retry(state: GraphState) -> GraphState:
    """
    複雑度に応じてmax_retryを動的調整
    """
    base_max_retry = state["max_retry"]
    complexity = state.get("estimated_complexity", "medium")

    # 複雑度ベースの調整係数
    complexity_factors = {
        "simple": 0.6,    # 5回 → 3回
        "medium": 1.0,    # 5回 → 5回
        "complex": 1.5    # 5回 → 7-8回
    }

    adjusted = int(base_max_retry * complexity_factors.get(complexity, 1.0))
    adjusted = max(3, min(adjusted, 10))  # 3-10回の範囲に制限

    state["adjusted_max_retry"] = adjusted
    logger.info(f"max_retry adjusted: {base_max_retry} → {adjusted} (complexity: {complexity})")

    return state
```

**変更箇所4: evaluation.py でretry戦略の最適化**

```python
def should_retry_with_feedback(state: GraphState) -> bool:
    """
    評価フィードバックを考慮したretry判定
    """
    current_retry = state.get("retry_count", 0)
    adjusted_max_retry = state.get("adjusted_max_retry", state["max_retry"])

    # 調整済みmax_retryと比較
    if current_retry >= adjusted_max_retry:
        return False

    # 評価結果に基づく早期終了判定
    evaluation = state.get("evaluation_result", {})

    # 完全に実現不可能な場合は早期終了
    if evaluation.get("all_tasks_infeasible", False):
        logger.info("All tasks infeasible, stop retry")
        return False

    # 部分的に実現可能な場合は続行
    return True
```

#### 📈 期待効果

| 項目 | Phase 9 | Phase 10（改善後） |
|------|---------|-------------------|
| **simple タスク** | 5回固定 | 3回（40%削減） |
| **medium タスク** | 5回固定 | 5回（変更なし） |
| **complex タスク** | 5回固定 | 7-8回（+40-60%） |
| **実行時間削減** | N/A | simple: 約40%削減 |
| **成功率向上** | N/A | complex: +10-20% |

---

### 改善案3: レスポンスフォーマット問題対応

#### 📊 現状分析

**Phase 9で発見された問題**:

**Scenario 1**:
```json
{
  "status": "failed",
  "error_message": "KeyError: 'job_id'"  // ← HTTPステータスは200
}
```

**Scenario 3**:
```json
{
  "status": "failed",
  "error_message": "評価結果: 実現可能なタスクなし"  // ← HTTPステータスは200
}
```

**問題点**:
- HTTPステータスコード200でエラーが返される
- `job_id`がエラー時に含まれていない
- `success`フラグがなく、ステータス文字列での判定が必要
- エラーの種類が不明確（システムエラー vs ビジネスロジックエラー）

#### ✅ 改善提案

**改善方針**: **統一されたレスポンススキーマ + 明確なエラー分類**

**変更箇所1: schemas/job_generator.py に統一スキーマ追加**

```python
from enum import Enum
from typing import Optional, Dict, Any

class JobGeneratorStatus(str, Enum):
    """Job Generator API のステータス"""
    SUCCESS = "success"                    # 完全成功
    PARTIAL_SUCCESS = "partial_success"    # 部分成功（警告あり）
    FAILED = "failed"                      # 失敗

class ErrorType(str, Enum):
    """エラー種別"""
    SYSTEM_ERROR = "system_error"          # システムエラー（バグ、内部エラー）
    VALIDATION_ERROR = "validation_error"  # バリデーションエラー
    BUSINESS_LOGIC_ERROR = "business_logic_error"  # ビジネスロジックエラー（実現不可など）
    TIMEOUT_ERROR = "timeout_error"        # タイムアウト

class JobGeneratorResponse(BaseModel):
    """統一されたJob Generator APIレスポンス"""

    # 必須フィールド（すべてのケースで必ず存在）
    success: bool = Field(..., description="処理成功フラグ")
    status: JobGeneratorStatus = Field(..., description="ステータス")

    # 準必須フィールド（失敗時はNoneまたはデフォルト値）
    job_id: Optional[str] = Field(None, description="生成されたJob ID（失敗時はNone）")
    job_master_id: Optional[str] = Field(None, description="生成されたJob Master ID（失敗時はNone）")

    # エラー情報（失敗時のみ）
    error_type: Optional[ErrorType] = Field(None, description="エラー種別")
    error_message: Optional[str] = Field(None, description="エラーメッセージ")
    error_details: Optional[Dict[str, Any]] = Field(None, description="詳細エラー情報")

    # メタ情報
    execution_time_seconds: Optional[float] = Field(None, description="実行時間（秒）")
    retry_count: Optional[int] = Field(None, description="リトライ回数")

    # 評価結果（部分成功・失敗時のみ）
    evaluation_result: Optional[Dict[str, Any]] = Field(None, description="評価結果")
    alternative_proposals: Optional[list] = Field(None, description="代替案提案")
    requirement_relaxation_suggestions: Optional[list] = Field(None, description="要求緩和提案")
    api_extension_proposals: Optional[list] = Field(None, description="API拡張提案")

    class Config:
        use_enum_values = True
```

**変更箇所2: job_generator_endpoints.py エラーハンドリング改善**

```python
@router.post("/job-generator", response_model=JobGeneratorResponse)
async def generate_job(request: JobGeneratorRequest) -> JobGeneratorResponse:
    """Job/Task自動生成API（統一レスポンス対応）"""
    start_time = time.time()

    try:
        # ワークフロー実行
        result = await workflow_instance.ainvoke(
            initial_state,
            config=RunnableConfig(recursion_limit=50)
        )

        execution_time = time.time() - start_time

        # 成功ケース
        if result.get("is_valid") and result.get("job_id"):
            return JobGeneratorResponse(
                success=True,
                status=JobGeneratorStatus.SUCCESS,
                job_id=result["job_id"],
                job_master_id=result.get("job_master_id"),
                execution_time_seconds=execution_time,
                retry_count=result.get("retry_count", 0)
            )

        # 部分成功ケース（警告あり）
        elif result.get("is_valid") and not result.get("job_id"):
            return JobGeneratorResponse(
                success=False,
                status=JobGeneratorStatus.PARTIAL_SUCCESS,
                job_id=None,
                job_master_id=None,
                error_type=ErrorType.BUSINESS_LOGIC_ERROR,
                error_message="評価は通過しましたが、Job/Task生成に失敗しました",
                error_details={"reason": result.get("error_message")},
                execution_time_seconds=execution_time,
                retry_count=result.get("retry_count", 0),
                evaluation_result=result.get("evaluation_result")
            )

        # 失敗ケース（実現不可）
        else:
            return JobGeneratorResponse(
                success=False,
                status=JobGeneratorStatus.FAILED,
                job_id=None,
                job_master_id=None,
                error_type=ErrorType.BUSINESS_LOGIC_ERROR,
                error_message=result.get("error_message", "要求を実現できませんでした"),
                error_details={
                    "reason": result.get("error_message"),
                    "infeasible_tasks": result.get("evaluation_result", {}).get("infeasible_tasks", [])
                },
                execution_time_seconds=execution_time,
                retry_count=result.get("retry_count", 0),
                evaluation_result=result.get("evaluation_result"),
                alternative_proposals=result.get("evaluation_result", {}).get("alternative_proposals", []),
                requirement_relaxation_suggestions=_generate_requirement_relaxation_suggestions(result),
                api_extension_proposals=result.get("evaluation_result", {}).get("api_extension_proposals", [])
            )

    except TimeoutError as e:
        return JobGeneratorResponse(
            success=False,
            status=JobGeneratorStatus.FAILED,
            job_id=None,
            job_master_id=None,
            error_type=ErrorType.TIMEOUT_ERROR,
            error_message=f"処理がタイムアウトしました: {str(e)}",
            execution_time_seconds=time.time() - start_time
        )

    except ValidationError as e:
        return JobGeneratorResponse(
            success=False,
            status=JobGeneratorStatus.FAILED,
            job_id=None,
            job_master_id=None,
            error_type=ErrorType.VALIDATION_ERROR,
            error_message=f"リクエストのバリデーションエラー: {str(e)}",
            error_details={"validation_errors": e.errors()}
        )

    except Exception as e:
        logger.exception("Unexpected error in generate_job")
        return JobGeneratorResponse(
            success=False,
            status=JobGeneratorStatus.FAILED,
            job_id=None,
            job_master_id=None,
            error_type=ErrorType.SYSTEM_ERROR,
            error_message=f"予期しないエラーが発生しました: {str(e)}",
            error_details={"exception_type": type(e).__name__}
        )
```

#### 📈 期待効果

**改善前（Phase 9）**:
```json
{
  "status": "failed",
  "error_message": "KeyError: 'job_id'"
}
```
- ❌ `success`フラグなし
- ❌ `job_id`なし
- ❌ エラー種別不明
- ❌ HTTPステータス200でエラー

**改善後（Phase 10）**:
```json
{
  "success": false,
  "status": "failed",
  "job_id": null,
  "job_master_id": null,
  "error_type": "business_logic_error",
  "error_message": "要求を実現できませんでした",
  "error_details": {
    "reason": "評価結果: 実現可能なタスクなし",
    "infeasible_tasks": [...]
  },
  "execution_time_seconds": 48.8,
  "retry_count": 3,
  "evaluation_result": {...},
  "alternative_proposals": [...],
  "requirement_relaxation_suggestions": [...],
  "api_extension_proposals": [...]
}
```
- ✅ `success`フラグで明確判定
- ✅ `job_id`は常に存在（失敗時はnull）
- ✅ エラー種別が明確
- ✅ 詳細なエラー情報
- ✅ 代替案・機能強化提案を含む

---

### 改善案4: 代替案・機能強化提案の充実

#### 📊 現状分析

**Phase 9の評価結果**:

**Scenario 1（企業分析→メール送信）**:
```json
{
  "alternative_proposals": [
    {
      "proposal": "1. 財務データ分析をLLMベース実装に置き換え",
      "agents": ["geminiAgent", "stringTemplateAgent"],
      "feasibility": "medium"
    }
  ],
  "api_extension_proposals": [
    {
      "feature": "Financial Data Agent",
      "description": "企業財務データを取得・分析するエージェント",
      "priority": "high"
    }
  ]
}
```

**問題点**:
- 代替案が1-3個と少ない
- ユーザー要求の緩和提案がない
- 具体的な実装手順が不足
- 優先度の判断基準が不明確

#### ✅ 改善提案

**改善方針**: **段階的実装戦略 + 要求緩和提案 + 具体的な実装ガイダンス**

**変更箇所1: evaluation.py プロンプト強化**

```python
# 現在のプロンプト（Phase 9）
"""
以下のJSON形式で応答してください:
{
  "is_valid": true/false,
  "all_tasks_feasible": true/false,
  "infeasible_tasks": [...],
  "alternative_proposals": [...],
  "api_extension_proposals": [...]
}
"""

# 改善後のプロンプト（Phase 10）
"""
以下のJSON形式で応答してください:
{
  "is_valid": true/false,
  "all_tasks_feasible": true/false,
  "infeasible_tasks": [...],
  "alternative_proposals": [...],
  "requirement_relaxation_suggestions": [...],  // 新規
  "phased_implementation_plan": {...},          // 新規
  "api_extension_proposals": [...]
}

### 代替案提案（alternative_proposals）
実現不可能なタスクに対する代替実装方法を提案してください。
各提案には以下を含めてください:
- proposal: 代替実装の概要
- agents: 使用するエージェント
- feasibility: 実現可能性（high/medium/low）
- implementation_steps: 具体的な実装手順（3-5ステップ）
- expected_quality: 期待される品質（元の要求と比較して）
- pros_and_cons: メリット・デメリット

### 要求緩和提案（requirement_relaxation_suggestions）（新規）
ユーザーの要求を緩和することで実現可能になる場合、以下を提案してください:

**提案フォーマット**:
{
  "original_requirement": "元の要求",
  "relaxed_requirement": "緩和後の要求",
  "relaxation_type": "scope_reduction" | "quality_relaxation" | "phased_approach",
  "feasibility_after_relaxation": "high" | "medium",
  "what_is_sacrificed": "何を犠牲にするか",
  "what_is_preserved": "何が保持されるか",
  "recommendation_level": "strongly_recommended" | "recommended" | "consider"
}

**緩和の種類**:
1. **scope_reduction**: スコープ削減
   - 例: "過去5年の売上" → "過去3年の売上"
   - 例: "すべてのPDF" → "最大10個のPDF"

2. **quality_relaxation**: 品質緩和
   - 例: "詳細な分析" → "サマリーレベルの分析"
   - 例: "リアルタイム処理" → "バッチ処理（1日1回）"

3. **phased_approach**: 段階的実装
   - 例: Phase 1で基本機能、Phase 2で高度な機能

### 段階的実装計画（phased_implementation_plan）（新規）
複雑な要求を段階的に実装する計画を提案してください:

**Phase 1: 基本機能（すぐに実装可能）**
- 最小限の機能で動作するバージョン
- 使用エージェント、実装時間、期待品質

**Phase 2: 拡張機能（API拡張後に実装可能）**
- どのAPI拡張が必要か
- 実装優先度、開発工数見積もり

**Phase 3: 完全版（将来的に実装可能）**
- フル機能版
- 必要な技術的投資、長期的なロードマップ
"""
```

**変更箇所2: job_generator_endpoints.py に要求緩和提案生成関数追加**

```python
def _generate_requirement_relaxation_suggestions(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    評価結果から要求緩和提案を生成
    """
    suggestions = []
    evaluation = result.get("evaluation_result", {})
    infeasible_tasks = evaluation.get("infeasible_tasks", [])

    if not infeasible_tasks:
        return suggestions

    # infeasible_tasksを分析して緩和提案を生成
    for task in infeasible_tasks:
        task_name = task.get("task")
        reason = task.get("reason", "")

        # パターンマッチングで緩和提案を生成
        if "メール送信" in task_name or "Email" in task_name:
            suggestions.append({
                "original_requirement": task_name,
                "relaxed_requirement": f"{task_name.replace('メール送信', 'メール下書き作成')}",
                "relaxation_type": "scope_reduction",
                "feasibility_after_relaxation": "high",
                "what_is_sacrificed": "自動送信機能",
                "what_is_preserved": "メール本文生成、分析結果の整形",
                "recommendation_level": "strongly_recommended",
                "implementation_note": "Gmail APIのDraft作成機能を使用し、ユーザーが手動で送信"
            })

        elif "過去" in task_name and "年" in task_name:
            # 期間の緩和提案
            import re
            years_match = re.search(r"過去(\d+)年", task_name)
            if years_match:
                original_years = int(years_match.group(1))
                reduced_years = max(1, original_years // 2)
                suggestions.append({
                    "original_requirement": task_name,
                    "relaxed_requirement": task_name.replace(f"過去{original_years}年", f"過去{reduced_years}年"),
                    "relaxation_type": "scope_reduction",
                    "feasibility_after_relaxation": "high",
                    "what_is_sacrificed": f"{original_years - reduced_years}年分のデータ",
                    "what_is_preserved": f"最新{reduced_years}年分のトレンド分析",
                    "recommendation_level": "recommended"
                })

        elif "詳細" in reason or "complex" in reason.lower():
            suggestions.append({
                "original_requirement": task_name,
                "relaxed_requirement": f"{task_name}（サマリーレベル）",
                "relaxation_type": "quality_relaxation",
                "feasibility_after_relaxation": "medium",
                "what_is_sacrificed": "詳細な分析、深い洞察",
                "what_is_preserved": "主要なトレンド、重要指標の抽出",
                "recommendation_level": "consider"
            })

    return suggestions
```

**変更箇所3: infeasible_tasks.yaml に代替案テンプレート追加**

```yaml
# ===== Phase 10: 代替案テンプレート =====
alternative_solution_templates:
  - infeasible_task_type: "外部サービス通知（Slack, Discord等）"
    alternative_solutions:
      - solution_type: "API key登録 + fetchAgent"
        description: "ユーザーがAPI keyを登録すれば実装可能"
        feasibility: "high"
        implementation_steps:
          - "myVaultにSlack/Discord API keyを登録"
          - "fetchAgentでWebhook URLにPOSTリクエスト"
          - "通知内容をstringTemplateAgentで整形"
        expected_quality: "100%（元の要求と同等）"
        pros: ["即座に実装可能", "公式API使用で安定"]
        cons: ["ユーザーがAPI key取得・登録する必要"]

      - solution_type: "メール通知で代替"
        description: "Slack/Discord通知の代わりにメール通知"
        feasibility: "medium"
        implementation_steps:
          - "Gmail APIでDraft作成"
          - "ユーザーが手動送信"
        expected_quality: "70%（リアルタイム性が低下）"
        pros: ["追加のAPI key不要", "実装が簡単"]
        cons: ["リアルタイム性が失われる", "手動操作が必要"]

  - infeasible_task_type: "企業財務データ取得"
    alternative_solutions:
      - solution_type: "Web検索 + LLM抽出"
        description: "Web検索で財務情報を取得し、LLMで抽出"
        feasibility: "medium"
        implementation_steps:
          - "geminiAgentで企業名から検索クエリ生成"
          - "fetchAgentでYahoo FinanceなどWeb検索"
          - "geminiAgentでHTML/JSONから財務データ抽出"
        expected_quality: "60-70%（公式データより精度低下）"
        pros: ["追加API不要", "幅広い企業に対応"]
        cons: ["データ精度がやや低い", "構造化データではない"]

      - solution_type: "ユーザーがCSVアップロード"
        description: "財務データをCSVで提供してもらい処理"
        feasibility: "high"
        implementation_steps:
          - "ユーザーが財務データCSVをアップロード"
          - "geminiAgentでCSV分析・トレンド抽出"
        expected_quality: "90%（データ品質に依存）"
        pros: ["正確なデータ処理", "実装が簡単"]
        cons: ["ユーザーがデータ準備する必要", "自動化度が低下"]

  - infeasible_task_type: "音声文字起こし（MP3→テキスト）"
    alternative_solutions:
      - solution_type: "外部Speech-to-Text API"
        description: "Google Cloud Speech-to-Text等のAPI利用"
        feasibility: "high"
        implementation_steps:
          - "myVaultにGoogle Cloud API keyを登録"
          - "fetchAgentでSpeech-to-Text APIを呼び出し"
          - "geminiAgentで文字起こし結果を整形"
        expected_quality: "95%（高精度）"
        pros: ["高精度な文字起こし", "多言語対応"]
        cons: ["追加API key必要", "従量課金コスト"]

      - solution_type: "LLM音声認識（実験的）"
        description: "Gemini 2.0の音声認識機能を使用"
        feasibility: "medium"
        implementation_steps:
          - "geminiAgent (2.0+)で音声ファイルを直接処理"
          - "文字起こし結果を取得"
        expected_quality: "70-80%（実験的機能）"
        pros: ["追加API不要", "シンプルな実装"]
        cons: ["精度がやや低い", "長時間音声は非対応"]

# ===== Phase 10: 要求緩和パターン =====
requirement_relaxation_patterns:
  - pattern_type: "期間短縮"
    original_pattern: "過去X年"
    relaxed_pattern: "過去Y年（Y < X）"
    typical_reduction: "50%削減"
    feasibility_improvement: "high"
    example: "過去5年の売上 → 過去3年の売上"

  - pattern_type: "件数削減"
    original_pattern: "すべての〇〇"
    relaxed_pattern: "最大N件の〇〇"
    typical_reduction: "上限10-20件"
    feasibility_improvement: "medium"
    example: "すべてのPDFファイル → 最大10個のPDFファイル"

  - pattern_type: "品質緩和"
    original_pattern: "詳細な分析"
    relaxed_pattern: "サマリーレベルの分析"
    typical_reduction: "詳細度50%削減"
    feasibility_improvement: "high"
    example: "詳細な財務分析 → 主要指標のサマリー"

  - pattern_type: "自動化度低減"
    original_pattern: "自動送信"
    relaxed_pattern: "下書き作成（手動送信）"
    typical_reduction: "自動化度70% → 50%"
    feasibility_improvement: "very_high"
    example: "メール自動送信 → メール下書き作成（ユーザーが手動送信）"

  - pattern_type: "段階的実装"
    original_pattern: "フル機能版"
    relaxed_pattern: "Phase 1: 基本機能 → Phase 2: 拡張機能"
    typical_reduction: "Phase 1で50-70%の機能"
    feasibility_improvement: "very_high"
    example: "完全な企業分析システム → Phase 1: 基本的な売上分析"
```

#### 📈 期待効果

| 指標 | Phase 9 | Phase 10（改善後） |
|------|---------|-------------------|
| **代替案提案数** | 1-3個 | 3-5個 |
| **要求緩和提案** | なし | 2-4個 |
| **段階的実装計画** | なし | あり（3 Phase） |
| **具体的な実装手順** | なし | あり（3-5ステップ） |
| **ユーザー満足度** | 低（選択肢が少ない） | 高（多様な選択肢） |
| **実現可能性** | 不明確 | 明確（high/medium/low） |

**改善前（Phase 9）**:
```json
{
  "alternative_proposals": [
    {
      "proposal": "LLMベース実装に置き換え",
      "agents": ["geminiAgent"],
      "feasibility": "medium"
    }
  ]
}
```

**改善後（Phase 10）**:
```json
{
  "alternative_proposals": [
    {
      "proposal": "Web検索 + LLM抽出で財務データ取得",
      "agents": ["geminiAgent", "fetchAgent", "stringTemplateAgent"],
      "feasibility": "medium",
      "implementation_steps": [
        "geminiAgentで企業名から検索クエリ生成",
        "fetchAgentでYahoo Finance検索",
        "geminiAgentでHTML/JSONから財務データ抽出",
        "stringTemplateAgentで結果を整形"
      ],
      "expected_quality": "60-70%（公式データより精度低下）",
      "pros_and_cons": {
        "pros": ["追加API不要", "幅広い企業に対応"],
        "cons": ["データ精度がやや低い", "構造化データではない"]
      }
    }
  ],
  "requirement_relaxation_suggestions": [
    {
      "original_requirement": "過去5年の売上データを分析",
      "relaxed_requirement": "過去3年の売上データを分析",
      "relaxation_type": "scope_reduction",
      "feasibility_after_relaxation": "high",
      "what_is_sacrificed": "2年分のデータ（長期トレンド）",
      "what_is_preserved": "最新3年分のトレンド分析、主要指標",
      "recommendation_level": "strongly_recommended"
    },
    {
      "original_requirement": "メール自動送信",
      "relaxed_requirement": "メール下書き作成（ユーザーが手動送信）",
      "relaxation_type": "scope_reduction",
      "feasibility_after_relaxation": "high",
      "what_is_sacrificed": "自動送信機能",
      "what_is_preserved": "メール本文生成、分析結果の整形",
      "recommendation_level": "strongly_recommended",
      "implementation_note": "Gmail APIのDraft作成機能を使用"
    }
  ],
  "phased_implementation_plan": {
    "phase_1": {
      "name": "基本機能版",
      "description": "企業名から基本的な情報を収集・分析",
      "feasibility": "high",
      "implementation_time": "すぐに実装可能",
      "features": [
        "Web検索で企業情報取得",
        "LLMで基本的な分析",
        "メール下書き作成（手動送信）"
      ],
      "expected_quality": "60-70%"
    },
    "phase_2": {
      "name": "拡張機能版",
      "description": "財務データAPI連携、詳細分析",
      "feasibility": "medium",
      "implementation_time": "API拡張後（2-3ヶ月）",
      "required_api_extensions": ["Financial Data Agent"],
      "features": [
        "公式財務データ取得",
        "過去3年の詳細分析",
        "トレンドグラフ生成"
      ],
      "expected_quality": "85-90%"
    },
    "phase_3": {
      "name": "完全版",
      "description": "フル機能、自動送信対応",
      "feasibility": "low",
      "implementation_time": "長期的な投資（6-12ヶ月）",
      "required_api_extensions": ["Email Sending Agent"],
      "features": [
        "過去5年の詳細分析",
        "競合比較分析",
        "メール自動送信"
      ],
      "expected_quality": "95-100%"
    }
  }
}
```

---

## 📊 Phase 10 実装計画

### Phase 10-A: geminiAgent推薦（15分）

**タスク**:
1. `graphai_capabilities.yaml`にrecommendation, cost_efficiency, performanceフィールド追加
2. geminiAgentを最優先に配置
3. `evaluation.py`プロンプトにgeminiAgent推奨を追記

**予想変更行数**: 約30行

---

### Phase 10-B: max_retry動的調整（45分）

**タスク**:
1. `state.py`にestimated_complexity, adjusted_max_retryフィールド追加
2. `requirement_analysis.py`に複雑度推定ロジック追加
3. `agent.py`に動的max_retry調整関数追加
4. `evaluation.py`でretry戦略最適化

**予想変更行数**: 約120行

---

### Phase 10-C: レスポンスフォーマット統一（60分）

**タスク**:
1. `schemas/job_generator.py`に統一スキーマ追加（JobGeneratorResponse, ErrorType）
2. `job_generator_endpoints.py`のエラーハンドリング全面改修
3. 成功・部分成功・失敗の各ケースでレスポンス統一
4. HTTPステータスコードとエラータイプの整合性確保

**予想変更行数**: 約200行

---

### Phase 10-D: 代替案・要求緩和提案強化（90分）

**タスク**:
1. `evaluation.py`プロンプト大幅拡張（代替案、要求緩和、段階的実装）
2. `job_generator_endpoints.py`に要求緩和提案生成関数追加
3. `infeasible_tasks.yaml`に代替案テンプレート追加
4. `infeasible_tasks.yaml`に要求緩和パターン追加

**予想変更行数**: 約250行

---

### Phase 10-E: テスト・品質チェック（60分）

**タスク**:
1. Scenario 1-3再実行
2. 新しいレスポンススキーマの動作確認
3. 代替案・要求緩和提案の品質確認
4. カバレッジチェック（90%維持）
5. pre-push-check-all.sh実行

**予想変更行数**: 約100行（テストコード）

---

### Phase 10-F: ドキュメント・コミット（30分）

**タスク**:
1. `phase-10-results.md`作成
2. Git commit（Phase 10変更）
3. 最終レビュー

**予想変更行数**: 約300行（ドキュメント）

---

## 📈 Phase 10 成功基準

| 指標 | 目標 | 測定方法 |
|------|------|---------|
| **geminiAgent推薦** | evaluation.pyプロンプトで明記 | プロンプト確認 |
| **max_retry最適化** | simple: 3回、medium: 5回、complex: 7-8回 | ログ確認 |
| **レスポンススキーマ統一** | success, job_id, error_typeが常に存在 | Scenario 1-3テスト |
| **代替案提案数** | 3-5個/シナリオ | テスト結果確認 |
| **要求緩和提案数** | 2-4個/シナリオ | テスト結果確認 |
| **段階的実装計画** | すべての失敗ケースで提供 | テスト結果確認 |
| **カバレッジ維持** | 90%以上 | pytest --cov |
| **品質チェック** | pre-push-check-all.sh合格 | 実行確認 |

---

## 🎯 Phase 10 期待効果

| 項目 | Phase 9 | Phase 10（改善後） | 改善率 |
|------|---------|-------------------|--------|
| **LLM推奨の明確性** | 不明確 | 明確（geminiAgent推奨） | N/A |
| **実行時間（simple）** | 約50秒 | 約30秒（40%削減） | -40% |
| **実行時間（complex）** | タイムアウトリスク | リトライ増で成功率向上 | +20% |
| **レスポンス一貫性** | 低（job_id欠落） | 高（統一スキーマ） | +100% |
| **エラー判定の明確性** | 低（文字列判定） | 高（successフラグ） | +100% |
| **代替案提案数** | 1-3個 | 3-5個 | +67-167% |
| **要求緩和提案** | なし | 2-4個 | N/A（新規） |
| **ユーザーガイダンス** | 不足 | 充実（段階的実装計画） | N/A（新規） |

---

## ✅ 制約条件チェック

### コード品質原則
- [x] **SOLID原則**: 遵守 / 各クラスは単一責任、スキーマ分離
- [x] **KISS原則**: 遵守 / 複雑度推定はシンプルなロジック
- [x] **YAGNI原則**: 遵守 / 必要な機能のみ追加
- [x] **DRY原則**: 遵守 / テンプレートで共通化

### アーキテクチャガイドライン
- [x] **architecture-overview.md**: 準拠 / レイヤー分離を維持
- [x] **レイヤー構造**: schemas → endpoints → nodes → prompts

### 設定管理ルール
- [x] **環境変数**: 遵守 / API keyは環境変数管理
- [x] **myVault**: 遵守 / ユーザーAPIキーはmyVault管理

### 品質担保方針
- [x] **単体テストカバレッジ**: 90%以上維持予定
- [x] **結合テストカバレッジ**: 50%以上維持予定
- [x] **Ruff linting**: エラーゼロ
- [x] **MyPy type checking**: エラーゼロ

### CI/CD準拠
- [x] **PRラベル**: feature ラベル付与予定
- [x] **コミットメッセージ**: 規約準拠
- [x] **pre-push-check-all.sh**: 実行予定

---

## 🚀 次のステップ

この改善提案をレビューいただき、承認後にPhase 10の実装を開始します。

**レビューポイント**:
1. ✅ 改善案1（geminiAgent推薦）の方針は適切か？
2. ✅ 改善案2（max_retry動的調整）の複雑度判定ロジックは妥当か？
3. ✅ 改善案3（レスポンスフォーマット統一）のスキーマ設計は十分か？
4. ✅ 改善案4（代替案・要求緩和提案）のテンプレートは実用的か？

**承認後の実装順序**:
1. Phase 10-A（15分）
2. Phase 10-B（45分）
3. Phase 10-C（60分）
4. Phase 10-D（90分）
5. Phase 10-E（60分）
6. Phase 10-F（30分）

**合計所要時間**: 約5時間

---

## 👤 改善案4: ユーザーシナリオ詳細

Phase 10で実装される代替案・要求緩和提案・段階的実装計画を、ユーザーがどのように活用するかを具体的なシナリオで説明します。

---

### **シナリオA: 代替案を採用して即座に再実行** ⚡ 高速解決パス

#### 📋 前提条件
- ユーザー: 企業の業務担当者（技術知識: 中程度）
- 要求: 「企業名を入力すると、その企業の過去5年の売上とビジネスモデルの変化をまとめてメール送信する」
- 緊急度: 高（今日中に使いたい）

---

#### 🔄 ユーザー体験フロー

**Step 1: 初回要求の入力**

```bash
# ユーザーがAPIにリクエスト送信
curl -X POST http://localhost:8104/aiagent-api/v1/job-generator \
  -H "Content-Type: application/json" \
  -d '{
    "user_requirement": "企業名を入力すると、その企業の過去5年の売上とビジネスモデルの変化をまとめてメール送信する",
    "max_retry": 5
  }'
```

---

**Step 2: システムからの失敗レスポンス（Phase 10改善後）**

```json
{
  "success": false,
  "status": "failed",
  "job_id": null,
  "job_master_id": null,
  "error_type": "business_logic_error",
  "error_message": "要求を実現できませんでした",
  "error_details": {
    "reason": "評価結果: 一部タスクが実現不可能",
    "infeasible_tasks": [
      {
        "task": "企業財務データ取得",
        "reason": "公式財務データAPIが利用不可"
      },
      {
        "task": "メール自動送信",
        "reason": "Email Sending Agent未実装"
      }
    ]
  },
  "execution_time_seconds": 48.8,
  "retry_count": 3,

  // ===== 重要: ユーザーへの代替案提示 =====
  "alternative_proposals": [
    {
      "proposal": "【推奨】Web検索 + LLM抽出で財務データ取得 + Gmail下書き作成",
      "agents": ["geminiAgent", "fetchAgent", "stringTemplateAgent"],
      "feasibility": "high",
      "implementation_steps": [
        "1. geminiAgentで企業名から検索クエリ生成",
        "2. fetchAgentでYahoo Finance等のWeb検索",
        "3. geminiAgentでHTML/JSONから財務データ抽出",
        "4. stringTemplateAgentで結果をMarkdown整形",
        "5. Gmail APIでメール下書き作成（手動送信）"
      ],
      "expected_quality": "70%（公式データより精度低下、自動送信→手動送信）",
      "pros_and_cons": {
        "pros": [
          "追加API key不要（Google API keyのみ）",
          "幅広い企業に対応",
          "すぐに実装可能"
        ],
        "cons": [
          "財務データ精度がやや低い（非公式データ）",
          "メール送信は手動操作が必要"
        ]
      },
      "recommendation_level": "strongly_recommended"
    },
    {
      "proposal": "ユーザーが財務データCSVをアップロード + Gmail下書き作成",
      "agents": ["geminiAgent", "stringTemplateAgent"],
      "feasibility": "high",
      "implementation_steps": [
        "1. ユーザーが企業の財務データをCSV形式で準備",
        "2. geminiAgentでCSVデータを分析・トレンド抽出",
        "3. stringTemplateAgentで結果をMarkdown整形",
        "4. Gmail APIでメール下書き作成（手動送信）"
      ],
      "expected_quality": "90%（データ品質に依存）",
      "pros_and_cons": {
        "pros": [
          "正確なデータ処理（ユーザー提供データ）",
          "実装が簡単"
        ],
        "cons": [
          "ユーザーがデータ準備する必要（手間）",
          "自動化度が低下"
        ]
      },
      "recommendation_level": "recommended"
    }
  ]
}
```

---

**Step 3: ユーザーの判断**

**ユーザーの思考プロセス**:
```
💭 「失敗した... でも代替案が2つ提示されている」

💭 「代替案1: Web検索 + LLM抽出」
   ✅ 追加API key不要
   ✅ すぐに使える
   ⚠️ 精度70%（許容範囲）
   ⚠️ 手動送信（許容可能）

💭 「代替案2: CSV アップロード」
   ✅ 精度90%（高い）
   ❌ 毎回CSVを準備するのは面倒

💭 「今日中に使いたいので、代替案1を採用しよう！」
```

**ユーザーの決定**:
- ✅ **代替案1を採用**: Web検索 + LLM抽出 + Gmail下書き作成
- 理由: 即座に実装可能、手動送信は許容可能

---

**Step 4: 要求の修正と再実行**

```bash
# ユーザーが代替案を反映した修正要求を送信
curl -X POST http://localhost:8104/aiagent-api/v1/job-generator \
  -H "Content-Type: application/json" \
  -d '{
    "user_requirement": "企業名を入力すると、Yahoo Finance等のWeb検索で財務情報を取得し、過去5年の売上とビジネスモデルの変化をまとめてGmail下書き作成する（ユーザーが手動送信）",
    "max_retry": 5
  }'
```

---

**Step 5: 成功レスポンス**

```json
{
  "success": true,
  "status": "success",
  "job_id": "job_20251021_001",
  "job_master_id": "jm_12345",
  "execution_time_seconds": 52.3,
  "retry_count": 1
}
```

---

**Step 6: ユーザーの満足度**

| 指標 | 評価 | コメント |
|------|------|---------|
| **解決速度** | ⭐⭐⭐⭐⭐ | 10分以内に解決 |
| **品質** | ⭐⭐⭐⭐ | 70%品質で実用可能 |
| **操作性** | ⭐⭐⭐⭐⭐ | 明確なガイダンス |
| **総合満足度** | ⭐⭐⭐⭐⭐ | 「すぐに使えた！」 |

---

### **シナリオB: 要求緩和を受け入れて再実行** 🔽 スコープ削減パス

#### 📋 前提条件
- ユーザー: 企業のマーケティング担当者（技術知識: 低）
- 要求: 「すべてのPDFファイルから特定のキーワードを含むページを抽出してMarkdownレポートにまとめる」
- 緊急度: 中（今週中に使いたい）

---

#### 🔄 ユーザー体験フロー

**Step 1: 初回要求の入力**

```bash
curl -X POST http://localhost:8104/aiagent-api/v1/job-generator \
  -H "Content-Type: application/json" \
  -d '{
    "user_requirement": "すべてのPDFファイルから特定のキーワードを含むページを抽出してMarkdownレポートにまとめる",
    "max_retry": 5
  }'
```

---

**Step 2: システムからの失敗レスポンス（Phase 10改善後）**

```json
{
  "success": false,
  "status": "failed",
  "job_id": null,
  "job_master_id": null,
  "error_type": "business_logic_error",
  "error_message": "要求を実現できませんでした",
  "error_details": {
    "reason": "評価結果: 処理対象が大規模すぎて実装不可",
    "infeasible_tasks": [
      {
        "task": "すべてのPDFファイルを処理",
        "reason": "PDFファイル数の上限がなく、リソース制約を超える可能性"
      }
    ]
  },
  "execution_time_seconds": 35.2,
  "retry_count": 2,

  // ===== 重要: ユーザーへの要求緩和提案 =====
  "requirement_relaxation_suggestions": [
    {
      "original_requirement": "すべてのPDFファイルから抽出",
      "relaxed_requirement": "最大20個のPDFファイルから抽出",
      "relaxation_type": "scope_reduction",
      "feasibility_after_relaxation": "high",
      "what_is_sacrificed": "20個を超えるPDFは処理対象外",
      "what_is_preserved": "最大20個までは完全に処理可能",
      "recommendation_level": "strongly_recommended",
      "implementation_note": "ユーザーが処理対象PDFを選択する方式"
    },
    {
      "original_requirement": "すべてのページを詳細に抽出",
      "relaxed_requirement": "キーワード含有ページのサマリーを抽出",
      "relaxation_type": "quality_relaxation",
      "feasibility_after_relaxation": "high",
      "what_is_sacrificed": "ページ全文の詳細情報",
      "what_is_preserved": "キーワード周辺のコンテキスト情報",
      "recommendation_level": "recommended",
      "implementation_note": "geminiAgentでサマリー生成"
    }
  ],

  "alternative_proposals": [
    {
      "proposal": "最大20個のPDF + キーワード検索 + Markdownレポート生成",
      "agents": ["geminiAgent", "stringTemplateAgent"],
      "feasibility": "high",
      "implementation_steps": [
        "1. ユーザーが処理対象PDF（最大20個）を指定",
        "2. geminiAgentで各PDFからキーワード検索",
        "3. キーワード含有ページを抽出",
        "4. stringTemplateAgentでMarkdownレポート生成"
      ],
      "expected_quality": "95%（上限20個の制約以外は同等）",
      "recommendation_level": "strongly_recommended"
    }
  ]
}
```

---

**Step 3: ユーザーの判断**

**ユーザーの思考プロセス**:
```
💭 「失敗した... 『すべてのPDF』が問題らしい」

💭 「要求緩和提案1: 最大20個のPDFに制限」
   ✅ 実現可能性: high
   ✅ 20個もあれば十分（実際は10個くらい）
   ⚠️ 20個を超える場合は追加実行が必要

💭 「要求緩和提案2: 詳細→サマリーに変更」
   ⚠️ サマリーでも問題ないが、できれば詳細が欲しい

💭 「要求緩和1を採用しよう！20個あれば十分」
```

**ユーザーの決定**:
- ✅ **要求緩和1を採用**: 最大20個のPDFに制限
- 理由: 実際の処理対象は10個程度なので十分

---

**Step 4: 要求の修正と再実行**

```bash
# ユーザーが要求緩和を反映した修正要求を送信
curl -X POST http://localhost:8104/aiagent-api/v1/job-generator \
  -H "Content-Type: application/json" \
  -d '{
    "user_requirement": "最大20個のPDFファイルから特定のキーワードを含むページを抽出してMarkdownレポートにまとめる",
    "max_retry": 5
  }'
```

---

**Step 5: 成功レスポンス**

```json
{
  "success": true,
  "status": "success",
  "job_id": "job_20251021_002",
  "job_master_id": "jm_12346",
  "execution_time_seconds": 41.7,
  "retry_count": 1
}
```

---

**Step 6: ユーザーの満足度**

| 指標 | 評価 | コメント |
|------|------|---------|
| **解決速度** | ⭐⭐⭐⭐⭐ | 5分以内に解決 |
| **品質** | ⭐⭐⭐⭐⭐ | 95%品質で実用可能 |
| **操作性** | ⭐⭐⭐⭐⭐ | 明確な緩和提案 |
| **総合満足度** | ⭐⭐⭐⭐⭐ | 「制約を理解して納得」 |

---

### **シナリオC: 段階的実装（Phase 1）を先行実装** 🚀 早期価値提供パス

#### 📋 前提条件
- ユーザー: 企業のIT部門マネージャー（技術知識: 高）
- 要求: 「企業名を入力すると、その企業の過去5年の売上とビジネスモデルの変化をまとめてメール送信する」
- 緊急度: 低（3ヶ月以内に完成版が欲しい）

---

#### 🔄 ユーザー体験フロー

**Step 1: 初回要求の入力**

```bash
curl -X POST http://localhost:8104/aiagent-api/v1/job-generator \
  -H "Content-Type: application/json" \
  -d '{
    "user_requirement": "企業名を入力すると、その企業の過去5年の売上とビジネスモデルの変化をまとめてメール送信する",
    "max_retry": 5
  }'
```

---

**Step 2: システムからの失敗レスポンス（Phase 10改善後）**

```json
{
  "success": false,
  "status": "failed",
  "job_id": null,
  "job_master_id": null,
  "error_type": "business_logic_error",
  "error_message": "要求を実現できませんでした",
  "error_details": {
    "reason": "評価結果: 一部タスクが実現不可能",
    "infeasible_tasks": [
      {
        "task": "企業財務データ取得",
        "reason": "公式財務データAPIが利用不可"
      },
      {
        "task": "メール自動送信",
        "reason": "Email Sending Agent未実装"
      }
    ]
  },
  "execution_time_seconds": 48.8,
  "retry_count": 3,

  // ===== 重要: 段階的実装計画の提示 =====
  "phased_implementation_plan": {
    "phase_1": {
      "name": "基本機能版（MVP）",
      "description": "企業名から基本的な情報を収集・分析",
      "feasibility": "high",
      "implementation_time": "すぐに実装可能",
      "features": [
        "Web検索で企業情報取得（Yahoo Finance等）",
        "geminiAgentで基本的な財務分析",
        "過去3年の売上トレンド分析（5年→3年に短縮）",
        "Gmail下書き作成（手動送信）"
      ],
      "expected_quality": "60-70%（公式データではない、手動送信）",
      "pros": [
        "追加API key不要",
        "すぐに使い始められる",
        "基本的な分析は可能"
      ],
      "cons": [
        "財務データ精度がやや低い",
        "過去5年→3年に短縮",
        "メール送信は手動"
      ]
    },
    "phase_2": {
      "name": "拡張機能版",
      "description": "財務データAPI連携、詳細分析",
      "feasibility": "medium",
      "implementation_time": "API拡張後（2-3ヶ月）",
      "required_api_extensions": [
        {
          "feature": "Financial Data Agent",
          "description": "企業財務データを取得・分析するエージェント",
          "priority": "high",
          "estimated_development_time": "6-8週間"
        }
      ],
      "features": [
        "公式財務データ取得（高精度）",
        "過去5年の詳細分析",
        "ビジネスモデル変化の深い洞察",
        "トレンドグラフ生成",
        "Gmail下書き作成（手動送信）"
      ],
      "expected_quality": "85-90%（公式データ使用、手動送信）"
    },
    "phase_3": {
      "name": "完全版",
      "description": "フル機能、自動送信対応",
      "feasibility": "low",
      "implementation_time": "長期的な投資（6-12ヶ月）",
      "required_api_extensions": [
        {
          "feature": "Financial Data Agent",
          "description": "（Phase 2で実装済み）",
          "priority": "high"
        },
        {
          "feature": "Email Sending Agent",
          "description": "メール自動送信エージェント",
          "priority": "medium",
          "estimated_development_time": "4-6週間"
        }
      ],
      "features": [
        "公式財務データ取得",
        "過去5年の詳細分析",
        "競合比較分析",
        "メール自動送信（完全自動化）"
      ],
      "expected_quality": "95-100%（フル機能）"
    }
  },

  "api_extension_proposals": [
    {
      "feature": "Financial Data Agent",
      "description": "企業財務データを取得・分析するエージェント",
      "priority": "high",
      "estimated_development_time": "6-8週間",
      "business_value": "企業分析の精度向上、自動化促進",
      "target_users": "財務分析、経営企画、投資判断"
    },
    {
      "feature": "Email Sending Agent",
      "description": "メール自動送信エージェント",
      "priority": "medium",
      "estimated_development_time": "4-6週間",
      "business_value": "完全自動化、ユーザー操作削減",
      "target_users": "営業、マーケティング、レポート配信"
    }
  ]
}
```

---

**Step 3: ユーザーの判断**

**ユーザーの思考プロセス**:
```
💭 「失敗した... でも段階的実装計画が提示されている」

💭 「Phase 1: 基本機能版（MVP）」
   ✅ すぐに使える
   ✅ 60-70%の品質で試せる
   ⚠️ 過去5年→3年に短縮
   ⚠️ 手動送信

💭 「Phase 2: 拡張機能版」
   ✅ 2-3ヶ月後に利用可能
   ✅ 85-90%の品質
   ✅ 公式財務データ使用
   ⚠️ まだ手動送信

💭 「Phase 3: 完全版」
   ✅ 6-12ヶ月後に利用可能
   ✅ 95-100%の品質
   ✅ 完全自動化

💭 「まずPhase 1で試して、Phase 2/3をシステム管理者に依頼しよう！」
```

**ユーザーの決定**:
- ✅ **Phase 1を先行実装**: 基本機能版（MVP）で試用開始
- ✅ **Phase 2/3を後日実装**: API拡張提案をシステム管理者に提出

---

**Step 4: Phase 1の実装（即座に実行）**

```bash
# ユーザーがPhase 1の要求を送信
curl -X POST http://localhost:8104/aiagent-api/v1/job-generator \
  -H "Content-Type: application/json" \
  -d '{
    "user_requirement": "【Phase 1】企業名を入力すると、Web検索で企業情報を取得し、過去3年の売上トレンドを分析してGmail下書き作成する（手動送信）",
    "max_retry": 5
  }'
```

**Phase 1の成功レスポンス**:
```json
{
  "success": true,
  "status": "success",
  "job_id": "job_20251021_003_phase1",
  "job_master_id": "jm_12347",
  "execution_time_seconds": 45.2,
  "retry_count": 1
}
```

---

**Step 5: API拡張依頼（システム管理者へ）**

**ユーザーがシステム管理者に送信するメール**:

```
件名: API拡張依頼: Financial Data Agent / Email Sending Agent

担当者様

以下のAPI拡張を依頼します。

【依頼背景】
Job/Task Generator APIで企業分析ワークフローを構築中ですが、
以下の機能が不足しており、完全版の実装ができません。

【依頼内容】

1. Financial Data Agent（優先度: 高）
   - 概要: 企業財務データを取得・分析するエージェント
   - 開発期間: 6-8週間
   - ビジネス価値: 企業分析の精度向上、自動化促進
   - 対象ユーザー: 財務分析、経営企画、投資判断

2. Email Sending Agent（優先度: 中）
   - 概要: メール自動送信エージェント
   - 開発期間: 4-6週間
   - ビジネス価値: 完全自動化、ユーザー操作削減
   - 対象ユーザー: 営業、マーケティング、レポート配信

【段階的実装計画】
- Phase 1（現在）: 基本機能版で運用中（品質60-70%）
- Phase 2（2-3ヶ月後）: Financial Data Agent実装後（品質85-90%）
- Phase 3（6-12ヶ月後）: Email Sending Agent実装後（品質95-100%）

【添付資料】
- API拡張提案詳細: phase-10-improvement-proposal.md

ご検討よろしくお願いいたします。
```

---

**Step 6: Phase 2/3の実装（後日）**

**2-3ヶ月後: Financial Data Agent実装完了**

```bash
# ユーザーがPhase 2の要求を送信
curl -X POST http://localhost:8104/aiagent-api/v1/job-generator \
  -H "Content-Type: application/json" \
  -d '{
    "user_requirement": "【Phase 2】企業名を入力すると、公式財務データを取得し、過去5年の売上とビジネスモデルの変化を詳細に分析してGmail下書き作成する（手動送信）",
    "max_retry": 5
  }'
```

**6-12ヶ月後: Email Sending Agent実装完了**

```bash
# ユーザーがPhase 3の要求を送信
curl -X POST http://localhost:8104/aiagent-api/v1/job-generator \
  -H "Content-Type: application/json" \
  -d '{
    "user_requirement": "【Phase 3】企業名を入力すると、公式財務データを取得し、過去5年の売上とビジネスモデルの変化を詳細に分析してメール自動送信する",
    "max_retry": 5
  }'
```

---

**Step 7: ユーザーの満足度**

| Phase | 品質 | 満足度 | コメント |
|-------|------|--------|---------|
| **Phase 1（即座）** | 60-70% | ⭐⭐⭐⭐ | 「すぐに試せた！」 |
| **Phase 2（2-3ヶ月）** | 85-90% | ⭐⭐⭐⭐⭐ | 「精度が上がった！」 |
| **Phase 3（6-12ヶ月）** | 95-100% | ⭐⭐⭐⭐⭐ | 「完全自動化達成！」 |

---

### **シナリオD: API拡張をシステム管理者に依頼して後日再挑戦** 🔧 根本解決パス

#### 📋 前提条件
- ユーザー: 企業のデータサイエンティスト（技術知識: 高）
- 要求: 「Gmail受信メールから音声ファイルを抽出し、文字起こししてMarkdownにまとめる」
- 緊急度: 低（6ヶ月以内に完成版が欲しい）

---

#### 🔄 ユーザー体験フロー

**Step 1: 初回要求の入力**

```bash
curl -X POST http://localhost:8104/aiagent-api/v1/job-generator \
  -H "Content-Type: application/json" \
  -d '{
    "user_requirement": "Gmail受信メールから音声ファイルを抽出し、文字起こししてMarkdownにまとめる",
    "max_retry": 5
  }'
```

---

**Step 2: システムからの失敗レスポンス（Phase 10改善後）**

```json
{
  "success": false,
  "status": "failed",
  "job_id": null,
  "job_master_id": null,
  "error_type": "business_logic_error",
  "error_message": "要求を実現できませんでした",
  "error_details": {
    "reason": "評価結果: 音声処理機能が利用不可",
    "infeasible_tasks": [
      {
        "task": "音声ファイルの文字起こし（MP3→テキスト）",
        "reason": "Speech-to-Text Agent未実装"
      }
    ]
  },
  "execution_time_seconds": 42.1,
  "retry_count": 2,

  // ===== 重要: 代替案は実用性が低い =====
  "alternative_proposals": [
    {
      "proposal": "【実験的】Gemini 2.0の音声認識機能を使用",
      "agents": ["geminiAgent"],
      "feasibility": "low",
      "implementation_steps": [
        "1. geminiAgent (2.0+)で音声ファイルを直接処理",
        "2. 文字起こし結果を取得"
      ],
      "expected_quality": "50-60%（実験的機能、精度低い）",
      "pros_and_cons": {
        "pros": ["追加API不要", "シンプルな実装"],
        "cons": [
          "精度が非常に低い（50-60%）",
          "長時間音声は非対応",
          "実験的機能のため不安定"
        ]
      },
      "recommendation_level": "not_recommended"
    }
  ],

  // ===== 重要: API拡張提案が明確 =====
  "api_extension_proposals": [
    {
      "feature": "Speech-to-Text Agent",
      "description": "音声ファイルを文字起こしするエージェント（Google Cloud Speech-to-Text等）",
      "priority": "high",
      "estimated_development_time": "4-6週間",
      "business_value": "音声データの自動処理、議事録作成、コンテンツ分析",
      "target_users": "カスタマーサポート、営業、マーケティング、コンテンツ制作",
      "technical_requirements": [
        "Google Cloud Speech-to-Text API連携",
        "音声ファイルフォーマット対応（MP3, WAV, FLAC等）",
        "多言語対応",
        "タイムスタンプ付き文字起こし"
      ],
      "estimated_cost": "従量課金（60分あたり$1.44程度）"
    }
  ],

  // ===== 重要: 要求緩和提案がない（根本解決が必要） =====
  "requirement_relaxation_suggestions": []
}
```

---

**Step 3: ユーザーの判断**

**ユーザーの思考プロセス**:
```
💭 「失敗した... 音声処理機能がない」

💭 「代替案: Gemini 2.0の音声認識」
   ❌ 精度50-60%（低すぎる）
   ❌ 実験的機能で不安定
   ❌ recommendation_level: not_recommended

💭 「要求緩和提案なし」
   → 緩和しても解決しない

💭 「API拡張提案: Speech-to-Text Agent」
   ✅ 精度95%以上（高精度）
   ✅ 開発期間4-6週間（許容範囲）
   ✅ 多言語対応、タイムスタンプ付き
   ✅ ビジネス価値が明確

💭 「代替案は使えない。API拡張を依頼して待つのが最善」
```

**ユーザーの決定**:
- ❌ **代替案は採用しない**: 品質が低すぎる
- ✅ **API拡張を依頼**: Speech-to-Text Agentの実装をシステム管理者に依頼

---

**Step 4: API拡張依頼（システム管理者へ）**

**ユーザーがシステム管理者に送信するメール**:

```
件名: API拡張依頼: Speech-to-Text Agent（優先度: 高）

担当者様

以下のAPI拡張を依頼します。

【依頼背景】
音声データの自動処理ワークフローを構築したいが、
Speech-to-Text機能が不足しており実装できません。

【依頼内容】

Speech-to-Text Agent
- 概要: 音声ファイルを高精度に文字起こしするエージェント
- 推奨実装: Google Cloud Speech-to-Text API連携
- 開発期間: 4-6週間
- ビジネス価値: 音声データの自動処理、議事録作成、コンテンツ分析
- 対象ユーザー: カスタマーサポート、営業、マーケティング、コンテンツ制作

【技術要件】
- 音声ファイルフォーマット対応（MP3, WAV, FLAC等）
- 多言語対応
- タイムスタンプ付き文字起こし
- 精度95%以上

【コスト】
- 従量課金（60分あたり$1.44程度）

【代替案の検討結果】
- Gemini 2.0の音声認識機能: 精度50-60%で実用不可
- → 高精度なSpeech-to-Text Agentの実装が必須

【添付資料】
- API拡張提案詳細: phase-10-improvement-proposal.md
- ビジネスケース: 音声データ活用による業務効率化ROI試算

ご検討よろしくお願いいたします。
```

---

**Step 5: API拡張の承認と実装（4-6週間後）**

**システム管理者からの返信**:
```
承認しました。Speech-to-Text Agent実装を開始します。
完了予定: 6週間後（2025年12月上旬）
進捗は毎週報告します。
```

---

**Step 6: API拡張完了後の再実行（6週間後）**

```bash
# ユーザーが元の要求を再送信
curl -X POST http://localhost:8104/aiagent-api/v1/job-generator \
  -H "Content-Type: application/json" \
  -d '{
    "user_requirement": "Gmail受信メールから音声ファイルを抽出し、文字起こししてMarkdownにまとめる",
    "max_retry": 5
  }'
```

**成功レスポンス**:
```json
{
  "success": true,
  "status": "success",
  "job_id": "job_20251201_001",
  "job_master_id": "jm_12348",
  "execution_time_seconds": 67.3,
  "retry_count": 1
}
```

---

**Step 7: ユーザーの満足度**

| 指標 | 評価 | コメント |
|------|------|---------|
| **解決速度** | ⭐⭐⭐ | 6週間待機（計画通り） |
| **品質** | ⭐⭐⭐⭐⭐ | 95%品質で高精度 |
| **操作性** | ⭐⭐⭐⭐⭐ | 明確なAPI拡張提案 |
| **総合満足度** | ⭐⭐⭐⭐⭐ | 「根本解決できた！」 |

---

### **シナリオE: 複数の提案を組み合わせて最適解を見つける** 🎯 ハイブリッドパス

#### 📋 前提条件
- ユーザー: 企業のプロダクトマネージャー（技術知識: 中程度）
- 要求: 「企業名を入力すると、その企業の過去5年の売上とビジネスモデルの変化をまとめてメール送信する」
- 緊急度: 中（1ヶ月以内に実用レベルが欲しい）

---

#### 🔄 ユーザー体験フロー

**Step 1: 初回要求の入力**

```bash
curl -X POST http://localhost:8104/aiagent-api/v1/job-generator \
  -H "Content-Type: application/json" \
  -d '{
    "user_requirement": "企業名を入力すると、その企業の過去5年の売上とビジネスモデルの変化をまとめてメール送信する",
    "max_retry": 5
  }'
```

---

**Step 2: システムからの失敗レスポンス（Phase 10改善後）**

```json
{
  "success": false,
  "status": "failed",
  "job_id": null,
  "job_master_id": null,
  "error_type": "business_logic_error",
  "error_message": "要求を実現できませんでした",
  "error_details": {
    "reason": "評価結果: 一部タスクが実現不可能",
    "infeasible_tasks": [
      {
        "task": "企業財務データ取得",
        "reason": "公式財務データAPIが利用不可"
      },
      {
        "task": "メール自動送信",
        "reason": "Email Sending Agent未実装"
      }
    ]
  },
  "execution_time_seconds": 48.8,
  "retry_count": 3,

  "alternative_proposals": [
    {
      "proposal": "Web検索 + LLM抽出",
      "feasibility": "high",
      "expected_quality": "70%"
    },
    {
      "proposal": "ユーザーがCSVアップロード",
      "feasibility": "high",
      "expected_quality": "90%"
    }
  ],

  "requirement_relaxation_suggestions": [
    {
      "original_requirement": "過去5年の売上データ",
      "relaxed_requirement": "過去3年の売上データ",
      "relaxation_type": "scope_reduction",
      "feasibility_after_relaxation": "high"
    },
    {
      "original_requirement": "メール自動送信",
      "relaxed_requirement": "Gmail下書き作成（手動送信）",
      "relaxation_type": "scope_reduction",
      "feasibility_after_relaxation": "high"
    }
  ]
}
```

---

**Step 3: ユーザーの判断（複数提案の比較）**

**ユーザーの思考プロセス**:
```
💭 「失敗した... 代替案と要求緩和の両方が提示されている」

💭 「代替案1: Web検索 + LLM抽出」
   ✅ すぐに使える
   ⚠️ 精度70%（やや低い）

💭 「代替案2: CSVアップロード」
   ✅ 精度90%（高い）
   ❌ 毎回CSVを準備するのは面倒

💭 「要求緩和1: 過去5年→3年」
   ✅ 実現可能性が上がる
   ⚠️ 長期トレンドが見えにくい

💭 「要求緩和2: 自動送信→手動送信」
   ✅ 実現可能性が上がる
   ✅ 手動送信は許容可能

💭 「ハイブリッド戦略を考えよう！」
   → 代替案1（Web検索） + 要求緩和1（3年） + 要求緩和2（手動送信）
   → 精度70% × 3年 × 手動送信 = 実用レベル80%

💭 「これなら今すぐ使えて、後日Phase 2で改善できる！」
```

**ユーザーの決定**:
- ✅ **ハイブリッド戦略**: 代替案1 + 要求緩和1 + 要求緩和2
- ✅ **段階的改善**: Phase 1で運用開始、Phase 2で品質向上

---

**Step 4: ハイブリッド要求の送信**

```bash
# ユーザーがハイブリッド要求を送信
curl -X POST http://localhost:8104/aiagent-api/v1/job-generator \
  -H "Content-Type: application/json" \
  -d '{
    "user_requirement": "企業名を入力すると、Web検索で企業情報を取得し、過去3年の売上トレンドとビジネスモデルの変化をまとめてGmail下書き作成する（手動送信）",
    "max_retry": 5
  }'
```

---

**Step 5: 成功レスポンス**

```json
{
  "success": true,
  "status": "success",
  "job_id": "job_20251021_004",
  "job_master_id": "jm_12349",
  "execution_time_seconds": 49.1,
  "retry_count": 1
}
```

---

**Step 6: 運用後のフィードバックと改善計画**

**1ヶ月後のユーザーレビュー**:
```
✅ Phase 1運用結果:
  - 実用レベル: 80%
  - ユーザー満足度: 4/5
  - 主な不満: 「過去3年だけだとトレンドが分かりにくい」

📝 改善計画:
  - Phase 2実装を決定
  - Financial Data Agent実装依頼をシステム管理者に提出
  - 完了予定: 2-3ヶ月後
```

---

**Step 7: Phase 2実装後（3ヶ月後）**

```bash
# Phase 2要求を送信
curl -X POST http://localhost:8104/aiagent-api/v1/job-generator \
  -H "Content-Type: application/json" \
  -d '{
    "user_requirement": "企業名を入力すると、公式財務データを取得し、過去5年の売上とビジネスモデルの変化を詳細に分析してGmail下書き作成する（手動送信）",
    "max_retry": 5
  }'
```

**Phase 2成功レスポンス**:
```json
{
  "success": true,
  "status": "success",
  "job_id": "job_20260121_001",
  "job_master_id": "jm_12350",
  "execution_time_seconds": 58.7,
  "retry_count": 1
}
```

---

**Step 8: ユーザーの満足度（Phase 1 → Phase 2）**

| Phase | 品質 | 満足度 | コメント |
|-------|------|--------|---------|
| **Phase 1（即座）** | 80% | ⭐⭐⭐⭐ | 「実用レベルで使えた！」 |
| **Phase 2（3ヶ月）** | 90% | ⭐⭐⭐⭐⭐ | 「完璧になった！」 |

---

## 📊 ユーザーシナリオ比較表

| シナリオ | 解決速度 | 品質 | 適用ケース | ユーザータイプ |
|---------|---------|------|-----------|-------------|
| **A: 代替案採用** | ⚡ 超高速（10分） | ⭐⭐⭐⭐ 70% | 緊急度高、品質許容可能 | 業務担当者 |
| **B: 要求緩和** | ⚡ 高速（5分） | ⭐⭐⭐⭐⭐ 95% | スコープ削減で解決 | マーケター |
| **C: 段階的実装** | 🚀 即座+長期 | ⭐⭐⭐⭐⭐ 段階的向上 | 時間的余裕あり | ITマネージャー |
| **D: API拡張依頼** | 🔧 長期（6週間） | ⭐⭐⭐⭐⭐ 95%+ | 根本解決が必要 | データサイエンティスト |
| **E: ハイブリッド** | 🎯 即座+改善 | ⭐⭐⭐⭐⭐ 段階的向上 | 柔軟な対応 | プロダクトマネージャー |

---

## 🎯 Phase 10改善案4の効果（ユーザーシナリオ観点）

| 指標 | Phase 9 | Phase 10（改善後） | 改善効果 |
|------|---------|-------------------|---------|
| **解決パスの選択肢** | 1つ（代替案のみ） | 5つ（代替案、緩和、段階、API拡張、ハイブリッド） | +400% |
| **ユーザー満足度** | 低（選択肢が少ない） | 高（多様なパス） | +100% |
| **解決率** | 33%（Scenario 2のみ） | 80-90%（多様な解決パス） | +150% |
| **実装時間** | 不明確 | 明確（即座～6ヶ月） | 透明性向上 |
| **品質の明確性** | 不明確 | 明確（60-100%） | 透明性向上 |

---

ご確認・フィードバックをお待ちしております。
