# V2 LLMワークフロー生成アーキテクチャ設計方針

> **Issue**: #342 (拡張)
> **作成日**: 2026-01-07
> **状態**: レビュー指摘対応済み

## 1. 背景と目的

### 1.1 現状の課題

Issue #342 で Job Generator V2 アーキテクチャを刷新したが、ワークフロー生成部分は V1 の `workflowGeneratorAgents` をそのまま使用している。V2 の `yaml_generator.py` には `generate_with_llm()` メソッドがプレースホルダーとして存在するのみ。

### 1.2 目的

V2 アーキテクチャに統合された新しい LLM ワークフロー生成システムを設計・実装する。

---

## 2. V1の問題分析

### 2.1 アーキテクチャ上の問題

| 問題 | 詳細 | 影響 |
|------|------|------|
| **複雑なグラフ構造** | 10ノード + 5ルーター + 複数の条件分岐 | 保守困難、デバッグ困難 |
| **パッチワーク的修正** | Issue #333, #337, #338, #340 で継ぎ接ぎ | コードの一貫性欠如 |
| **多段階検証** | 6段階の検証プロセス | 実行時間の増大 |
| **LangGraph依存** | LangGraph StateGraph 必須 | テスト困難、依存性問題 |
| **リトライ管理の複雑さ** | retry_count, test_data_regen_count, object_array_regen_count | Issue #342 と同類の問題発生リスク |

### 2.2 V1 ワークフロー構造

```
generator
    ↓
schema_validator ─────────────────────┐
    ↓                                 │
sample_input_generator                │
    ↓                                 │
[sample_input_router]                 │
    ↓                                 │
workflow_tester                       │
    ↓                                 │
validator                             │
    ↓                                 │
[validator_router]                    │
    ↓                                 │
llm_evaluator                         │
    ↓                                 │
[llm_evaluator_router]                │
    ↓                    ↓            │
test_data_regenerator  self_repair ←──┘
    ↓                    ↓
workflow_tester        generator (リトライ)
    ↓                    ↓
   ...                  ...
    ↓
result_summary_generator
    ↓
   END
```

### 2.3 LLM生成の失敗パターン（過去Issue分析）

| Issue | 失敗パターン | 原因 |
|-------|-------------|------|
| **#333** | APIエンドポイント・フィールド名の不一致 | LLMがAPI仕様を理解していない |
| **#337** | copyAgentのネスト参照エラー | データフローパターンの理解不足 |
| **#338** | 出力スキーマの不完全性 | タスクチェーン連携の理解不足 |
| **#340** | オブジェクト配列の型エラー | stringTemplateAgent制約の理解不足 |

### 2.4 根本原因

```
LLMに対するGraphAIルールの伝達が不十分
    ↓
不正なYAML生成
    ↓
検証失敗 → self_repair → 再生成
    ↓
複雑なリトライループ → パフォーマンス低下・無限ループリスク
```

---

## 3. V2 設計方針

### 3.1 基本コンセプト

```
「検証で修正する」から「最初から正しく生成する」へ
```

### 3.2 設計原則

| 原則 | V1 | V2 |
|------|-----|-----|
| **アーキテクチャ** | LangGraph StateGraph | Protocol-based (WorkflowProtocol) |
| **検証戦略** | 生成後の多段階検証 | プロンプト内での制約埋め込み + 軽量検証 |
| **LLM利用** | 生成 + 評価 + 修復 (3回以上) | 生成のみ (1回、リトライ時最大3回) |
| **ルール伝達** | 巨大プロンプト | 構造化Few-shot + 制約セクション |
| **リトライ** | self_repair → generator ループ | ExecutionContext フェーズ別管理 |

### 3.3 アーキテクチャ概要

