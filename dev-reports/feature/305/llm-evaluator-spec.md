# LLM Evaluator 機能仕様書

**作成日**: 2024-12-24
**更新日**: 2024-12-24
**ブランチ**: fix/issue/305
**親Issue**: #305 (Job生成ワークフローの2段階進捗表示)
**担当**: Claude Code

---

## 1. 概要

### 1.1 背景

現在の Workflow Generator の Validator ノードは**ルールベース検証**のみを行っています：

| 検証種別 | 内容 | 限界 |
|---------|------|------|
| YAML構文検証 | `yaml.safe_load()` でパース可能か | 意味論的な正しさは検証不可 |
| HTTPステータス検証 | 200/400/404/500/504 の判定 | 成功でも出力品質は不明 |
| GraphAI実行エラー検証 | ノードエラー・タイムアウト検出 | エラーがなくても品質は不明 |
| 出力スキーマ検証 | 結果が存在するか | 出力内容の妥当性は検証不可 |
| **テストデータ検証** | なし | **テストデータの品質が検証されていない** |

### 1.2 目的

**LLM Evaluator** を追加し、以下を実現します：

1. **意味論的検証**: ワークフローが要件を満たしているか LLM が評価
2. **品質スコアリング**: 0-100点のスコアと詳細な評価理由を提供
3. **テストデータ品質評価**: サンプル入力の妥当性を評価し、不備があれば再生成
4. **結果サマリ**: 全検証結果を集約した人間可読なサマリを生成

### 1.3 スコープ

| 対象 | スコープ内 | スコープ外 |
|------|-----------|-----------|
| 検証対象 | 生成されたYAML、実行結果、入出力、**テストデータ** | 外部API品質 |
| 評価観点 | 構造、意味、品質、**テストデータ妥当性** | パフォーマンス |
| 出力形式 | JSON + Markdown サマリ | PDF レポート |

---

## 2. アーキテクチャ

### 2.1 システム構成

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Workflow Generator LangGraph Flow                          │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌────────────┐    ┌─────────────────┐    ┌─────────────────┐                │
│  │  Generator │───▶│ Sample Input    │───▶│ Workflow Tester │                │
│  │    Node    │    │ Generator Node  │    │      Node       │                │
│  └────────────┘    └─────────────────┘    └────────┬────────┘                │
│        ▲                    ▲                      │                          │
│        │                    │                      ▼                          │
│        │                    │              ┌─────────────────┐                │
│        │                    │              │   Validator     │                │
│        │                    │              │     Node        │                │
│        │                    │              └────────┬────────┘                │
│        │                    │                       │                          │
│        │                    │                       ▼                          │
│        │           ┌────────┴────────┐    ┌─────────────────┐                │
│        │           │  Test Data      │◀───│  LLM Evaluator  │                │
│        │           │  Regenerator    │    │     Node        │                │
│        │           │  Node (NEW)     │    │   (NEW)         │                │
│        │           └─────────────────┘    └────────┬────────┘                │
│        │                                           │                          │
│        │                                           ▼                          │
│  ┌─────┴──────┐                          ┌─────────────────┐                 │
│  │Self-Repair │◀─────────────────────────│ Result Summary  │                 │
│  │    Node    │                          │    Generator    │───▶ END         │
│  └────────────┘                          │   (NEW)         │                 │
│                                          └─────────────────┘                 │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 フロー変更

**現行フロー:**
```
generator → sample_input_generator → workflow_tester → validator → (条件分岐) → self_repair or END
```

**新フロー:**
```
generator → sample_input_generator → workflow_tester → validator → llm_evaluator
    → (条件分岐)
        ├─ テストデータ不備 → test_data_regenerator → workflow_tester (再テスト)
        ├─ ワークフロー不備 → self_repair → generator (再生成)
        └─ 成功 → result_summary_generator → END
```

### 2.3 ノード責務

| ノード | 責務 | LLM使用 |
|--------|------|---------|
| `validator_node` | ルールベース検証（既存） | No |
| `llm_evaluator_node` | LLMによる意味論的評価 + テストデータ評価（**新規**） | Yes |
| `test_data_regenerator_node` | LLMによるテストデータ再生成（**新規**） | Yes |
| `result_summary_generator_node` | 結果集約・サマリ生成（**新規**） | Yes (optional) |

---

## 3. 詳細設計

### 3.1 State 拡張

