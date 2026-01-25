# 設計方針書: V2 Workflow Generator 品質改善

Issue #343 - タイムアウト単位・エラーフィードバック・プロンプト重複

---

## 現状調査サマリ

### 対象プロジェクト
- **プロジェクト名**: expertAgent
- **主要モジュール**: `aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/`

### 既存アーキテクチャパターン

| パターン | 使用箇所 | 目的 |
|---------|---------|------|
| **Orchestrator** | `JobGenerationOrchestrator` | フェーズ間の状態遷移管理 |
| **Pipeline** | `ValidationPipeline` | 複数バリデータの順序実行 |
| **Protocol** | `WorkflowProtocol` | ワークフローの共通インターフェース |
| **Observer** | `ValidationObserver` | バリデーション結果の通知 |
| **SubWorkflow** | `YamlGeneratorSubWorkflow` | サブ処理の単一責任分離 |

### モジュール間依存関係

```
yaml_generator.py
├── LLMGeneratorSubWorkflow
│   ├── AgentSelector         ← API-Agent マッピング
│   ├── ParameterMapper       ← パラメータ変換
│   └── PromptBuilderSubWorkflow
│       └── assembler.py
│           ├── APISchemaInjector  ← スキーマ注入
│           └── WorkflowPatternLibrary
├── YamlValidatorSubWorkflow  ← YAML構文検証
└── ValidationPipeline        ← 深いバリデーション
    ├── SourcePathRuleEngine
    └── AgentConstraintValidator
```

### 既存API設計パターン

- **ValidationError**: 構造化エラー（code, message, location, suggestion, severity）
- **ValidationResult**: `is_valid`, `errors`, `to_prompt_feedback()` メソッド提供
- **WorkflowPrompt**: `error_feedback` フィールド存在（現在未使用）

### 設計上の制約

1. **既存リトライ構造を活かす**: `yaml_generator.generate_with_llm()` の while ループ構造を維持
2. **ValidationPipeline を活用**: 既存の `to_prompt_feedback()` を最大限利用
3. **後方互換性**: 既存APIインターフェースの変更を最小化
4. **SOLID原則遵守**: 特に単一責任原則とオープン/クローズド原則

---

## 問題分析

### 問題1: タイムアウト単位の矛盾（Critical）

```
┌─────────────────────────────────────────────────────────────┐
│  プロンプト (agent_rules.py)                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  timeout: 30  ← 「30秒」として教示                    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓ LLM生成
┌─────────────────────────────────────────────────────────────┐
│  生成されたYAML                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  timeout: 30  ← LLMが教示通りに生成                   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓ バリデーション
┌─────────────────────────────────────────────────────────────┐
│  AgentConstraintValidator                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  LIKELY_SECONDS_THRESHOLD = 500                      │   │
│  │  if timeout < 500:                                   │   │
│  │      error("Timeout likely in seconds, not ms")     │   │ ← 拒否！
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**根本原因**: GraphAI はミリ秒を期待するが、プロンプトで秒として教示

### 問題2: エラーフィードバック未渡し（Critical）

```python
# yaml_generator.py の現状コード
previous_errors: list = []
attempt = 0

while attempt <= max_retries:
    # LLM呼び出し - error_feedback を渡していない！
    result = await llm_generator.generate_from_task(
        task_name=task_name,
        # ... 他パラメータ
        # error_feedback=??? ← 存在しない
    )

    # 検証
    if not validation_result.is_valid:
        previous_errors = validation_result.errors  # 収集するが
        attempt += 1
        continue  # 次回LLM呼び出しに渡さない
```

**根本原因**: リトライループに error_feedback 引き渡し機構がない

### 問題3: API情報の重複（Major）

```
┌─────────────────────────────────────────────────────────────┐
│  assembler.py でのAPI情報注入                                │
├─────────────────────────────────────────────────────────────┤
│  1. api_constraints (recommended_apis リスト)                │
│     → format_multiple_api_constraints()                      │
│     → "Recommended APIs: /utility/json_stringify, ..."       │
├─────────────────────────────────────────────────────────────┤
│  2. api_mappings (AgentSelector 由来)                        │
│     → _format_api_mappings()                                 │
│     → "URL: ${EXPERTAGENT_BASE_URL}/utility/..."            │
│        "Method: POST", "Agent: fetchAgent"                   │
├─────────────────────────────────────────────────────────────┤
│  3. APISchemaInjector                                        │
│     → inject()                                               │
│     → "Request Schema: {...}", "Response Schema: {...}"     │
└─────────────────────────────────────────────────────────────┘
                              ↓
          同じAPIの情報が3回重複してプロンプトに出現