```
┌─────────────────────────────────────────────────────────────┐
│              WorkflowGenWorkflow (V2)                       │
│                  implements WorkflowProtocol                │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│PromptBuilder  │   │ LLMGenerator  │   │ YamlValidator │
│ SubWorkflow   │   │  SubWorkflow  │   │  SubWorkflow  │
└───────────────┘   └───────────────┘   └───────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│- Few-shot例選択│   │- 構造化出力   │   │- YAML構文検証 │
│- API制約埋込   │   │- 単一LLM呼出  │   │- Agent存在確認│
│- タスク文脈化  │   │- JSON Schema  │   │- 参照解決検証 │
└───────────────┘   └───────────────┘   └───────────────┘
```

### 3.4 モジュラープロンプトアーキテクチャ（修正箇所の局所化）

**設計目標**: 機能改善や不具合修正時に、特定のプロンプト/ファイルのみを修正すれば良い構造

#### プロンプトコンポーネントの分離

```
prompts/
├── __init__.py
├── system/                      # システムプロンプト（役割定義）
│   └── workflow_generator.py    # 「あなたはGraphAIワークフロー生成の専門家です」
│
├── rules/                       # GraphAIルール（制約）
│   ├── base_rules.py           # 基本ルール（version, source, isResult）
│   ├── agent_rules.py          # Agent別制約（stringTemplateAgent等）
│   ├── reference_rules.py      # 参照ルール（:node.path形式）
│   └── api_rules.py            # API呼出ルール（fetchAgent設定）
│
├── constraints/                 # API別制約（動的生成）
│   ├── loader.py               # expert_agent_capabilities.yaml読込
│   └── formatter.py            # 制約文字列フォーマット
│
└── few_shot/                    # Few-shot例
    ├── loader.py               # 例の読み込み・選択ロジック
    ├── search_pattern.yaml     # 検索系パターン
    ├── api_call_pattern.yaml   # API呼出パターン
    ├── map_pattern.yaml        # mapAgent使用パターン
    └── llm_chain_pattern.yaml  # LLMチェーンパターン
```

#### 修正シナリオ別の対応ファイル

| 問題/改善 | 修正ファイル | 影響範囲 |
|----------|-------------|---------|
| **stringTemplateAgentの配列処理エラー** | `rules/agent_rules.py` | Agent制約のみ |
| **copyAgentの参照解決エラー** | `rules/reference_rules.py` | 参照ルールのみ |
| **新しいAPIの追加** | `constraints/loader.py` + capabilities.yaml | API制約のみ |
| **検索系ワークフローの品質向上** | `few_shot/search_pattern.yaml` | 検索パターンのみ |
| **mapAgent使用時のエラー** | `few_shot/map_pattern.yaml` + `rules/agent_rules.py` | 配列処理関連のみ |
| **全体的なYAML品質向上** | `system/workflow_generator.py` | システムプロンプトのみ |

#### プロンプト組み立てフロー

```python
class PromptBuilderSubWorkflow:
    """モジュラープロンプト組み立て"""

    def __init__(self):
        # 各コンポーネントを独立してロード
        self._system_prompt = load_system_prompt()      # prompts/system/
        self._base_rules = load_base_rules()            # prompts/rules/base_rules.py
        self._agent_rules = load_agent_rules()          # prompts/rules/agent_rules.py
        self._reference_rules = load_reference_rules()  # prompts/rules/reference_rules.py
        self._api_rules = load_api_rules()              # prompts/rules/api_rules.py
        self._few_shot_loader = FewShotLoader()         # prompts/few_shot/

    async def build(self, task_definition, interface_schema, context):
        # 1. タスクに必要なルールのみを選択的に組み込み
        relevant_rules = self._select_relevant_rules(task_definition)

        # 2. API固有の制約を動的生成
        api_constraints = await self._build_api_constraints(
            task_definition.recommended_apis
        )

        # 3. 適切なFew-shot例を選択
        examples = self._few_shot_loader.select(task_definition)

        # 4. 最終プロンプト組み立て
        return WorkflowPrompt(
            system=self._system_prompt,
            rules=relevant_rules,           # 必要なルールのみ
            api_constraints=api_constraints,
            examples=examples,
            task_context=self._contextualize_task(task_definition),
        )
```