```python
# state.py への追加フィールド

class WorkflowGeneratorState(TypedDict, total=False):
    # ===== 既存フィールド =====
    # ... (省略)

    # ===== LLM Evaluator (NEW) =====
    llm_evaluation_result: LLMEvaluationResult | None
    evaluation_score: int | None  # 0-100
    evaluation_feedback: str | None  # LLMからのフィードバック
    evaluation_suggestions: list[str]  # 改善提案リスト

    # ===== Test Data Quality (NEW) =====
    test_data_quality_score: int | None  # 0-100
    test_data_issues: list[str]  # テストデータの問題点
    needs_test_data_regeneration: bool  # テストデータ再生成が必要か
    test_data_regeneration_count: int  # テストデータ再生成回数
    max_test_data_regeneration: int  # 最大再生成回数 (default: 2)
    regenerated_sample_input: dict[str, Any] | None  # LLM生成のサンプル入力

    # ===== Result Summary (NEW) =====
    validation_summary: ValidationSummary | None
    summary_markdown: str | None  # Markdown形式のサマリ
```

### 3.2 LLM Evaluator Node

#### 3.2.1 評価観点

| 観点 | 重み | 評価内容 |
|------|------|---------|
| **構造的妥当性** | 20% | ノード構成、データフローの論理性 |
| **要件充足度** | 30% | TaskMaster要件を満たしているか |
| **出力品質** | 20% | 実行結果が期待通りか |
| **エラー耐性** | 10% | エラーハンドリングの適切さ |
| **テストデータ品質** | 20% | サンプル入力の妥当性・現実性 |

#### 3.2.2 テストデータ品質評価の詳細

| 評価項目 | 内容 | 低スコア例 |
|---------|------|-----------|
| **現実性** | 実際のユースケースで使われそうなデータか | `"sample_text"`, `"test"`, `"aaa"` |
| **スキーマ適合性** | 入力スキーマの制約を満たしているか | 必須フィールド欠落、型不一致 |
| **ドメイン妥当性** | ビジネスドメインに適した値か | 企業名に `"sample_text"` を使用 |
| **境界値考慮** | エッジケースを含むか | 空文字、最大長、特殊文字 |
| **API互換性** | 呼び出すAPIが受け付けるデータか | 存在しない企業コード |

#### 3.2.3 入力データ

```python
@dataclass
class LLMEvaluatorInput:
    """LLM Evaluator への入力データ"""

    # TaskMaster情報
    task_name: str
    task_description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    recommended_apis: list[str]

    # 生成結果
    yaml_content: str
    sample_input: dict[str, Any]
    execution_result: dict[str, Any] | None

    # ルールベース検証結果
    rule_based_issues: list[dict[str, str]]
    http_status: int | None

    # テストデータ再生成情報 (NEW)
    is_regenerated_test_data: bool
    test_data_regeneration_count: int
```

#### 3.2.4 出力データ

```python
class LLMEvaluationResult(BaseModel):
    """LLM Evaluator の評価結果"""

    # 総合スコア (0-100)
    overall_score: int = Field(..., ge=0, le=100)

    # 観点別スコア
    structural_score: int = Field(..., ge=0, le=100)
    requirement_score: int = Field(..., ge=0, le=100)
    output_quality_score: int = Field(..., ge=0, le=100)
    error_handling_score: int = Field(..., ge=0, le=100)
    test_data_quality_score: int = Field(..., ge=0, le=100)  # NEW

    # テストデータ評価詳細 (NEW)
    test_data_issues: list[str]  # テストデータの問題点
    needs_test_data_regeneration: bool  # 再生成が必要か
    suggested_test_data: dict[str, Any] | None  # 推奨テストデータ（再生成用）

    # 評価詳細
    strengths: list[str]  # 良い点
    weaknesses: list[str]  # 改善が必要な点
    suggestions: list[str]  # 具体的な改善提案

    # 判定
    is_acceptable: bool  # 合格判定 (overall_score >= 70)
    failure_reason: Literal[
        "none",
        "workflow_quality",
        "test_data_quality",
        "both"
    ]  # NEW: 失敗理由の分類
    confidence: float  # LLMの確信度 (0.0-1.0)

    # メタ情報
    evaluation_model: str  # 使用したモデル名
    evaluation_timestamp: str
```

#### 3.2.5 プロンプト設計