```

**根本原因**: API情報のソースが複数存在し、統合されていない

---

## アーキテクチャ設計

### 修正対象のコンポーネント図

```
┌─────────────────────────────────────────────────────────────────────┐
│                    yaml_generator.py                                 │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  generate_with_llm()                                          │ │
│  │  ┌─────────────────────────────────────────────────────────┐ │ │
│  │  │  while attempt <= max_retries:                          │ │ │
│  │  │    ┌─────────────────────────────────────────────────┐ │ │ │
│  │  │    │  [NEW] error_feedback = format_errors(prev)     │ │ │ │
│  │  │    └─────────────────────────────────────────────────┘ │ │ │
│  │  │                      ↓                                  │ │ │
│  │  │    llm_generator.generate_from_task(                   │ │ │
│  │  │        ...,                                            │ │ │
│  │  │        error_feedback=error_feedback  ← [NEW]          │ │ │
│  │  │    )                                                   │ │ │
│  │  └─────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    llm_generator.py                                  │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  generate_from_task(..., error_feedback: str = "")  ← [NEW]   │ │
│  │                      ↓                                        │ │
│  │  prompt_builder.build(..., error_feedback=error_feedback)     │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    assembler.py                                      │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  assemble_prompt(..., error_feedback: str = "")               │ │
│  │                      ↓                                        │ │
│  │  WorkflowPrompt(                                              │ │
│  │      ...,                                                     │ │
│  │      error_feedback=error_feedback  ← 既存フィールド活用      │ │
│  │  )                                                            │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### レイヤー構成

変更なし（既存レイヤー構成を維持）

---

## 技術選定

| カテゴリ | 選定技術 | 選定理由 | 既存との整合性 |
|---------|---------|---------|---------------|
| エラーフォーマット | `ValidationResult.to_prompt_feedback()` | 既存メソッド活用 | 完全互換 |
| タイムアウト単位 | ミリ秒統一 | GraphAI仕様準拠 | 完全互換 |
| API情報整理 | APISchemaInjector優先 | スキーマ詳細度 | 軽微な変更 |

---

## 設計パターン

### 既存パターンの活用

| パターン | 修正での使用 | 新規/既存 |
|---------|-------------|----------|
| **Chain of Responsibility** | ValidationPipeline でのエラー収集 | 既存活用 |
| **Template Method** | `to_prompt_feedback()` | 既存活用 |
| **Strategy** | エラーフィードバック形式 | 既存活用 |

### 新規パターン導入

**なし** - 既存パターンで十分対応可能

---

## データモデル設計

### 既存モデルの変更

変更なし - `ValidationError`, `ValidationResult` をそのまま使用

### フロー変更

```
[Before]
yaml_generator.generate_with_llm()
  ↓
llm_generator.generate_from_task(task_name, ..., context)
  ↓
prompt_builder.build(task_name, ..., error_feedback="")  ← 常に空
  ↓
assembler.assemble_prompt(..., error_feedback="")
  ↓
WorkflowPrompt(error_feedback="")  ← 常に空

[After]
yaml_generator.generate_with_llm()
  ↓
[NEW] error_feedback = validation_result.to_prompt_feedback()
  ↓
llm_generator.generate_from_task(task_name, ..., context, error_feedback)
  ↓
prompt_builder.build(task_name, ..., error_feedback=error_feedback)
  ↓
assembler.assemble_prompt(..., error_feedback=error_feedback)
  ↓
WorkflowPrompt(error_feedback=error_feedback)  ← エラー情報含む
```

---

## API設計

### インターフェース変更

#### 1. `LLMGeneratorSubWorkflow.generate_from_task()`

```python
# Before
async def generate_from_task(
    self,
    task_name: str,
    task_description: str,
    input_schema: dict[str, Any],
    output_schema: dict[str, Any],
    recommended_apis: list[str] | None = None,
    dependencies: list[str] | None = None,
    context: "ExecutionContext | None" = None,
) -> LLMGenerationResult:

# After
async def generate_from_task(
    self,
    task_name: str,
    task_description: str,
    input_schema: dict[str, Any],
    output_schema: dict[str, Any],
    recommended_apis: list[str] | None = None,
    dependencies: list[str] | None = None,
    context: "ExecutionContext | None" = None,
    error_feedback: str = "",  # [NEW] エラーフィードバック
) -> LLMGenerationResult:
```

#### 2. `PromptBuilderSubWorkflow.build()`