#### 局所化のメリット

| メリット | 説明 |
|---------|------|
| **迅速な修正** | 問題の原因が明確 → 修正ファイルが特定しやすい |
| **テストの局所化** | 修正したコンポーネントのみテスト可能 |
| **A/Bテスト** | Few-shot例の差し替えで効果測定可能 |
| **段階的改善** | 1つのルール/例を改善 → 効果確認 → 次へ |
| **回帰防止** | 他のコンポーネントへの影響を最小化 |

---

## 4. 詳細設計

### 4.1 PromptBuilder SubWorkflow

**目的**: LLMが「最初から正しく」生成できるプロンプトを構築

```python
class PromptBuilderSubWorkflow:
    """Few-shot + 制約ベースのプロンプト構築"""

    async def build(
        self,
        task_definition: TaskDefinition,
        interface_schema: InterfaceSchema,
        context: ExecutionContext,
    ) -> WorkflowPrompt:
        # 1. タスクに適したFew-shot例を選択
        examples = await self._select_few_shot_examples(task_definition)

        # 2. 使用APIの制約を埋め込み
        api_constraints = await self._build_api_constraints(
            task_definition.recommended_apis
        )

        # 3. GraphAIルールの構造化セクション
        rules_section = self._build_rules_section()

        # 4. 最終プロンプト組み立て
        return WorkflowPrompt(
            system=rules_section,
            examples=examples,
            constraints=api_constraints,
            task_context=self._contextualize_task(task_definition),
        )
```

**Few-shot例の選択戦略**:

| API種別 | 選択するFew-shot例 |
|---------|-------------------|
| google_search | 検索 → 整形パターン |
| gmail_send | 入力検証 → API呼出パターン |
| explorer_agent | 複合LLM呼出パターン |
| mapAgent使用 | 配列処理パターン |

### 4.2 LLMGenerator SubWorkflow

**目的**: 単一のLLM呼び出しで高品質なYAMLを生成

```python
class LLMGeneratorSubWorkflow:
    """構造化出力によるYAML生成"""

    async def generate(
        self,
        prompt: WorkflowPrompt,
        context: ExecutionContext,
    ) -> LLMGenerationResult:
        # Pydanticモデルで構造化出力を強制
        result = await invoke_structured_llm(
            system_prompt=prompt.system,
            user_prompt=prompt.render(),
            response_model=GraphAIWorkflowSchema,  # 構造化スキーマ
            model_env_var="WORKFLOW_GENERATOR_V2_MODEL",
            default_model="gemini-3-flash-preview",
        )

        return LLMGenerationResult(
            yaml_content=result.result.to_yaml(),
            model_name=result.model_name,
        )
```

**GraphAIWorkflowSchema (Pydantic)**:

```python
class NodeDefinition(BaseModel):
    """GraphAI ノード定義"""

    agent: str                              # Agent種別（fetchAgent, stringTemplateAgent等）
    inputs: dict[str, Any] | None = None    # 入力定義（:node.path形式の参照を含む）
    params: dict[str, Any] | None = None    # Agentパラメータ
    isResult: bool = False                  # 最終出力ノードフラグ
    console: dict[str, Any] | None = None   # デバッグログ設定

    @validator("agent")
    def validate_agent_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("agent must not be empty")
        return v


class GraphAIWorkflowSchema(BaseModel):
    """構造化出力で生成品質を担保"""

    version: Literal["0.5"] = "0.5"
    nodes: dict[str, NodeDefinition]

    @validator("nodes")
    def validate_has_source(cls, v):
        if "source" not in v:
            raise ValueError("source node is required")
        return v

    @validator("nodes")
    def validate_has_result(cls, v):
        if not any(n.isResult for n in v.values()):
            raise ValueError("At least one node must have isResult=True")
        return v

    def to_yaml(self) -> str:
        """YAML形式で出力"""
        return yaml.dump(
            self.dict(exclude_none=True),
            default_flow_style=False,
            allow_unicode=True,
        )
```