```yaml
# prompts/llm_evaluation.yaml

system_prompt: |
  あなたはGraphAIワークフローの品質評価エキスパートです。
  以下の観点でワークフローを評価し、構造化されたJSONで結果を返してください。

  ## 評価観点

  ### 1. 構造的妥当性 (structural_score: 0-100)
  - ノード定義が正しいか
  - データフローが論理的か
  - 依存関係が適切か
  - 無駄なノードがないか

  ### 2. 要件充足度 (requirement_score: 0-100)
  - TaskMasterの説明を満たしているか
  - 推奨APIを適切に使用しているか
  - 入力スキーマを正しく処理しているか
  - 出力スキーマに準拠しているか

  ### 3. 出力品質 (output_quality_score: 0-100)
  - 実行結果が期待通りか
  - データ形式が正しいか
  - 必須フィールドが含まれているか

  ### 4. エラー耐性 (error_handling_score: 0-100)
  - エラーハンドリングが適切か
  - リトライロジックがあるか
  - フォールバック処理があるか

  ### 5. テストデータ品質 (test_data_quality_score: 0-100) ★重要★
  テストデータ（サンプル入力）の品質を厳密に評価してください：

  - **現実性**: 実際のユースケースで使われそうなデータか
    - NG例: "sample_text", "test", "aaa", "xxx"
    - OK例: "トヨタ自動車", "東京都渋谷区", "2024-01-15"

  - **スキーマ適合性**: 入力スキーマの制約を満たしているか
    - 必須フィールドが存在するか
    - 型が正しいか

  - **ドメイン妥当性**: ビジネスドメインに適した値か
    - 企業情報取得タスクなら実在しそうな企業名
    - 日付フィールドなら妥当な日付形式

  - **API互換性**: 呼び出すAPIが受け付けるデータか
    - 外部APIが存在チェックする場合、存在しうる値か

  テストデータが不適切な場合は `needs_test_data_regeneration: true` とし、
  `suggested_test_data` に適切なテストデータを提案してください。

  ## 出力形式
  必ず以下のJSON形式で回答してください：
  ```json
  {
    "overall_score": <0-100>,
    "structural_score": <0-100>,
    "requirement_score": <0-100>,
    "output_quality_score": <0-100>,
    "error_handling_score": <0-100>,
    "test_data_quality_score": <0-100>,
    "test_data_issues": ["問題点1", "問題点2"],
    "needs_test_data_regeneration": <true|false>,
    "suggested_test_data": { "field1": "適切な値1", ... } | null,
    "strengths": ["良い点1", "良い点2"],
    "weaknesses": ["改善点1", "改善点2"],
    "suggestions": ["具体的な改善提案1", "具体的な改善提案2"],
    "is_acceptable": <true|false>,
    "failure_reason": "none" | "workflow_quality" | "test_data_quality" | "both",
    "confidence": <0.0-1.0>
  }
  ```

user_prompt_template: |
  ## TaskMaster情報
  - 名前: {task_name}
  - 説明: {task_description}
  - 推奨API: {recommended_apis}

  ## 入力スキーマ
  ```json
  {input_schema}
  ```

  ## 出力スキーマ
  ```json
  {output_schema}
  ```

  ## 生成されたワークフローYAML
  ```yaml
  {yaml_content}
  ```

  ## サンプル入力（テストデータ）
  ```json
  {sample_input}
  ```

  ※ このテストデータは{test_data_source}で生成されました。
  ※ テストデータ再生成回数: {test_data_regeneration_count}

  ## 実行結果
  ```json
  {execution_result}
  ```

  ## ルールベース検証の問題点
  {rule_based_issues}

  上記を評価し、JSON形式で結果を返してください。
  特にテストデータの品質を厳密に評価し、不適切な場合は適切なテストデータを提案してください。
```

#### 3.2.6 実装

```python
# nodes/llm_evaluator.py

async def llm_evaluator_node(
    state: WorkflowGeneratorState,
) -> WorkflowGeneratorState:
    """LLMによるワークフロー品質評価ノード。

    Args:
        state: 現在のワークフロー生成状態

    Returns:
        LLM評価結果を含む更新された状態
    """
    logger.info("Starting LLM evaluator node")

    # 入力データの構築
    evaluator_input = _build_evaluator_input(state)

    # LLM呼び出し
    evaluation_result = await _call_llm_evaluator(evaluator_input)

    # 結果の検証とフォールバック
    if evaluation_result is None:
        logger.warning("LLM evaluation failed, using fallback")
        evaluation_result = _create_fallback_evaluation(state)

    # テストデータ再生成判定
    needs_regeneration = (
        evaluation_result.needs_test_data_regeneration
        and state.get("test_data_regeneration_count", 0) < state.get("max_test_data_regeneration", 2)
    )

    # 合格判定ロジック（テストデータ品質も考慮）
    is_acceptable = (
        evaluation_result.overall_score >= 70
        and evaluation_result.requirement_score >= 60
        and evaluation_result.test_data_quality_score >= 50  # テストデータ最低基準
        and not needs_regeneration
    )

    return {
        **state,
        "llm_evaluation_result": evaluation_result.model_dump(),
        "evaluation_score": evaluation_result.overall_score,
        "evaluation_feedback": _format_feedback(evaluation_result),
        "evaluation_suggestions": evaluation_result.suggestions,
        "test_data_quality_score": evaluation_result.test_data_quality_score,
        "test_data_issues": evaluation_result.test_data_issues,
        "needs_test_data_regeneration": needs_regeneration,
        "suggested_test_data": evaluation_result.suggested_test_data,
        "is_valid": state.get("is_valid", False) and is_acceptable,
    }
```