```python
# Before
def build(
    self,
    task_name: str,
    task_description: str,
    input_schema: dict[str, Any],
    output_schema: dict[str, Any],
    recommended_apis: list[str] | None = None,
    dependencies: list[str] | None = None,
    api_mappings: list[dict[str, Any]] | None = None,
) -> WorkflowPrompt:

# After
def build(
    self,
    task_name: str,
    task_description: str,
    input_schema: dict[str, Any],
    output_schema: dict[str, Any],
    recommended_apis: list[str] | None = None,
    dependencies: list[str] | None = None,
    api_mappings: list[dict[str, Any]] | None = None,
    error_feedback: str = "",  # [NEW]
) -> WorkflowPrompt:
```

---

## セキュリティ設計

### エラーメッセージのサニタイズ方針

アーキテクチャレビューで指摘されたセキュリティリスクに対応するため、
エラーフィードバックをLLMに渡す際のサニタイズ処理を設計する。

#### サニタイズ対象

| 対象 | リスク | 対策 |
|------|--------|------|
| 特殊文字（`<`, `>`, `{`, `}`） | プロンプト構造の破壊 | HTMLエスケープ |
| 制御文字 | 予期しない動作 | 除去 |
| 長大なエラーメッセージ | トークン枯渇 | 切り詰め |
| 機密情報（パス、トークン等） | 情報漏洩 | パターンマスク |

#### 実装方針

```python
# validators/__init__.py に追加
import re

# 機密情報パターン
SENSITIVE_PATTERNS = [
    (r"/Users/[^/\s]+", "[USER_PATH]"),           # ユーザーパス
    (r"[a-zA-Z0-9_-]{32,}", "[TOKEN]"),           # 長いトークン文字列
    (r"password\s*[:=]\s*\S+", "password=[MASKED]"),  # パスワード
]

def sanitize_error_message(message: str, max_length: int = 500) -> str:
    """エラーメッセージをサニタイズ。

    Args:
        message: 元のエラーメッセージ
        max_length: 最大文字数

    Returns:
        サニタイズ済みメッセージ
    """
    # 1. 機密情報のマスク
    for pattern, replacement in SENSITIVE_PATTERNS:
        message = re.sub(pattern, replacement, message)

    # 2. 制御文字の除去
    message = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", message)

    # 3. 特殊文字のエスケープ（LLMプロンプト向け）
    message = message.replace("{{", "{ {").replace("}}", "} }")

    # 4. 長さ制限
    if len(message) > max_length:
        message = message[:max_length - 3] + "..."

    return message
```

#### ValidationResult への統合

```python
# ValidationResult.to_prompt_feedback() の改善
def to_prompt_feedback(
    self,
    max_errors: int = 5,
    max_total_length: int = 2000,
) -> str:
    """サニタイズ済みエラーフィードバックを生成。

    Args:
        max_errors: 含めるエラーの最大数
        max_total_length: フィードバック全体の最大文字数

    Returns:
        LLM向けにフォーマットされたエラーフィードバック
    """
    if not self.errors:
        return ""

    # 重大度順にソート（critical → major → minor）
    sorted_errors = sorted(
        self.errors,
        key=lambda e: {"critical": 0, "major": 1, "minor": 2}.get(e.severity, 3)
    )

    # 最大件数に制限
    limited_errors = sorted_errors[:max_errors]

    lines = [
        "",
        "## Previous Generation Errors (MUST FIX)",
        "",
    ]

    for error in limited_errors:
        # 各エラーメッセージをサニタイズ
        safe_message = sanitize_error_message(error.message)
        safe_suggestion = sanitize_error_message(error.suggestion or "")

        lines.append(f"- **{error.code.value}** at `{error.location}`")
        lines.append(f"  - Error: {safe_message}")
        if safe_suggestion:
            lines.append(f"  - Fix: {safe_suggestion}")
        lines.append("")

    lines.append("Please generate corrected YAML fixing the above errors.")

    feedback = "\n".join(lines)

    # 全体長制限
    if len(feedback) > max_total_length:
        feedback = feedback[:max_total_length - 50]
        feedback += "\n\n... (additional errors truncated)"

    return feedback
```

---

## フィードバック長制限設計

### 制限値の定義

| パラメータ | 値 | 理由 |
|-----------|-----|------|
| `MAX_ERRORS` | 5 | 最重要エラーに集中させる |
| `MAX_MESSAGE_LENGTH` | 500文字 | 個別メッセージの上限 |
| `MAX_TOTAL_LENGTH` | 2000文字 | フィードバック全体の上限 |

### LLMコンテキスト影響分析