### 4.3 YamlValidator SubWorkflow

**目的**: 軽量な検証で致命的エラーのみ検出

```python
class YamlValidatorSubWorkflow:
    """軽量検証（V1の多段階検証を統合・簡略化）"""

    async def validate(
        self,
        yaml_content: str,
        context: ExecutionContext,
    ) -> ValidationResult:
        errors = []

        # 1. YAML構文検証
        errors.extend(self._validate_yaml_syntax(yaml_content))

        # 2. 必須構造検証（source, isResult）
        errors.extend(self._validate_required_structure(yaml_content))

        # 3. Agent存在確認（AVAILABLE_AGENTS.md参照）
        errors.extend(self._validate_agent_exists(yaml_content))

        # 4. 参照解決検証（:node.path形式）
        errors.extend(self._validate_references(yaml_content))

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
        )
```

**V1との検証比較**:

| 検証項目 | V1 | V2 |
|---------|-----|-----|
| YAML構文 | workflow_tester で暗黙 | 明示的検証 |
| Schema検証 | workflow_schema_validator | プロンプト内制約 |
| API互換性 | 実行時検出 | プロンプト内制約 |
| 配列型検証 | sample_input_generator + llm_evaluator | プロンプト内制約 |
| **実行テスト** | workflow_tester (API呼出) | **削除（オプション）** |
| **LLM評価** | llm_evaluator | **削除** |

### 4.4 WorkflowGenWorkflow (統合)

```python
class WorkflowGenWorkflow:
    """WorkflowProtocol準拠のワークフロー生成"""

    # implements WorkflowProtocol

    async def execute(
        self,
        input_data: WorkflowGenInput,
        context: ExecutionContext,
    ) -> WorkflowResult[WorkflowGenOutput]:

        # リトライ時は前回エラーを取得
        previous_errors = context.get_retry_errors(Phase.WORKFLOW_GEN)

        # Phase 1: プロンプト構築（リトライ時はエラー情報を含める）
        if previous_errors:
            prompt = await self._prompt_builder.build_with_errors(
                task_definition=input_data.task_definition,
                interface_schema=input_data.interface_schema,
                context=context,
                previous_errors=previous_errors,
            )
        else:
            prompt = await self._prompt_builder.build(
                task_definition=input_data.task_definition,
                interface_schema=input_data.interface_schema,
                context=context,
            )

        # Phase 2: LLM生成
        generation = await self._llm_generator.generate(prompt, context)

        # Phase 3: 軽量検証
        validation = await self._yaml_validator.validate(
            generation.yaml_content, context
        )

        if not validation.is_valid:
            # リトライ可能かチェック
            if context.can_retry(Phase.WORKFLOW_GEN):
                context.record_retry(Phase.WORKFLOW_GEN, validation.errors)
                return WorkflowResult.retry(validation.errors)
            else:
                return WorkflowResult.failure(validation.errors)

        return WorkflowResult.success(
            WorkflowGenOutput(
                yaml_content=generation.yaml_content,
                workflow_name=f"workflow_{input_data.task_id}",
            )
        )
```

### 4.5 リトライ時のプロンプト改善戦略

**目的**: 同じエラーを繰り返さないよう、リトライ時にエラー情報をプロンプトに反映

#### ValidationError の標準化

```python
@dataclass
class ValidationError:
    """検証エラーの標準形式"""

    code: str           # エラーコード（"MISSING_SOURCE", "INVALID_AGENT"等）
    message: str        # 人間可読メッセージ
    location: str       # エラー位置（"nodes.search.agent"）
    suggestion: str     # 修正提案（LLMへのヒント）

    def to_prompt_section(self) -> str:
        """プロンプト用のエラー説明を生成"""
        return f"""
- エラー: {self.message}
  - 位置: {self.location}
  - 修正方法: {self.suggestion}
"""
```

#### エラーコード一覧