### 3.3 Test Data Regenerator Node (NEW)

#### 3.3.1 概要

テストデータの品質が低い場合に、LLMを使用して適切なテストデータを再生成するノード。

#### 3.3.2 入力データ

```python
@dataclass
class TestDataRegeneratorInput:
    """Test Data Regenerator への入力データ"""

    # TaskMaster情報
    task_name: str
    task_description: str
    input_schema: dict[str, Any]
    recommended_apis: list[str]

    # 前回のテストデータとその問題点
    previous_sample_input: dict[str, Any]
    test_data_issues: list[str]

    # LLMからの提案（あれば使用）
    suggested_test_data: dict[str, Any] | None
```

#### 3.3.3 出力データ

```python
class RegeneratedTestData(BaseModel):
    """再生成されたテストデータ"""

    sample_input: dict[str, Any]  # 新しいサンプル入力
    generation_rationale: str  # 生成理由の説明
    expected_behavior: str  # このデータで期待される動作
```

#### 3.3.4 プロンプト設計

```yaml
# prompts/test_data_regeneration.yaml

system_prompt: |
  あなたはテストデータ生成のエキスパートです。
  与えられたタスク情報と入力スキーマに基づいて、
  適切で現実的なテストデータを生成してください。

  ## テストデータ生成のガイドライン

  1. **現実性**: 実際のビジネスシーンで使われるようなデータを生成
     - 企業名なら実在しそうな企業名（例: "トヨタ自動車株式会社"）
     - 住所なら実在しそうな住所形式
     - 日付なら妥当な日付

  2. **スキーマ準拠**: 入力スキーマの全ての制約を満たす
     - 必須フィールドは必ず含める
     - 型制約を守る
     - enum制約があれば有効な値を使用

  3. **API互換性**: 推奨APIが受け付けるデータ形式
     - 外部APIの仕様を考慮
     - 存在チェックがあるAPIの場合、存在しうる値を使用

  4. **テスト有効性**: ワークフローを適切にテストできるデータ
     - 正常系をテストできる値
     - 処理の全パスを通過できる値

  ## 出力形式
  ```json
  {
    "sample_input": { ... },
    "generation_rationale": "このデータを生成した理由",
    "expected_behavior": "このデータで期待される動作"
  }
  ```

user_prompt_template: |
  ## タスク情報
  - 名前: {task_name}
  - 説明: {task_description}
  - 推奨API: {recommended_apis}

  ## 入力スキーマ
  ```json
  {input_schema}
  ```

  ## 前回のテストデータ（問題あり）
  ```json
  {previous_sample_input}
  ```

  ## 前回のテストデータの問題点
  {test_data_issues}

  ## LLMからの提案（参考）
  ```json
  {suggested_test_data}
  ```

  上記を踏まえて、適切なテストデータを生成してください。
```

#### 3.3.5 実装

```python
# nodes/test_data_regenerator.py

async def test_data_regenerator_node(
    state: WorkflowGeneratorState,
) -> WorkflowGeneratorState:
    """テストデータ再生成ノード。

    Args:
        state: 現在のワークフロー生成状態

    Returns:
        再生成されたテストデータを含む更新された状態
    """
    logger.info("Starting test data regenerator node")

    current_count = state.get("test_data_regeneration_count", 0)
    max_count = state.get("max_test_data_regeneration", 2)

    if current_count >= max_count:
        logger.warning(f"Max test data regeneration count ({max_count}) reached")
        return {
            **state,
            "needs_test_data_regeneration": False,
            "status": "test_data_regeneration_exhausted",
        }

    # LLMからの提案があればそれを優先使用
    suggested_data = state.get("suggested_test_data")
    if suggested_data:
        logger.info("Using LLM suggested test data")
        new_sample_input = suggested_data
    else:
        # LLMで新規生成
        regenerator_input = _build_regenerator_input(state)
        regenerated = await _call_llm_regenerator(regenerator_input)
        new_sample_input = regenerated.sample_input

    logger.info(f"Regenerated test data: {new_sample_input}")

    return {
        **state,
        "sample_input": new_sample_input,
        "regenerated_sample_input": new_sample_input,
        "test_data_regeneration_count": current_count + 1,
        "needs_test_data_regeneration": False,
        "status": "test_data_regenerated",
    }
```