```
通常のプロンプトサイズ: ~8,000 tokens
+ エラーフィードバック: ~500 tokens（2000文字 ≈ 500 tokens）
= 合計: ~8,500 tokens

モデル別コンテキスト上限:
- gemini-3-flash-preview: 128K tokens ✅ 余裕あり
- gpt-4o: 128K tokens ✅ 余裕あり
- claude-3-opus: 200K tokens ✅ 余裕あり
```

### 切り詰めポリシー

```
優先度順:
1. critical エラー → 必ず含める
2. major エラー → MAX_ERRORS に達するまで含める
3. minor エラー → 残り枠があれば含める
4. 超過分 → "... (N additional errors)" で示す
```

---

## API情報重複削除の段階的移行計画

### Phase 概要

```
┌─────────────────────────────────────────────────────────────────────┐
│  Phase 1: 非推奨化 (Issue #343 スコープ)                            │
│  - api_constraints に @deprecated 警告を追加                        │
│  - ログ出力で重複を警告                                             │
│  期間: 本Issue内                                                    │
├─────────────────────────────────────────────────────────────────────┤
│  Phase 2: 統合準備 (将来Issue)                                      │
│  - APISchemaInjector と AgentSelector のデータ統合                  │
│  - 新しい UnifiedAPIInfo クラスの設計                               │
│  期間: 次スプリント                                                 │
├─────────────────────────────────────────────────────────────────────┤
│  Phase 3: 完全移行 (将来Issue)                                      │
│  - api_constraints, api_mappings の削除                             │
│  - UnifiedAPIInfo への完全移行                                       │
│  期間: Phase 2 完了後                                               │
└─────────────────────────────────────────────────────────────────────┘
```

### Phase 1 詳細（本Issue スコープ）

#### 1.1 非推奨警告の追加

```python
# assembler.py の修正
import warnings

def assemble_prompt(
    ...
    recommended_apis: list[str] | None = None,  # Phase 1: 非推奨
    api_mappings: list[dict[str, Any]] | None = None,  # Phase 1: 非推奨
    ...
) -> WorkflowPrompt:
    """..."""

    # Phase 1: 重複警告
    if recommended_apis and api_mappings:
        warnings.warn(
            "Both recommended_apis and api_mappings provided. "
            "API information may be duplicated in prompt. "
            "Consider using APISchemaInjector only.",
            DeprecationWarning,
            stacklevel=2
        )
```

#### 1.2 APISchemaInjector 優先化

```python
# assembler.py の修正（Phase 1）
def assemble_prompt(...) -> WorkflowPrompt:
    ...

    # API情報の組み立て
    api_section = ""

    # APISchemaInjector を優先（詳細なスキーマ情報を含む）
    if api_injector is None:
        api_injector = APISchemaInjector()

    if recommended_apis:
        # Phase 1: APISchemaInjector 経由でのみ注入
        api_section = api_injector.inject("", recommended_apis)

        # Phase 1: api_mappings は補足情報としてのみ使用
        # （URL, Method のみ、スキーマは除外）
        if api_mappings:
            api_section += _format_api_endpoints_only(api_mappings)

    # api_constraints は廃止（Phase 1で削除）
    # api_constraints = format_multiple_api_constraints(recommended_apis)  # 削除
```

#### 1.3 テスト追加

```python
# tests/unit/test_job_generator_v2/test_api_info_deduplication.py

def test_warns_on_duplicate_api_info():
    """重複API情報で警告が出ることを確認"""
    with pytest.warns(DeprecationWarning, match="API information may be duplicated"):
        assemble_prompt(
            ...,
            recommended_apis=["api1"],
            api_mappings=[{"api_name": "api1", ...}],
        )

def test_api_schema_injector_priority():
    """APISchemaInjector が優先されることを確認"""
    prompt = assemble_prompt(
        ...,
        recommended_apis=["json_stringify"],
    )
    # スキーマ情報が含まれていることを確認
    assert "request_schema" in prompt.api_constraints.lower() or \
           "Request Schema" in prompt.api_constraints
```

### Phase 2-3 は将来Issueで詳細化

本Issueでは Phase 1 のみを実装スコープとする。
Phase 2-3 は別Issueとして起票し、詳細設計を行う。

---

## パフォーマンス設計

### プロンプトサイズ最適化

API情報重複の整理により、プロンプトサイズを削減：

| 項目 | Before | After | 削減率 |
|------|--------|-------|--------|
| API情報セクション | 3箇所 | 1-2箇所 | 33-66% |
| 推定トークン削減 | - | 500-1000 tokens | - |

---

## 設計判断とトレードオフ

### 判断1: タイムアウト単位の統一方法