| コード | 説明 | 修正提案例 |
|--------|------|-----------|
| `MISSING_SOURCE` | sourceノードがない | `source: {}` を追加してください |
| `MISSING_RESULT` | isResult=trueのノードがない | 最終ノードに `isResult: true` を追加 |
| `INVALID_AGENT` | 存在しないAgent | 利用可能: fetchAgent, stringTemplateAgent, ... |
| `INVALID_REFERENCE` | 参照先が存在しない | `:search.result` → `:search.results` |
| `YAML_SYNTAX` | YAML構文エラー | インデントを確認してください |

#### build_with_errors の実装

```python
class PromptBuilderSubWorkflow:

    async def build_with_errors(
        self,
        task_definition: TaskDefinition,
        interface_schema: InterfaceSchema,
        context: ExecutionContext,
        previous_errors: list[ValidationError],
    ) -> WorkflowPrompt:
        """リトライ時：前回エラーを含めたプロンプト構築"""

        # 通常のプロンプト構築
        base_prompt = await self.build(task_definition, interface_schema, context)

        # エラーフィードバックセクションを追加
        error_feedback = self._build_error_feedback(previous_errors)

        return WorkflowPrompt(
            system=base_prompt.system,
            rules=base_prompt.rules,
            api_constraints=base_prompt.api_constraints,
            examples=base_prompt.examples,
            task_context=base_prompt.task_context,
            error_feedback=error_feedback,  # 追加
        )

    def _build_error_feedback(self, errors: list[ValidationError]) -> str:
        """エラーフィードバックセクションを構築"""
        if not errors:
            return ""

        lines = [
            "",
            "## 前回生成時のエラー（必ず修正してください）",
            "",
        ]
        for error in errors:
            lines.append(error.to_prompt_section())

        lines.append("")
        lines.append("上記のエラーを修正した正しいYAMLを生成してください。")

        return "\n".join(lines)
```

#### リトライ時のプロンプト例

```
## 前回生成時のエラー（必ず修正してください）

- エラー: Agent 'searchAgent' は存在しません
  - 位置: nodes.search.agent
  - 修正方法: 利用可能なAgent: fetchAgent, stringTemplateAgent, geminiAgent, ...

- エラー: 参照先 ':search.result' が解決できません
  - 位置: nodes.format.inputs.data
  - 修正方法: 正しい参照パスを確認してください。':search.results' ではありませんか？

上記のエラーを修正した正しいYAMLを生成してください。
```

---

## 5. Few-shot例の管理

### 5.1 ディレクトリ構造

```
jobGeneratorV2/workflows/workflow_gen/
├── __init__.py
├── workflow.py              # WorkflowGenWorkflow
├── llm_generator.py         # LLMGeneratorSubWorkflow
├── yaml_validator.py        # YamlValidatorSubWorkflow
├── schemas.py               # GraphAIWorkflowSchema等
│
├── prompt_builder/          # PromptBuilderSubWorkflow（モジュラー構造）
│   ├── __init__.py          # PromptBuilderSubWorkflow クラス
│   ├── assembler.py         # プロンプト組み立てロジック
│   │
│   ├── system/              # システムプロンプト
│   │   ├── __init__.py
│   │   └── workflow_generator.py  # 役割定義プロンプト
│   │
│   ├── rules/               # GraphAIルール（修正頻度：中）
│   │   ├── __init__.py
│   │   ├── base_rules.py    # 基本ルール（version, source, isResult）
│   │   ├── agent_rules.py   # Agent別制約（stringTemplateAgent等）
│   │   ├── reference_rules.py  # 参照ルール（:node.path形式）
│   │   └── api_rules.py     # API呼出ルール（fetchAgent設定）
│   │
│   ├── constraints/         # API別制約（動的生成）
│   │   ├── __init__.py
│   │   ├── loader.py        # capabilities.yaml読込
│   │   └── formatter.py     # 制約文字列フォーマット
│   │
│   └── few_shot/            # Few-shot例（修正頻度：高）
│       ├── __init__.py
│       ├── loader.py        # 例の読み込み・選択ロジック
│       ├── search_pattern.yaml      # 検索系パターン
│       ├── api_call_pattern.yaml    # API呼出パターン
│       ├── map_pattern.yaml         # mapAgent使用パターン
│       └── llm_chain_pattern.yaml   # LLMチェーンパターン
│
└── validators/              # 検証ロジック（モジュラー構造）
    ├── __init__.py
    ├── syntax_validator.py  # YAML構文検証
    ├── structure_validator.py  # 必須構造検証
    ├── agent_validator.py   # Agent存在確認
    └── reference_validator.py  # 参照解決検証
```