### 3.4 Result Summary Generator Node

#### 3.4.1 サマリ構造

```python
class ValidationSummary(BaseModel):
    """検証結果サマリ"""

    # 基本情報
    task_master_id: str
    task_name: str
    workflow_name: str
    generated_at: str

    # 検証ステータス
    overall_status: Literal["success", "partial", "failed"]

    # ルールベース検証結果
    rule_based_validation: RuleBasedValidationSummary

    # LLM評価結果
    llm_evaluation: LLMEvaluationSummary

    # テストデータ品質 (NEW)
    test_data_evaluation: TestDataEvaluationSummary

    # 統合スコア
    final_score: int  # 0-100

    # 推奨アクション
    recommended_actions: list[str]

    # リトライ情報
    retry_count: int
    max_retry: int
    test_data_regeneration_count: int  # NEW
    max_test_data_regeneration: int  # NEW


class TestDataEvaluationSummary(BaseModel):
    """テストデータ評価サマリ"""

    quality_score: int
    source: Literal["auto_generated", "llm_regenerated"]
    issues: list[str]
    regeneration_history: list[dict[str, Any]]
```

#### 3.4.2 Markdown サマリ出力

```markdown
# Workflow Validation Summary

## 基本情報
| 項目 | 値 |
|------|-----|
| TaskMaster ID | tm_01ABC123 |
| タスク名 | 企業情報取得 |
| ワークフロー名 | workflow_tm_01ABC123 |
| 生成日時 | 2024-12-24 10:30:00 |

## 検証結果サマリ

### 総合判定: ✅ 成功 (スコア: 85/100)

### ルールベース検証
| 検証項目 | 結果 | 詳細 |
|---------|------|------|
| YAML構文 | ✅ Pass | 構文エラーなし |
| HTTP実行 | ✅ Pass | ステータス 200 |
| GraphAI実行 | ✅ Pass | エラーなし |
| 出力スキーマ | ✅ Pass | 必須フィールド存在 |

### LLM評価
| 観点 | スコア | コメント |
|------|--------|---------|
| 構造的妥当性 | 90/100 | ノード構成が適切 |
| 要件充足度 | 85/100 | 推奨APIを正しく使用 |
| 出力品質 | 80/100 | 期待通りの出力 |
| エラー耐性 | 75/100 | 基本的なエラー処理あり |
| **テストデータ品質** | 85/100 | 現実的なデータを使用 |

### テストデータ評価 (NEW)
| 項目 | 値 |
|------|-----|
| 品質スコア | 85/100 |
| データソース | LLM再生成 (2回目) |
| 再生成回数 | 1回 |

#### テストデータ履歴
| 回数 | データ | 問題点 | 結果 |
|------|--------|--------|------|
| 初回 | `{"company_name": "sample_text"}` | 非現実的なデータ | ❌ 再生成 |
| 2回目 | `{"company_name": "トヨタ自動車"}` | - | ✅ 成功 |

### 良い点
- ノード構成がシンプルで理解しやすい
- 入出力スキーマに準拠している
- 推奨APIを効果的に活用している
- **テストデータが現実的で適切**

### 改善提案
1. エラー時のリトライロジックを追加
2. タイムアウト設定の明示化を推奨

## リトライ履歴
| 種別 | 回数 | 結果 | 詳細 |
|------|------|------|------|
| ワークフロー再生成 | 1 | ❌ → ✅ | YAML構文エラー修正 |
| テストデータ再生成 | 1 | ❌ → ✅ | 現実的なデータに変更 |

---
*Generated by Workflow Generator v2.0*
```

---

## 4. Router 変更

### 4.1 新しいルーティングロジック

