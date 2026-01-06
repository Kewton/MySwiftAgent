# 設計方針書: Issue #338 タスクチェーン インターフェース契約強制メカニズム

**作成日**: 2026-01-06
**Issue**: [#338 Task Chain Interface Contract Enforcement](https://github.com/Kewton/MySwiftAgent/issues/338)
**関連Issue**: #337, #340

---

## 現状調査サマリ

### 対象プロジェクト

- **プロジェクト名**: expertAgent
- **主要モジュール**:
  - `aiagent/langgraph/workflowGeneratorAgents/` - GraphAIワークフロー生成
  - `aiagent/langgraph/jobTaskGeneratorAgents/` - Job/Task生成
- **関連サービス**: graphAiServer, jobqueue

### 既存アーキテクチャパターン

| パターン | 使用箇所 | 目的 |
|---------|---------|------|
| **LangGraph StateGraph** | `agent.py` | 状態遷移ベースのワークフロー実行 |
| **Router Pattern** | `*_router()` 関数群 | 条件分岐による動的ルーティング |
| **Pydantic BaseModel** | `models/`, `state.py` | スキーマ定義・バリデーション |
| **Node Pattern** | `nodes/*.py` | 単一責任の処理ユニット |
| **Prompt Engineering** | `prompts/*.py` | LLM向けプロンプト生成 |

### 類似機能の設計

| 機能 | 設計概要 |
|------|---------|
| `evaluator_node` (jobTaskGenerator) | LLMによる実現可能性評価、`check_interface_compatibility()` 関数 |
| `llm_evaluator_node` (workflowGenerator) | LLMによるワークフロー品質評価、スコアベース合否判定 |
| `schema_enrichment_node` | OpenAPI仕様との照合・補完 |
| `validation_node` | ルールベース検証 |

### モジュール間依存関係

```
expertAgent
├── aiagent/langgraph/
│   ├── jobTaskGeneratorAgents/     # Job/Task生成
│   │   ├── agent.py               # LangGraph定義
│   │   ├── nodes/                 # 処理ノード
│   │   │   ├── evaluator.py      # 実現可能性評価
│   │   │   └── ...
│   │   └── prompts/              # LLMプロンプト
│   │
│   └── workflowGeneratorAgents/   # ワークフロー生成
│       ├── agent.py              # LangGraph定義
│       ├── nodes/
│       │   ├── generator.py      # YAML生成
│       │   ├── llm_evaluator.py  # 品質評価
│       │   └── ...
│       └── prompts/
│
└── app/api/v1/                   # REST API
    └── job_generator_endpoints.py
```

### 既存API設計パターン

- **エンドポイント命名規則**: `/v1/{resource}` (RESTful)
- **レスポンス形式**: JSON (`{"status": ..., "result": ...}`)
- **エラーハンドリング**: HTTPステータス + `error_message` フィールド

### 参照したドキュメント

| ドキュメント | 関連内容 |
|------------|---------|
| `docs/spec/job-generation-workflow.md` | LangGraph 7段階ワークフロー設計 |
| `docs/arch/service-dependencies.md` | サービス間通信フロー |
| `docs/design/architecture-overview.md` | 4層アーキテクチャ |
| `root-cause-analysis.md` | 6つの真因と改善提案 |

### 設計上の制約

1. **後方互換性**: 既存APIインターフェースを維持
2. **LangGraph互換**: StateGraph/Router パターンに準拠
3. **非破壊的変更**: 既存ワークフローの動作を保証
4. **テストカバレッジ**: 単体90%/結合50%維持

---

## アーキテクチャ設計

### システム構成図

```mermaid
graph TB
    subgraph "Workflow Generator (改善対象)"
        GEN[generator_node]
        COMP[completeness_validator]
        SCHEMA[schema_validator_node]
        TEST[workflow_tester_node]
        SAMPLE[sample_input_generator_node]
        EVAL[llm_evaluator_node]
        REPAIR[self_repair_node]
    end

    subgraph "新規追加コンポーネント"
        CV[Critical Weakness<br/>Validator]
        IC[Interface Contract<br/>Validator]
        TV[Type Validator]
    end

    subgraph "Routing Layer (改善対象)"
        R1[schema_validator_router]
        R2[llm_evaluator_router]
        R3[self_repair_router]
    end

    GEN --> COMP
    COMP --> SCHEMA
    SCHEMA --> R1
    R1 -->|valid| TEST
    R1 -->|invalid| REPAIR

    TEST --> SAMPLE
    SAMPLE --> EVAL
    EVAL --> CV
    CV --> R2
    R2 -->|pass| SUCCESS[result_summary]
    R2 -->|fail| REPAIR

    REPAIR --> R3
    R3 -->|retry| GEN
    R3 -->|max_retry| END[END]

    IC -.->|Phase 1-B| EVAL
    TV -.->|Phase 2-C| GEN
```

### レイヤー構成

| レイヤー | 責務 | 改善対象 |
|---------|------|---------|
| **Routing Layer** | 条件分岐ロジック | `llm_evaluator_router` の改善 |
| **Validation Layer** | 検証ロジック | Critical Weakness検出、型検証 |
| **Generation Layer** | LLM呼び出し・YAML生成 | プロンプト改善 |
| **State Layer** | 状態管理 | `is_acceptable` フラグ伝播 |

---

## 技術選定

| カテゴリ | 選定技術 | 選定理由 | 既存との整合性 |
|---------|---------|---------|---------------|
| **状態管理** | LangGraph TypedDict | 型安全な状態定義 | 既存パターン踏襲 |
| **バリデーション** | Pydantic v2 | スキーマ検証 | 既存パターン踏襲 |
| **ルーティング** | 関数ベースRouter | 条件分岐の明示化 | 既存パターン踏襲 |
| **テスト** | pytest + pytest-asyncio | 非同期テスト対応 | 既存パターン踏襲 |
| **型チェック** | `isinstance()` + Union types | ランタイム型検証 | Python標準 |

---

## 設計パターン

### 採用パターン

#### 1. Strategy Pattern (評価戦略)

**目的**: Critical Weakness検出ロジックの差し替え可能化

```python
# 既存パターン: 単純なスコア閾値
if evaluation_score < 70:
    return "self_repair"

# 新規: Strategy Patternによる複合評価
class EvaluationStrategy(Protocol):
    def should_reject(self, result: LLMEvaluationResult) -> bool: ...

class CriticalWeaknessStrategy:
    def should_reject(self, result: LLMEvaluationResult) -> bool:
        return any("Critical" in w for w in result.weaknesses)

class CompositeStrategy:
    def __init__(self, strategies: list[EvaluationStrategy]):
        self.strategies = strategies

    def should_reject(self, result: LLMEvaluationResult) -> bool:
        return any(s.should_reject(result) for s in self.strategies)
```

**既存パターンとの整合性**: `evaluator_node` の `check_interface_compatibility()` と同様の関数分離パターン

#### 2. Chain of Responsibility (検証チェーン)

**目的**: 複数の検証ロジックを順次適用

```python
# 既存: 単一ルーターで複数条件チェック
def llm_evaluator_router(state):
    if needs_test_data_regeneration:
        return "test_data_regenerator"
    if not is_rule_valid:
        return "self_repair"
    if failure_reason in ("workflow_quality", "both"):
        return "self_repair"
    if evaluation_score < 70:
        return "self_repair"
    return "result_summary_generator"

# 新規: 検証チェーンの明示化
validators = [
    TestDataRegenerationValidator(),
    RuleBasedValidator(),
    CriticalWeaknessValidator(),  # 新規追加
    AcceptabilityValidator(),      # 新規追加
    ScoreThresholdValidator(),
]
```

#### 3. Type Guard Pattern (型検証)

**目的**: `recommended_apis` の型安全性確保

```python
# 真因2-C対応: 型ガード関数
def normalize_api_item(api: str | dict) -> dict[str, str]:
    """Normalize API item to dict format."""
    if isinstance(api, str):
        return {"api_name": api, "endpoint": api}
    if isinstance(api, dict):
        return {
            "api_name": api.get("api_name") or api.get("name") or "",
            "endpoint": api.get("endpoint") or "",
        }
    raise TypeError(f"Expected str or dict, got {type(api)}")
```

---

## データモデル設計

### ER図 (State拡張)

```mermaid
erDiagram
    WorkflowGeneratorState ||--|| EvaluationResult : has
    EvaluationResult ||--o{ Weakness : contains
    EvaluationResult ||--o| CriticalStatus : has

    WorkflowGeneratorState {
        str yaml_content
        dict task_data
        dict sample_input
        bool is_valid
        bool is_acceptable "新規追加"
        int evaluation_score
    }

    EvaluationResult {
        int overall_score
        list weaknesses
        str failure_reason
        bool has_critical "新規追加"
    }

    Weakness {
        str severity "Critical/Warning/Info"
        str message
        str suggestion
    }

    CriticalStatus {
        bool detected
        list critical_issues
    }
```

### State拡張

```python
class WorkflowGeneratorState(TypedDict):
    # 既存フィールド
    yaml_content: str
    task_data: dict
    sample_input: dict | str | None
    is_valid: bool
    evaluation_score: int
    llm_evaluation_result: dict

    # 新規追加フィールド (Phase 4)
    is_acceptable: bool  # 真因2-B対応
    has_critical_weakness: bool  # 真因2-A対応
    critical_issues: list[str]  # 真因2-A対応
```

---

## API設計

### 既存APIへの影響

**変更なし** - 内部実装のみの改善

### 内部インターフェース変更

#### llm_evaluator_router (改善)

```python
def llm_evaluator_router(
    state: WorkflowGeneratorState,
) -> Literal["test_data_regenerator", "self_repair", "result_summary_generator"]:
    """
    改善点:
    1. is_acceptable フラグを判定に使用 (真因2-B)
    2. Critical weakness検出で自動失敗 (真因2-A)
    """
    # 既存ロジック
    needs_test_data_regeneration = state.get("needs_test_data_regeneration", False)
    if needs_test_data_regeneration:
        return "test_data_regenerator"

    is_rule_valid = state.get("is_valid", False)
    if not is_rule_valid:
        return "self_repair"

    # 新規: is_acceptable フラグを使用 (真因2-B)
    is_acceptable = state.get("is_acceptable", True)
    if not is_acceptable:
        logger.info("Workflow not acceptable (is_acceptable=False), routing to self_repair")
        return "self_repair"

    # 新規: Critical weakness検出 (真因2-A)
    has_critical = state.get("has_critical_weakness", False)
    if has_critical:
        logger.info("Critical weakness detected, routing to self_repair")
        return "self_repair"

    # 既存ロジック継続
    evaluation_result = state.get("llm_evaluation_result") or {}
    failure_reason = evaluation_result.get("failure_reason", "none")
    if failure_reason in ("workflow_quality", "both"):
        return "self_repair"

    evaluation_score = state.get("evaluation_score") or 0
    if evaluation_score < 70:
        return "self_repair"

    return "result_summary_generator"
```

---

## セキュリティ設計

**変更なし** - 既存のセキュリティ実装を継続

---

## パフォーマンス設計

### 検証処理の最適化

| 項目 | 現状 | 改善後 |
|------|------|--------|
| Critical検出 | LLM判断のみ | プログラム的検出追加 |
| 型検証 | 実行時エラー | 事前検証 |
| 早期終了 | スコア閾値のみ | 複合条件で早期終了 |

### 期待される効果

- **不要なリトライ削減**: Critical検出で早期終了
- **ランタイムエラー削減**: 型検証で事前検出
- **評価精度向上**: 複合評価による誤判定削減

---

## 設計判断とトレードオフ

### 判断1: Critical Weakness の検出方法

| 選択肢 | メリット | デメリット | 採用 |
|--------|---------|-----------|------|
| **A. LLMに`failure_reason`設定を強制** | 変更少 | LLM依存度高 | - |
| **B. プログラム的に`weaknesses`を解析** | 確実 | 文字列マッチング | 採用 |
| **C. 新規フィールド`has_critical`追加** | 明示的 | 既存LLMプロンプト変更必要 | - |

**採用理由**: 選択肢Bは既存のLLMレスポンスを変更せず、確実に検出可能

```python
def _has_critical_weakness(weaknesses: list[str]) -> bool:
    """Check if any weakness contains 'Critical' keyword."""
    critical_patterns = ["Critical", "CRITICAL", "critical", "致命的"]
    return any(
        any(pattern in w for pattern in critical_patterns)
        for w in weaknesses
    )
```

### 判断2: is_acceptable フラグの伝播

| 選択肢 | メリット | デメリット | 採用 |
|--------|---------|-----------|------|
| **A. State に新規フィールド追加** | 明示的 | State変更 | 採用 |
| **B. llm_evaluation_result 内で計算** | 変更少 | 責務混在 | - |

**採用理由**: 選択肢Aは責務が明確で、テストが容易

### 判断3: 型バリデーションの実装箇所

| 選択肢 | メリット | デメリット | 採用 |
|--------|---------|-----------|------|
| **A. 各利用箇所でガード** | 局所的 | 重複コード | - |
| **B. ユーティリティ関数で一元化** | DRY | 呼び出し漏れリスク | 採用 |
| **C. Pydantic Validatorで強制** | 自動 | State変更大 | - |

**採用理由**: 選択肢Bは既存コードへの影響最小でDRY原則に準拠

---

## 実装フェーズ

### Phase 4: 評価ルーティングの改善 (高優先度)

| タスク | 対象ファイル | 内容 |
|--------|------------|------|
| 4-1 | `llm_evaluator.py` | `_has_critical_weakness()` 関数追加 |
| 4-2 | `llm_evaluator.py` | `has_critical_weakness` をStateに設定 |
| 4-3 | `agent.py` | `llm_evaluator_router` でis_acceptable使用 |
| 4-4 | `state.py` | `is_acceptable`, `has_critical_weakness` フィールド追加 |
| 4-5 | `tests/unit/` | 単体テスト追加 |

### Phase 5: 型バリデーション強化 (高優先度)

| タスク | 対象ファイル | 内容 |
|--------|------------|------|
| 5-1 | `utils/type_guards.py` | `normalize_api_item()` 関数作成 |
| 5-2 | `nodes/*.py` | 各ノードで型ガード適用 |
| 5-3 | `tests/unit/` | 単体テスト追加 |

### Phase 6: 動的配列処理パターン (中優先度)

| タスク | 対象ファイル | 内容 |
|--------|------------|------|
| 6-1 | `prompts/workflow_generation.py` | 配列処理パターンをプロンプトに追加 |
| 6-2 | `tests/unit/` | プロンプトテスト追加 |

### Phase 7: タスクチェーンインターフェース検証 (中優先度)

| タスク | 対象ファイル | 内容 |
|--------|------------|------|
| 7-1 | `nodes/interface_validator.py` | 新規バリデーターノード作成 |
| 7-2 | `agent.py` | グラフにノード追加 |
| 7-3 | `tests/unit/` | 単体テスト追加 |

---

## テスト計画

### 単体テスト

```python
# tests/unit/test_critical_weakness_detection.py
class TestCriticalWeaknessDetection:
    def test_detect_critical_keyword(self):
        weaknesses = ["Critical: Missing output node"]
        assert _has_critical_weakness(weaknesses) is True

    def test_no_critical(self):
        weaknesses = ["Warning: Consider adding error handling"]
        assert _has_critical_weakness(weaknesses) is False

    def test_japanese_critical(self):
        weaknesses = ["致命的: 出力ノードがありません"]
        assert _has_critical_weakness(weaknesses) is True
```

### 結合テスト

```python
# tests/integration/test_issue_338_routing.py
class TestIssue338Routing:
    async def test_critical_weakness_triggers_self_repair(self):
        """Critical weaknessが検出された場合、self_repairにルーティングされる"""
        state = {
            "evaluation_score": 72,  # 閾値以上
            "llm_evaluation_result": {
                "weaknesses": ["Critical: Output node missing search_results"],
                "failure_reason": "none",  # LLMはnoneを返す
            },
            "is_valid": True,
        }
        result = llm_evaluator_router(state)
        assert result == "self_repair"

    async def test_is_acceptable_false_triggers_self_repair(self):
        """is_acceptable=Falseの場合、self_repairにルーティングされる"""
        state = {
            "evaluation_score": 72,
            "is_acceptable": False,  # 新規フラグ
            "is_valid": True,
        }
        result = llm_evaluator_router(state)
        assert result == "self_repair"
```

---

## 参照ドキュメント

- [Issue #338](https://github.com/Kewton/MySwiftAgent/issues/338)
- [root-cause-analysis.md](./root-cause-analysis.md)
- [job-generation-workflow.md](../../../docs/spec/job-generation-workflow.md)
- [service-dependencies.md](../../../docs/arch/service-dependencies.md)
- [GRAPHAI_WORKFLOW_GENERATION_RULES.md](../../../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)

---

## 実装状況

| フェーズ | 状態 | 完了日 |
|---------|------|--------|
| Phase 4: 評価ルーティング改善 | ✅ 完了 | 2026-01-06 |
| Phase 5: 型バリデーション強化 | ✅ 完了 | 2026-01-06 |
| Phase 6: 動的配列処理パターン | ✅ 完了 | 2026-01-06 |
| Phase 7: タスクチェーンIF検証 | ✅ 完了 | 2026-01-06 |

### Phase 4 実装詳細

**変更ファイル:**
- `state.py`: `is_acceptable`, `has_critical_weakness`, `critical_issues` フィールド追加
- `llm_evaluator.py`: `_has_critical_weakness()` 関数追加、`llm_evaluator_node` で新フィールド設定
- `agent.py`: `llm_evaluator_router` に `is_acceptable` と `has_critical_weakness` チェック追加

**追加テスト:**
- `test_llm_evaluator_node.py`: `TestHasCriticalWeakness` (8テスト), `TestLLMEvaluatorNodeCriticalWeakness` (3テスト)
- `test_llm_evaluator_routers.py`: `TestIssue338CriticalWeaknessRouting` (5テスト)
- `test_issue_338_critical_weakness_routing.py`: 結合テスト (7テスト)

### Phase 5 実装詳細

**対応した真因:** 真因2-C (型バリデーション不足)

**新規ファイル:**
- `utils/type_guards.py`: 型ガード関数モジュール
  - `normalize_api_item()`: str/dict を統一形式に変換
  - `normalize_recommended_apis()`: APIリストを正規化
  - `get_api_name()`, `get_api_endpoint()`: 安全なアクセサ
  - `format_apis_comma_separated()`: プロンプト用フォーマット
  - `format_apis_for_prompt()`: 詳細フォーマット

**変更ファイル:**
- `utils/__init__.py`: 型ガード関数をエクスポート
- `prompts/llm_evaluation.py`: `_format_recommended_apis()` を `format_apis_comma_separated()` に置換
- `prompts/test_data_regeneration.py`: 同上

**追加テスト:**
- `test_type_guards.py`: 39テスト（単体テスト）
- `test_type_guard_integration.py`: 9テスト（結合テスト）
- 既存テスト更新: `test_llm_evaluation_prompt.py`, `test_test_data_regeneration_prompt.py`

### Phase 6 実装詳細

**対応した真因:** 真因1-A (LLMが固定長の配列処理を生成)

**新規定数:**
- `DYNAMIC_ARRAY_PROCESSING_PATTERNS`: 動的配列処理パターンのガイドライン
  - `mapAgent` を使用した均一処理パターン
  - `reduceAgent` を使用した集約パターン
  - ハードコードされた固定長パターンの禁止

**変更ファイル:**
- `prompts/workflow_generation.py`: `DYNAMIC_ARRAY_PROCESSING_PATTERNS` 定数追加、プロンプトに統合

**追加テスト:**
- `test_workflow_generation_prompts.py`:
  - `TestDynamicArrayProcessingPatterns` (7テスト): 定数内容テスト
  - `TestDynamicArrayPatternsIntegration` (3テスト): プロンプト統合テスト

### Phase 7 実装詳細

**対応した真因:** 真因1-B (タスクチェーンのインターフェース不整合)

**新規ファイル:**
- `utils/interface_validator.py`: インターフェース検証モジュール
  - `InterfaceIssue`: 検証問題を表すモデル
  - `InterfaceValidationResult`: 検証結果モデル
  - `validate_interface_compatibility()`: 2タスク間の互換性検証
  - `validate_task_chain_interfaces()`: タスクチェーン全体の検証
  - `format_interface_issues()`: 問題のフォーマット出力

**変更ファイル:**
- `utils/__init__.py`: インターフェース検証関数をエクスポート

**追加テスト:**
- `test_interface_validator.py`: 24テスト（単体テスト）
  - 互換性検証: 必須フィールド欠落、型不一致、互換型
  - タスクチェーン検証: 空チェーン、単一タスク、複数タスク
  - フォーマット: エラー/警告の表示

---

## 変更履歴

| 日付 | バージョン | 変更内容 |
|------|-----------|---------|
| 2026-01-06 | 1.0 | 初版作成 |
| 2026-01-06 | 1.1 | Phase 4 実装完了 |
| 2026-01-06 | 1.2 | Phase 5 実装完了 |
| 2026-01-06 | 1.3 | Phase 6 実装完了 (動的配列処理パターン) |
| 2026-01-06 | 1.4 | Phase 7 実装完了 (インターフェース検証) |