#### 修正頻度による分類

| 分類 | ディレクトリ | 修正頻度 | 修正例 |
|-----|-------------|---------|--------|
| **高頻度** | `few_shot/` | 高 | 新パターン追加、例の品質改善 |
| **中頻度** | `rules/` | 中 | Agent制約追加、ルール修正 |
| **低頻度** | `system/`, `validators/` | 低 | アーキテクチャ変更時のみ |

### 5.2 Few-shot例の選択ロジック

#### 選択基準（優先度順）

| 優先度 | 基準 | 説明 |
|--------|------|------|
| 1 | API種別 | 推奨APIに基づく基本パターン |
| 2 | 出力スキーマ | 配列出力、ネスト構造等 |
| 3 | 依存関係 | タスクチェーンの複雑さ |
| 4 | 特殊Agent | mapAgent、copyAgent使用時 |

#### 実装

```python
def select_few_shot_examples(
    task_definition: TaskDefinition,
    max_examples: int = 2,
) -> list[FewShotExample]:
    """タスクに最適なFew-shot例を選択（多角的評価）"""

    scored_patterns: dict[str, float] = {}

    # 1. API種別に基づく選択（基本スコア）
    for api in task_definition.recommended_apis:
        api_lower = api.lower()
        if "search" in api_lower:
            scored_patterns["search_pattern"] = scored_patterns.get("search_pattern", 0) + 1.0
        elif "gmail" in api_lower or "send" in api_lower:
            scored_patterns["api_call_pattern"] = scored_patterns.get("api_call_pattern", 0) + 1.0
        elif "explorer" in api_lower or "llm" in api_lower or "gemini" in api_lower:
            scored_patterns["llm_chain_pattern"] = scored_patterns.get("llm_chain_pattern", 0) + 1.0
        elif "tts" in api_lower or "speech" in api_lower:
            scored_patterns["api_call_pattern"] = scored_patterns.get("api_call_pattern", 0) + 0.8

    # 2. 出力スキーマの特性に基づく選択
    if _has_array_output(task_definition.output_schema):
        scored_patterns["map_pattern"] = scored_patterns.get("map_pattern", 0) + 1.5

    if _has_nested_object_output(task_definition.output_schema):
        scored_patterns["complex_transform_pattern"] = scored_patterns.get("complex_transform_pattern", 0) + 1.0

    # 3. 依存関係の複雑さに基づく選択
    dependency_count = len(task_definition.dependencies or [])
    if dependency_count > 2:
        scored_patterns["complex_chain_pattern"] = scored_patterns.get("complex_chain_pattern", 0) + 1.2
    elif dependency_count > 0:
        scored_patterns["simple_chain_pattern"] = scored_patterns.get("simple_chain_pattern", 0) + 0.5

    # 4. 入力スキーマに配列がある場合（mapAgent必要の可能性）
    if _has_array_input(task_definition.input_schema):
        scored_patterns["map_pattern"] = scored_patterns.get("map_pattern", 0) + 1.0

    # スコア順にソートして上位を選択
    sorted_patterns = sorted(
        scored_patterns.items(),
        key=lambda x: x[1],
        reverse=True
    )

    selected = [pattern for pattern, score in sorted_patterns[:max_examples]]

    # 最低1つは基本パターンを含める
    if not selected:
        selected = ["api_call_pattern"]

    return load_examples(selected)


def _has_array_output(schema: dict | None) -> bool:
    """出力スキーマに配列が含まれるか"""
    if not schema:
        return False
    if schema.get("type") == "array":
        return True
    properties = schema.get("properties", {})
    return any(
        prop.get("type") == "array"
        for prop in properties.values()
    )


def _has_nested_object_output(schema: dict | None) -> bool:
    """出力スキーマにネストしたオブジェクトが含まれるか"""
    if not schema:
        return False
    properties = schema.get("properties", {})
    for prop in properties.values():
        if prop.get("type") == "object":
            return True
        if prop.get("type") == "array" and prop.get("items", {}).get("type") == "object":
            return True
    return False


def _has_array_input(schema: dict | None) -> bool:
    """入力スキーマに配列が含まれるか"""
    if not schema:
        return False
    if schema.get("type") == "array":
        return True
    properties = schema.get("properties", {})
    return any(
        prop.get("type") == "array"
        for prop in properties.values()
    )
```