```python
def llm_evaluator_router(
    state: WorkflowGeneratorState,
) -> Literal["test_data_regenerator", "result_summary_generator", "self_repair"]:
    """LLM Evaluator 後のルーティング。

    ルーティングロジック:
    1. テストデータ再生成が必要 & 再生成可能 → test_data_regenerator
    2. ワークフロー品質不足 → self_repair
    3. それ以外 → result_summary_generator
    """
    needs_test_data_regeneration = state.get("needs_test_data_regeneration", False)
    test_data_regen_count = state.get("test_data_regeneration_count", 0)
    max_test_data_regen = state.get("max_test_data_regeneration", 2)

    # テストデータ再生成が必要かつ可能
    if needs_test_data_regeneration and test_data_regen_count < max_test_data_regen:
        logger.info("Test data quality insufficient, regenerating")
        return "test_data_regenerator"

    # ルールベース検証失敗
    is_rule_valid = state.get("is_valid", False)
    if not is_rule_valid:
        return "self_repair"

    # LLM評価スコア不足（テストデータ以外の問題）
    evaluation_result = state.get("llm_evaluation_result", {})
    failure_reason = evaluation_result.get("failure_reason", "none")

    if failure_reason in ("workflow_quality", "both"):
        logger.info("Workflow quality insufficient, self-repairing")
        return "self_repair"

    evaluation_score = state.get("evaluation_score", 0)
    if evaluation_score < 70:
        logger.info(f"LLM evaluation score ({evaluation_score}) below threshold")
        return "self_repair"

    return "result_summary_generator"


def test_data_regenerator_router(
    state: WorkflowGeneratorState,
) -> Literal["workflow_tester"]:
    """Test Data Regenerator 後のルーティング。

    常に workflow_tester へ戻って再テスト
    """
    return "workflow_tester"
```

### 4.2 更新されたグラフ定義

```python
def create_workflow_generator_graph() -> Any:
    """更新されたLangGraphワークフロー"""

    workflow = StateGraph(WorkflowGeneratorState)

    # ノード追加
    workflow.add_node("generator", generator_node)
    workflow.add_node("sample_input_generator", sample_input_generator_node)
    workflow.add_node("workflow_tester", workflow_tester_node)
    workflow.add_node("validator", validator_node)
    workflow.add_node("llm_evaluator", llm_evaluator_node)  # NEW
    workflow.add_node("test_data_regenerator", test_data_regenerator_node)  # NEW
    workflow.add_node("result_summary_generator", result_summary_generator_node)  # NEW
    workflow.add_node("self_repair", self_repair_node)

    # エッジ定義
    workflow.set_entry_point("generator")
    workflow.add_edge("generator", "sample_input_generator")
    workflow.add_edge("sample_input_generator", "workflow_tester")
    workflow.add_edge("workflow_tester", "validator")
    workflow.add_edge("validator", "llm_evaluator")

    # LLM Evaluator からの条件分岐
    workflow.add_conditional_edges(
        "llm_evaluator",
        llm_evaluator_router,
        {
            "test_data_regenerator": "test_data_regenerator",
            "result_summary_generator": "result_summary_generator",
            "self_repair": "self_repair",
        },
    )

    # Test Data Regenerator → Workflow Tester (再テスト)
    workflow.add_edge("test_data_regenerator", "workflow_tester")

    # Result Summary → END
    workflow.add_edge("result_summary_generator", END)

    # Self-Repair からの条件分岐
    workflow.add_conditional_edges(
        "self_repair",
        self_repair_router,
        {
            "generator": "generator",
            "END": END,
        },
    )

    return workflow.compile()
```

---

## 5. 設定オプション

### 5.1 環境変数

```bash
# LLM Evaluator 設定
LLM_EVALUATOR_ENABLED=true           # LLM評価の有効/無効
LLM_EVALUATOR_MODEL=gpt-4o-mini      # 評価に使用するモデル
LLM_EVALUATOR_THRESHOLD=70           # 合格スコア閾値
LLM_EVALUATOR_TIMEOUT=30             # タイムアウト秒数

# Test Data Quality 設定 (NEW)
TEST_DATA_QUALITY_THRESHOLD=50       # テストデータ品質の最低基準
MAX_TEST_DATA_REGENERATION=2         # テストデータ最大再生成回数
TEST_DATA_REGENERATOR_MODEL=gpt-4o-mini  # 再生成に使用するモデル

# Result Summary 設定
RESULT_SUMMARY_ENABLED=true          # サマリ生成の有効/無効
RESULT_SUMMARY_FORMAT=markdown       # 出力形式 (markdown|json)
```

### 5.2 Pydantic Settings

```python
# core/config.py への追加

class LLMEvaluatorSettings(BaseModel):
    """LLM Evaluator 設定"""
    enabled: bool = Field(default=True)
    model: str = Field(default="gpt-4o-mini")
    threshold: int = Field(default=70, ge=0, le=100)
    timeout: int = Field(default=30, ge=1)

class TestDataRegeneratorSettings(BaseModel):
    """Test Data Regenerator 設定"""
    quality_threshold: int = Field(default=50, ge=0, le=100)
    max_regeneration: int = Field(default=2, ge=1, le=5)
    model: str = Field(default="gpt-4o-mini")

class ResultSummarySettings(BaseModel):
    """Result Summary 設定"""
    enabled: bool = Field(default=True)
    format: Literal["markdown", "json"] = Field(default="markdown")
```