| 選択肢 | メリット | デメリット | 採用 |
|--------|---------|----------|------|
| **A. プロンプトをミリ秒に統一** | GraphAI仕様と一致 | 直感的でない | ✓ 採用 |
| B. バリデータ閾値を緩和 | プロンプト変更不要 | 誤入力検出できない | - |
| C. 両方許容 | 柔軟 | 一貫性欠如 | - |

**選定理由**: GraphAI の仕様がミリ秒であり、一貫性を優先

### 判断2: エラーフィードバックの渡し方

| 選択肢 | メリット | デメリット | 採用 |
|--------|---------|----------|------|
| **A. 既存パラメータ追加** | 最小限の変更 | シグネチャ変更 | ✓ 採用 |
| B. Contextに含める | シグネチャ変更なし | Contextの肥大化 | - |
| C. 別メソッド追加 | 後方互換性維持 | 複雑化 | - |

**選定理由**: 既存の `error_feedback` フィールドを活用し、明示的なデータフローを実現

### 判断3: API情報の整理方法

| 選択肢 | メリット | デメリット | 採用 |
|--------|---------|----------|------|
| **A. APISchemaInjector 優先** | スキーマ詳細度高い | api_mappings活用度低下 | ✓ 採用 |
| B. api_mappings 統合 | 既存活用 | スキーマ詳細度不足 | - |
| C. 完全統合 | 理想的 | 大規模リファクタ | 将来検討 |

**選定理由**: スキーマ詳細度がLLM生成品質に直結するため

---

## 実装計画

### Task 1: タイムアウト単位統一

**修正ファイル**:
- `prompt_builder/rules/agent_rules.py`
  - `timeout: 30` → `timeout: 30000`
  - 説明文に「milliseconds」明記

**テスト**:
- 既存テストのタイムアウト値更新
- プロンプト内の単位表記テスト追加

### Task 2: エラーフィードバック渡し

**修正ファイル**:
1. `yaml_generator.py`
   - リトライループ内で `validation_result.to_prompt_feedback()` 呼び出し
   - `llm_generator.generate_from_task()` に `error_feedback` パラメータ追加

2. `llm_generator.py`
   - `generate_from_task()` に `error_feedback` パラメータ追加
   - `prompt_builder.build()` に渡す

3. `prompt_builder/prompt_builder.py`
   - `build()` に `error_feedback` パラメータ追加
   - `assembler.assemble_prompt()` に渡す

**テスト**:
- エラーフィードバック渡しの単体テスト
- リトライ時のプロンプト内容検証テスト

### Task 3: API情報整理

**修正ファイル**:
- `prompt_builder/assembler.py`
  - `api_constraints` セクションのシンプル化
  - `APISchemaInjector` の結果を優先的に使用
  - 重複情報の排除

**テスト**:
- プロンプト内API情報の重複チェックテスト
- トークン数削減の検証

---

## 参照ドキュメント

| ドキュメント | 内容 |
|------------|------|
| `dev-reports/feature/issue/342/architecture-design.md` | V2 Job Generator アーキテクチャ設計 |
| `expertAgent/docs/API_REFERENCE.md` | API仕様 |
| `docs/design/graphai-env-vars.md` | GraphAI 環境変数仕様 |
| `graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md` | GraphAI ワークフロー生成ルール |

---

## 変更影響範囲

### 影響ファイル一覧

| ファイル | 変更種別 | 影響度 |
|---------|---------|--------|
| `validators/agent_constraint_validator.py` | 定数変更なし（プロンプト側で対応） | 低 |
| `prompt_builder/rules/agent_rules.py` | timeout例をmsに変更 | 低 |
| `workflows/workflow_gen/yaml_generator.py` | エラーフィードバック渡し追加 | 中 |
| `workflows/workflow_gen/llm_generator.py` | パラメータ追加 | 中 |
| `prompt_builder/prompt_builder.py` | パラメータ追加 | 低 |
| `prompt_builder/assembler.py` | API情報整理 | 中 |

### テスト影響

| テストファイル | 影響 |
|--------------|------|
| `tests/unit/test_job_generator_v2/test_agent_constraint_validator.py` | タイムアウト値更新 |
| `tests/unit/test_job_generator_v2/test_source_path_rule_engine.py` | 変更なし |
| `tests/integration/test_validation_pipeline.py` | 変更なし |
| **[NEW]** `tests/unit/test_job_generator_v2/test_error_feedback.py` | 新規追加 |
| **[NEW]** `tests/integration/test_llm_retry_with_feedback.py` | 新規追加 |

---

**作成日**: 2026-01-09
**作成者**: Claude Code
**対象Issue**: #343