#### Few-shot例の追加パターン

| パターン | ファイル | 用途 |
|---------|---------|------|
| `search_pattern` | search_pattern.yaml | 検索API → 結果整形 |
| `api_call_pattern` | api_call_pattern.yaml | 汎用API呼出 |
| `llm_chain_pattern` | llm_chain_pattern.yaml | LLM連鎖処理 |
| `map_pattern` | map_pattern.yaml | 配列処理（mapAgent） |
| `complex_chain_pattern` | complex_chain_pattern.yaml | 複数依存タスク |
| `complex_transform_pattern` | complex_transform_pattern.yaml | ネスト構造変換 |
| `simple_chain_pattern` | simple_chain_pattern.yaml | 単純な2ノード連携 |

### 5.3 Few-shot例のフォーマット

```yaml
# few_shot_examples/search_pattern.yaml
name: "search_pattern"
description: "検索API → 結果整形パターン"
applicable_apis:
  - "google_search"
  - "gmail_search"
task_example:
  name: "キーワード検索タスク"
  description: "指定キーワードでGoogle検索を実行し、結果を整形"
  input_schema:
    type: object
    properties:
      keyword:
        type: string
  output_schema:
    type: object
    properties:
      results:
        type: array
        items:
          type: object
          properties:
            title:
              type: string
            url:
              type: string
workflow_yaml: |
  version: 0.5
  nodes:
    source: {}

    search:
      agent: fetchAgent
      inputs:
        url: "http://localhost:8004/aiagent-api/v1/utility/google_search"
        body:
          query: :source.keyword
          num_results: 5
      params:
        method: POST
        headers:
          Content-Type: application/json

    format_results:
      agent: stringTemplateAgent
      inputs:
        results: :search.results
      params:
        template: |
          検索結果:
          ${results}
      isResult: true
```

---

## 6. 環境変数・設定

### 6.1 新規環境変数

| 環境変数 | デフォルト | 説明 |
|---------|-----------|------|
| `WORKFLOW_GENERATOR_V2_MODEL` | `gemini-3-flash-preview` | V2 YAML生成モデル |
| `WORKFLOW_GENERATOR_V2_TEMPERATURE` | `0.3` | 低めの温度で安定性重視 |
| `WORKFLOW_GENERATOR_V2_MAX_RETRY` | `2` | 最大リトライ回数 |
| `WORKFLOW_GENERATOR_V2_ENABLE_EXECUTION_TEST` | `false` | 実行テスト有効化（デバッグ用） |

### 6.2 config.py への追加

```python
# Workflow Generator V2 (Issue #342 extension)
WORKFLOW_GENERATOR_V2_MODEL: str = Field(default="gemini-3-flash-preview")
WORKFLOW_GENERATOR_V2_TEMPERATURE: float = Field(default=0.3)
WORKFLOW_GENERATOR_V2_MAX_RETRY: int = Field(default=2)
WORKFLOW_GENERATOR_V2_ENABLE_EXECUTION_TEST: bool = Field(default=False)
```

---

## 7. 期待される効果