---

## 6. テスト計画

### 6.1 単体テスト

| テストケース | 内容 | 期待結果 |
|-------------|------|---------|
| `test_llm_evaluator_high_score` | 高品質YAMLの評価 | score >= 80, is_acceptable=True |
| `test_llm_evaluator_low_score` | 低品質YAMLの評価 | score < 70, is_acceptable=False |
| `test_llm_evaluator_timeout` | LLM応答タイムアウト | フォールバック評価が返る |
| `test_llm_evaluator_invalid_response` | 不正なLLM応答 | フォールバック評価が返る |
| `test_test_data_quality_high` | 高品質テストデータ | test_data_quality_score >= 80 |
| `test_test_data_quality_low` | 低品質テストデータ ("sample_text") | needs_regeneration=True |
| `test_test_data_regenerator_success` | テストデータ再生成成功 | 現実的なデータが生成される |
| `test_test_data_regenerator_max_count` | 最大再生成回数到達 | status="exhausted" |
| `test_result_summary_success` | 成功ケースのサマリ生成 | status="success" |
| `test_result_summary_with_regeneration` | 再生成履歴付きサマリ | 履歴が含まれる |
| `test_markdown_generation` | Markdownサマリ生成 | 正しいMarkdown形式 |

### 6.2 結合テスト

| テストケース | 内容 | 期待結果 |
|-------------|------|---------|
| `test_full_flow_with_evaluation` | 全フロー実行 | サマリが生成される |
| `test_retry_after_low_score` | 低スコア後のリトライ | self_repairが呼ばれる |
| `test_test_data_regeneration_flow` | テストデータ再生成フロー | 再生成→再テスト→成功 |
| `test_test_data_regeneration_then_workflow_repair` | 再生成後もワークフロー不備 | self_repairが呼ばれる |
| `test_disabled_evaluation` | 評価無効時 | validator → END |

### 6.3 実践的受入テスト（L3/L4）

> **重要**: モックテストだけでは実データ形式との不整合を検出できない。
> 実際に発見されたバグ例: `recommended_apis: list[dict]` 形式で `TypeError` 発生

#### 6.3.1 実データ形式テスト

| テストケース | 内容 | 期待結果 |
|-------------|------|---------|
| `test_create_prompt_with_dict_recommended_apis` | `recommended_apis: list[dict]` 形式でプロンプト生成 | 正常にAPI名が抽出される |
| `test_create_prompt_with_mixed_recommended_apis` | 混在形式（str + dict）でプロンプト生成 | 正常に処理される |
| `test_llm_evaluator_with_real_task_data` | 実際のTaskMasterデータ形式を使用 | TypeErrorなく処理完了 |

```python
# tests/unit/test_llm_evaluation_prompt.py

def test_create_prompt_with_dict_recommended_apis():
    """recommended_apis が list[dict] 形式でも動作することを確認"""
    prompt = create_llm_evaluation_prompt(
        task_name="テストタスク",
        task_description="説明",
        input_schema={},
        output_schema={},
        recommended_apis=[
            {"name": "gmail_api", "endpoint": "/api/v1/gmail"},
            {"name": "drive_api", "endpoint": "/api/v1/drive"},
        ],  # 実際のデータ形式
        yaml_content="version: 0.5",
        sample_input={},
        execution_result=None,
        rule_based_issues=[],
    )
    assert "gmail_api" in prompt
    assert "drive_api" in prompt
```

#### 6.3.2 E2Eテスト（フロントエンド→バックエンド）

| テストケース | 内容 | 期待結果 |
|-------------|------|---------|
| `test_workflow_generation_completes_within_timeout` | 生成が5分以内に完了 | success または明確なエラー |
| `test_generation_progress_updates` | 進捗状況がUIに反映 | phase/progressが更新される |
| `test_generation_failure_displays_error` | 失敗時にエラー表示 | 具体的なエラーメッセージ表示 |

```typescript
// tests/e2e/generate-workflow.spec.ts

test('ワークフロー生成が5分以内に完了する', async ({ page }) => {
  await page.goto('/projects/xxx/workbenches/yyy/generate');
  await page.click('button:has-text("Generate")');

  // 5分以内に完了または明確なエラーメッセージ
  await expect(page.locator('[data-testid="generation-status"]'))
    .toHaveText(/success|failed/, { timeout: 300000 });
});
```

#### 6.3.3 統合テスト（実LLM API使用）

| テストケース | 内容 | 期待結果 |
|-------------|------|---------|
| `test_llm_evaluator_with_real_api` | 実APIでLLM評価 | 0-100のスコアが返る |
| `test_full_workflow_generation_e2e` | 全フロー実行（モックなし） | ワークフローYAMLが生成される |