| 指標 | V1 | V2 (期待) |
|------|-----|-----------|
| **LLM呼出回数** | 3-10回/タスク | 1-3回/タスク |
| **生成時間** | 30-120秒 | 5-15秒 |
| **成功率** | ~70% | ~90% |
| **コード行数** | ~3000行 | ~800行 |
| **テスト容易性** | 困難（LangGraph依存） | 容易（Protocol-based） |

---

## 8. 実装フェーズ

| フェーズ | 内容 | 見積り |
|---------|------|--------|
| **F.1** | Few-shot例の作成・整理 | 2時間 |
| **F.2** | PromptBuilderSubWorkflow | 3時間 |
| **F.3** | GraphAIWorkflowSchema (Pydantic) | 2時間 |
| **F.4** | LLMGeneratorSubWorkflow | 2時間 |
| **F.5** | YamlValidatorSubWorkflow | 2時間 |
| **F.6** | WorkflowGenWorkflow統合 | 2時間 |
| **F.7** | 単体テスト | 3時間 |
| **F.8** | 結合テスト・受入テスト | 4時間 |
| **合計** | | **20時間** |

---

## 9. 検討事項

### 9.1 実行テストの扱い

**V1**: `workflow_tester` でGraphAIサーバーに実際に実行

**V2案**:
- **Option A**: 削除（構造検証のみ）
- **Option B**: オプション化（`enable_execution_test=False` デフォルト） **← 推奨**
- **Option C**: 別フェーズとして分離（WorkflowTestWorkflow）

#### 推奨理由（Option B）

| 観点 | 説明 |
|------|------|
| **リスク軽減** | 既存機能の完全削除はリスクが高い |
| **段階的移行** | デフォルトOFFで新アーキテクチャを検証後、必要に応じて有効化 |
| **デバッグ支援** | 問題発生時にONにして実行テストで原因特定可能 |
| **後方互換性** | V1と同等の検証が必要な場合にも対応可能 |

#### 実装イメージ

```python
class WorkflowGenWorkflow:
    def __init__(
        self,
        enable_execution_test: bool = False,  # デフォルトOFF
    ):
        self._enable_execution_test = enable_execution_test

    async def execute(self, input_data, context):
        # ... 通常の生成・検証 ...

        # オプション: 実行テスト
        if self._enable_execution_test:
            test_result = await self._workflow_tester.test(
                yaml_content=generation.yaml_content,
                context=context,
            )
            if not test_result.success:
                # 実行エラーを検証エラーに追加
                validation.errors.extend(test_result.errors)

        # ...
```

#### 環境変数

```python
# config.py
WORKFLOW_GENERATOR_V2_ENABLE_EXECUTION_TEST: bool = Field(default=False)
```

### 9.2 LLM評価の削除

**V1**: `llm_evaluator` でワークフロー品質をLLM評価

**V2案**:
- 削除し、構造検証のみに簡略化
- 品質評価が必要な場合は、別途手動レビューまたは受入テストで対応

### 9.3 Few-shot例の優先度

作成優先度:
1. **search_pattern** - Google検索系（最も頻出）
2. **api_call_pattern** - 汎用API呼出
3. **llm_chain_pattern** - LLM連鎖処理
4. **map_pattern** - 配列処理（mapAgent）

---

## 10. リスクと対策

| リスク | 対策 |
|--------|------|
| Few-shot例が不十分で生成品質低下 | 段階的に例を追加、成功例を自動収集 |
| 構造化出力がLLMでサポートされない | JSON Schemaベースのバリデーションにフォールバック |
| 新しいAgent追加時の対応漏れ | AVAILABLE_AGENTS.md との同期チェック |
| リトライでも成功しないケース | 詳細エラーログ + 手動介入フローを用意 |

---

## 11. 次のアクション

1. この設計方針のレビュー・承認
2. 検討事項（9.1, 9.2, 9.3）の決定
3. Issue作成（#342の子Issueまたは新規Issue）
4. 実装開始

---

*Generated: 2026-01-07*
*Issue #342 Extension - Workflow Generator V2 Architecture*