```python
# tests/integration/test_llm_evaluator_real.py

@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="No API key")
async def test_llm_evaluator_with_real_api():
    """実際のLLM APIを使用した統合テスト"""
    state = create_test_state_with_real_data()
    result = await llm_evaluator_node(state)

    assert result["evaluation_score"] is not None
    assert 0 <= result["evaluation_score"] <= 100
```

#### 6.3.4 受入テストチェックリスト

```markdown
## 受入テスト確認項目

### L3: ローカル受入テスト
- [ ] 実データ形式でのテスト（recommended_apis: list[dict]）
- [ ] サービス起動確認（expertAgent, graphAiServer）
- [ ] フロントエンドからの生成リクエスト成功確認
- [ ] 5分以内に完了またはエラー返却

### L4: E2Eテスト
- [ ] Playwright による UI 操作テスト
- [ ] タイムアウト動作の確認
- [ ] エラーメッセージの表示確認
- [ ] Langfuseトレースリンクの動作確認
```

---

## 7. 実装スケジュール

### Phase 1: State拡張とモデル定義
- [ ] `state.py` に新フィールド追加（テストデータ関連含む）
- [ ] `LLMEvaluationResult` モデル定義（テストデータ評価含む）
- [ ] `RegeneratedTestData` モデル定義
- [ ] `ValidationSummary` モデル定義（テストデータ履歴含む）

### Phase 2: LLM Evaluator Node 実装
- [ ] プロンプトYAML作成（テストデータ評価観点追加）
- [ ] `llm_evaluator_node` 実装
- [ ] フォールバックロジック実装
- [ ] 単体テスト作成

### Phase 3: Test Data Regenerator Node 実装 (NEW)
- [ ] プロンプトYAML作成
- [ ] `test_data_regenerator_node` 実装
- [ ] LLM提案データ優先使用ロジック実装
- [ ] 単体テスト作成

### Phase 4: Result Summary Generator Node 実装
- [ ] `result_summary_generator_node` 実装
- [ ] Markdownテンプレート作成（テストデータ履歴含む）
- [ ] 単体テスト作成

### Phase 5: グラフ統合
- [ ] `agent.py` のグラフ定義更新
- [ ] 3方向ルーター実装
- [ ] 結合テスト作成

### Phase 6: 設定とドキュメント
- [ ] 環境変数追加
- [ ] Pydantic Settings 更新
- [ ] API Reference 更新

---

## 8. 制約条件チェック結果

### コード品質原則
- [x] SOLID原則: 各ノードは単一責任（テストデータ再生成を分離）
- [x] KISS原則: シンプルなノード構成
- [x] YAGNI原則: 必要最小限の機能のみ
- [x] DRY原則: 共通処理はヘルパー関数化

### アーキテクチャガイドライン
- [x] architecture-overview.md: LangGraphノード設計に準拠
- [x] レイヤー分離: プロンプト/ノード/状態を分離

### 設定管理ルール
- [x] 環境変数: LLM_EVALUATOR_*, TEST_DATA_* で管理
- [x] ユーザー設定: Pydantic Settingsで管理

### 品質担保方針
- [ ] 単体テストカバレッジ: 目標90%以上
- [ ] 結合テストカバレッジ: 目標50%以上
- [ ] Ruff linting: エラーゼロ
- [ ] MyPy type checking: エラーゼロ

---

## 9. リスクと対策

| リスク | 影響度 | 対策 |
|--------|--------|------|
| LLM応答遅延 | 中 | タイムアウト設定、フォールバック |
| LLM評価の不安定性 | 中 | 複数回評価の平均化オプション |
| テストデータ再生成ループ | 中 | 最大再生成回数制限 (default: 2) |
| 再生成データも低品質 | 中 | LLM提案データ優先使用、品質閾値設定 |
| コスト増加 | 低 | 小型モデル(gpt-4o-mini)使用 |
| プロンプトインジェクション | 低 | 入力サニタイズ |

---

## 10. 参考資料

- [既存Validator実装](../../expertAgent/aiagent/langgraph/workflowGeneratorAgents/nodes/validator.py)
- [既存Sample Input Generator実装](../../expertAgent/aiagent/langgraph/workflowGeneratorAgents/nodes/sample_input_generator.py)
- [WorkflowGeneratorState定義](../../expertAgent/aiagent/langgraph/workflowGeneratorAgents/state.py)
- [LangGraph公式ドキュメント](https://langchain-ai.github.io/langgraph/)
- [GraphAI Workflow Generation Rules](../../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)
