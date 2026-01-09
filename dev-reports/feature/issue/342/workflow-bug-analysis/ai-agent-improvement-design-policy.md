# AIエージェント ワークフロー生成 改善設計方針書

## 概要

- **作成日**: 2026-01-09
- **対象**: expertAgent ワークフロー生成機能（Job Generator V2）
- **目的**: AI生成ワークフローの品質向上と実行成功率の改善
- **関連Issue**: #342

---

## 第1章: 発見された問題点の分類

### 1.1 問題点サマリー

| # | カテゴリ | 重大度 | 影響 | 根本原因 |
|---|---------|--------|------|----------|
| P1 | APIスキーマ誤り | 🔴 Critical | 実行時エラー | API仕様の未参照 |
| P2 | ソースパス参照誤り | 🔴 Critical | データ取得失敗 | JobQueue統合ルール未理解 |
| P3 | stringTemplateAgent誤解 | 🔴 Critical | データ欠落 | Agent仕様の誤解 |
| P4 | user_input型制約誤解 | 🔴 Critical | HTTP 422 | 型制約の未認識 |
| P5 | タイムアウト単位誤り | 🟡 Major | タイムアウト | 単位の誤認識 |
| P6 | 環境変数URL使用 | 🟡 Major | 接続失敗 | 実行環境の誤解 |
| P7 | 不要な中間ノード | 🟢 Minor | 可読性低下 | 最適化不足 |
| P8 | 記事コンテンツ未取得 | 🔴 Critical | 品質低下 | 設計パターン欠如 |

### 1.2 問題の詳細分析

#### P1: APIスキーマの誤り

**症状**:
```yaml
# AI生成（誤）
body:
  query: "検索キーワード"    # パラメータ名が違う
  num_results: 3             # パラメータ名が違う
```

**正解**:
```yaml
body:
  queries: ["検索キーワード"]  # 配列型、複数形
  num: 3                       # 略称
```

**根本原因**: AIがAPI仕様書（OpenAPI/Swagger）を参照せずに推測でパラメータを生成

**影響範囲**: 全タスク（Google検索、LLM呼び出し、メール送信）

---

#### P2: ソースパス参照の誤り

**症状**:
```yaml
# AI生成（誤）
inputs:
  query: :source.query
  results: :source.search_results
```

**正解**:
```yaml
inputs:
  query: :source.user_input.query
  results: :source.user_input.search_results
```

**根本原因**: JobQueueの`body_template`変換メカニズムを理解していない

**JobQueue body_template変換ルール**:
```json
{
  "user_input": "{{tasks[N-1].output_data}}",  // 前タスクの出力
  "job_params": "{{job.body}}",                // ジョブパラメータ
  "model_name": "taskmaster/..."               // TaskMaster識別子
}
```

**影響範囲**: 全タスク（データフロー全体）

---

#### P3: stringTemplateAgentの機能誤解

**症状**:
```yaml
# AI生成（誤）
params:
  template: |
    検索結果: ${JSON.stringify(results)}
```

**実際の出力**:
```
検索結果: ${JSON.stringify(results)}  # リテラル文字列
```

**根本原因**: `stringTemplateAgent`がJavaScript式を評価すると誤解

**技術的事実**:
- `stringTemplateAgent`は**単純な変数置換のみ**を行う
- `${varName}`形式で変数を参照
- JavaScript関数（`JSON.stringify()`等）は**評価されない**
- オブジェクトは`[object Object]`としてリテラル出力

---

#### P4: user_input型制約の誤解

**症状**:
```yaml
# AI生成（誤）
body:
  user_input:
    task: "要約生成"
    keyword: :source.job_params.query
    search_results: :source.user_input.search_results
```

**エラー**:
```json
{
  "detail": "Validation error",
  "errors": [{
    "type": "string_type",
    "loc": ["body", "user_input"],
    "msg": "Input should be a valid string"
  }]
}
```

**根本原因**: `/aiagent/utility/jsonoutput`の`user_input`が`str`型のみ受け付けることを認識していない

---

#### P5: タイムアウト単位の誤り

**症状**:
```yaml
# AI生成（誤）
timeout: 180  # 秒と誤解 → 実際は180ミリ秒 = 0.18秒
```

**正解**:
```yaml
timeout: 180000  # ミリ秒 = 180秒 = 3分
```

**根本原因**: GraphAIのtimeoutがミリ秒単位であることを認識していない

---

#### P6: 環境変数URLの使用

**症状**:
```yaml
# AI生成（誤）
url: ${EXPERTAGENT_BASE_URL}/aiagent-api/v1/...
```

**正解**:
```yaml
url: http://localhost:8004/aiagent-api/v1/...
```

**根本原因**: GraphAI実行時に`${...}`形式が解決されないことを認識していない

---

#### P7: 不要な中間ノードの生成

**症状**:
```yaml
# AI生成（不要）
extract_search_results:
  agent: copyAgent
  inputs:
    search_results: :source.search_results
  params:
    namedKey: search_results  # 使用方法が誤り
```

**根本原因**: 最適化不足、Agent APIの誤解

---

#### P8: 記事コンテンツ未取得

**症状**:
- Google検索のスニペット（約150文字）のみを使用
- LLMは「スニペットの再整形」しかできない
- 記事の深い内容が含まれない

**根本原因**: 「検索→記事取得→要約」のワークフローパターンが存在しない

---

## 第2章: AIエージェントへの改善方針

### 2.1 改善方針の全体像

```
┌─────────────────────────────────────────────────────────────────┐
│                    改善方針アーキテクチャ                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │  入力強化   │ →  │  生成改善   │ →  │  検証強化   │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│        │                  │                  │                 │
│        ▼                  ▼                  ▼                 │
│  ・API仕様書注入     ・Few-shot改善    ・スキーマ検証          │
│  ・統合ルール追加    ・制約条件明記    ・パス検証              │
│  ・Agent仕様明記     ・パターン提供    ・実行前テスト          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 入力強化（プロンプト改善）

#### 2.2.1 API仕様書の注入

**現状**: AIはAPI仕様を推測で生成
**改善**: OpenAPIスキーマをプロンプトに含める

```yaml
# プロンプトに追加する情報
available_apis:
  - endpoint: /utility/google_search
    method: POST
    request_schema:
      queries:
        type: array
        items: string
        description: "検索クエリの配列"
      num:
        type: integer
        max: 3
        description: "結果件数"
    response_schema:
      search_results: array
      search_results_count: integer
```

#### 2.2.2 JobQueue統合ルールの追加

**現状**: ソースパス参照ルールが未定義
**改善**: `GRAPHAI_WORKFLOW_GENERATION_RULES.md`に追加

```markdown
## ソースパス参照ルール

### 必須ルール
- 前タスクの出力を参照: `:source.user_input.{field_name}`
- ジョブパラメータを参照: `:source.job_params.{field_name}`
- 同一ワークフロー内のノード出力: `:{node_name}.{field_name}`

### 禁止パターン
- ❌ `:source.{field_name}` （user_input/job_params欠落）
- ❌ `:source.body.{field_name}` （bodyは存在しない）
```

#### 2.2.3 Agent仕様の明記

**現状**: stringTemplateAgentの制限が未記載
**改善**: 各Agentの制限事項を明記

```markdown
## stringTemplateAgent 制限事項

### できること
- `${varName}` 形式での変数置換
- 複数変数の埋め込み

### できないこと
- ❌ JavaScript式の評価（`${JSON.stringify()}`は動作しない）
- ❌ 条件分岐、ループ
- ❌ オブジェクトの自動文字列化（`[object Object]`になる）

### オブジェクト→文字列変換が必要な場合
1. `/utility/json_stringify` APIを先に呼び出す
2. 文字列化された結果をstringTemplateAgentに渡す
```

### 2.3 生成改善（Few-shot・制約条件）

#### 2.3.1 Few-shotサンプルの拡充

**追加すべきパターン**:

| パターン | 用途 |
|---------|------|
| Google検索→LLM要約 | 検索結果の要約 |
| Google検索→記事取得→LLM要約 | 記事コンテンツの要約 |
| API呼び出し→データ変換→出力 | データパイプライン |
| オブジェクト→文字列→テンプレート | stringTemplateAgent使用 |

#### 2.3.2 制約条件の明記

```yaml
# ワークフロー生成時の制約条件
constraints:
  timeout:
    unit: milliseconds
    min: 1000
    max: 300000
    default: 30000

  source_path:
    required_prefix:
      - ":source.user_input."
      - ":source.job_params."
    forbidden_patterns:
      - ":source.{field}"  # user_input/job_params欠落

  url:
    forbidden_patterns:
      - "${ENV_VAR}"  # 環境変数は解決されない
    required_format: "http(s)://host:port/path"
```

#### 2.3.3 標準ワークフローパターンの提供

**パターン: 記事コンテンツ要約**

```yaml
# 標準パターン: Google検索 → 記事取得 → LLM要約
nodes:
  # Step 1: 検索結果からURLを抽出
  extract_urls:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/utility/extract_article_urls
      method: POST
      body:
        search_results: :source.user_input.search_results
        max_urls: 2

  # Step 2: 記事コンテンツを取得
  fetch_article_1:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/utility/fetch_web_content
      method: POST
      body:
        url: :extract_urls.article_url_1

  # Step 3: オブジェクトを文字列化
  stringify_content:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/utility/json_stringify
      method: POST
      body:
        data: :fetch_article_1.markdown_content

  # Step 4: プロンプト構築
  build_prompt:
    agent: stringTemplateAgent
    inputs:
      content: :stringify_content.json_string
    params:
      template: |
        以下の記事を要約してください：
        ${content}

  # Step 5: LLM呼び出し
  generate_summary:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/aiagent/utility/jsonoutput
      method: POST
      body:
        user_input: :build_prompt  # 文字列型
        model_name: gemini-2.0-flash
        force_json: true
    timeout: 120000
```

### 2.4 検証強化（生成後チェック）

#### 2.4.1 スキーマ検証

```python
def validate_workflow_schema(workflow: dict) -> list[str]:
    """生成されたワークフローのスキーマを検証"""
    errors = []

    for node_name, node in workflow.get("nodes", {}).items():
        # timeout検証
        timeout = node.get("timeout")
        if timeout and timeout < 1000:
            errors.append(
                f"[{node_name}] timeout={timeout}は秒単位の可能性があります。"
                "ミリ秒単位（例: 30000）で指定してください。"
            )

        # URL検証
        if "inputs" in node:
            url = node["inputs"].get("url")
            if url and "${" in str(url):
                errors.append(
                    f"[{node_name}] URLに環境変数が含まれています。"
                    "GraphAIは環境変数を解決しません。"
                )

    return errors
```

#### 2.4.2 ソースパス検証

```python
def validate_source_paths(workflow: dict) -> list[str]:
    """ソースパス参照の検証"""
    errors = []

    VALID_PREFIXES = [
        ":source.user_input.",
        ":source.job_params.",
    ]

    for node_name, node in workflow.get("nodes", {}).items():
        inputs = node.get("inputs", {})
        for key, value in inputs.items():
            if isinstance(value, str) and value.startswith(":source."):
                if not any(value.startswith(p) for p in VALID_PREFIXES):
                    if value.startswith(":source.") and "." not in value[8:]:
                        errors.append(
                            f"[{node_name}.{key}] パス '{value}' は無効です。"
                            ":source.user_input.xxx または :source.job_params.xxx を使用してください。"
                        )

    return errors
```

#### 2.4.3 stringTemplateAgent検証

```python
def validate_string_template(workflow: dict) -> list[str]:
    """stringTemplateAgentのテンプレート検証"""
    errors = []

    JS_PATTERNS = [
        r"\$\{.*JSON\.stringify.*\}",
        r"\$\{.*\.map\(.*\}",
        r"\$\{.*\.filter\(.*\}",
        r"\$\{.*\.reduce\(.*\}",
    ]

    for node_name, node in workflow.get("nodes", {}).items():
        if node.get("agent") == "stringTemplateAgent":
            template = node.get("params", {}).get("template", "")
            for pattern in JS_PATTERNS:
                if re.search(pattern, template):
                    errors.append(
                        f"[{node_name}] テンプレートにJavaScript式が含まれています。"
                        "stringTemplateAgentはJavaScript式を評価しません。"
                        "/utility/json_stringify APIを使用してください。"
                    )

    return errors
```

---

## 第3章: 設計方針

### 3.1 アーキテクチャ設計

```
┌─────────────────────────────────────────────────────────────────┐
│                   ワークフロー生成パイプライン                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐    │
│  │ 要件分析 │ → │ タスク   │ → │ワークフロー│ → │ 検証     │    │
│  │          │   │ 分解     │   │ 生成      │   │          │    │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘    │
│       │              │              │              │           │
│       ▼              ▼              ▼              ▼           │
│  ・ユーザー要件  ・API選択     ・YAML生成     ・スキーマ検証   │
│  ・コンテキスト  ・データフロー ・パス設定     ・パス検証      │
│  ・制約条件      ・依存関係    ・タイムアウト  ・テンプレート検証│
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    強化コンポーネント                     │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │  ・APIスキーマインジェクター                             │   │
│  │  ・ソースパスルールエンジン                              │   │
│  │  ・Agent制約バリデーター                                 │   │
│  │  ・ワークフローパターンライブラリ                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 コンポーネント設計

#### 3.2.0 抽象インターフェース定義【必須】

**目的**: 将来の拡張性確保とテスタビリティ向上

```python
from abc import ABC, abstractmethod
from typing import Protocol
import logging

logger = logging.getLogger(__name__)


class WorkflowValidator(ABC):
    """ワークフロー検証の基底クラス"""

    @abstractmethod
    def validate(self, workflow: dict) -> list[str]:
        """
        ワークフローを検証し、エラーリストを返す

        Args:
            workflow: 検証対象のワークフロー辞書

        Returns:
            エラーメッセージのリスト（空リストは検証成功）
        """
        pass

    def log_errors(self, errors: list[str], workflow_id: str = "") -> None:
        """検証エラーをログ出力"""
        if errors:
            logger.warning(
                f"Workflow validation errors [{workflow_id}]: {len(errors)} errors found",
                extra={"errors": errors, "workflow_id": workflow_id}
            )


class PromptInjector(Protocol):
    """プロンプト注入のプロトコル"""

    def inject(self, prompt: str, context: dict) -> str:
        """プロンプトに情報を注入"""
        ...


class PatternProvider(Protocol):
    """パターン提供のプロトコル"""

    def get_pattern(self, pattern_name: str) -> dict | None:
        """パターン名からテンプレートを取得"""
        ...

    def suggest_pattern(self, requirements: str) -> str:
        """要件からパターンを提案"""
        ...
```

#### 3.2.1 APIスキーマインジェクター

**責務**: プロンプトにAPI仕様を注入
**実装**: `PromptInjector`プロトコルを実装

```python
class APISchemaInjector(PromptInjector):
    """API仕様をプロンプトに注入するコンポーネント"""

    def __init__(self, openapi_spec_path: str):
        self.spec = self._load_spec(openapi_spec_path)

    def inject(self, prompt: str, required_apis: list[str]) -> str:
        """プロンプトにAPI仕様を注入"""
        api_docs = []
        for api in required_apis:
            if api in self.spec:
                api_docs.append(self._format_api_doc(api, self.spec[api]))

        return prompt + "\n\n## 利用可能なAPI仕様\n" + "\n".join(api_docs)
```

#### 3.2.2 ソースパスルールエンジン

**責務**: ソースパス参照ルールの適用と検証

```python
class SourcePathRuleEngine:
    """ソースパス参照ルールを管理するエンジン"""

    RULES = {
        "previous_task_output": ":source.user_input.{field}",
        "job_parameters": ":source.job_params.{field}",
        "same_workflow_node": ":{node_name}.{field}",
    }

    def generate_path(self, context: str, field: str) -> str:
        """コンテキストに応じた正しいパスを生成"""
        if context == "previous_task":
            return f":source.user_input.{field}"
        elif context == "job_params":
            return f":source.job_params.{field}"
        else:
            raise ValueError(f"Unknown context: {context}")

    def validate_path(self, path: str) -> tuple[bool, str]:
        """パスの妥当性を検証"""
        if path.startswith(":source.") and not (
            path.startswith(":source.user_input.") or
            path.startswith(":source.job_params.")
        ):
            return False, "user_input または job_params が必要です"
        return True, ""
```

#### 3.2.3 Agent制約バリデーター

**責務**: Agent固有の制約を検証

```python
class AgentConstraintValidator:
    """Agent固有の制約を検証するバリデーター"""

    CONSTRAINTS = {
        "stringTemplateAgent": {
            "forbidden_patterns": [
                r"\$\{.*JSON\.",
                r"\$\{.*\.\w+\(",
            ],
            "message": "JavaScript式は評価されません。/utility/json_stringifyを使用してください。"
        },
        "fetchAgent": {
            "required_fields": ["url", "method"],
            "timeout_unit": "milliseconds",
            "timeout_range": (1000, 300000),
        }
    }

    def validate(self, agent: str, config: dict) -> list[str]:
        """Agent設定を検証"""
        errors = []
        constraints = self.CONSTRAINTS.get(agent, {})

        # 禁止パターンのチェック
        if "forbidden_patterns" in constraints:
            template = config.get("params", {}).get("template", "")
            for pattern in constraints["forbidden_patterns"]:
                if re.search(pattern, template):
                    errors.append(constraints["message"])

        # タイムアウト範囲のチェック
        if "timeout_range" in constraints:
            timeout = config.get("timeout", 30000)
            min_t, max_t = constraints["timeout_range"]
            if timeout < min_t:
                errors.append(f"timeout={timeout}は小さすぎます（最小: {min_t}ms）")

        return errors
```

#### 3.2.4 ワークフローパターンライブラリ

**責務**: 標準ワークフローパターンの提供

```python
class WorkflowPatternLibrary:
    """標準ワークフローパターンを提供するライブラリ"""

    PATTERNS = {
        "search_and_summarize": {
            "description": "Google検索→スニペット要約",
            "nodes": ["google_search", "stringify", "build_prompt", "llm_call"],
        },
        "search_fetch_summarize": {
            "description": "Google検索→記事取得→コンテンツ要約",
            "nodes": ["google_search", "extract_urls", "fetch_articles",
                     "stringify", "build_prompt", "llm_call"],
        },
        "api_transform_output": {
            "description": "API呼び出し→データ変換→出力",
            "nodes": ["api_call", "transform", "output"],
        },
    }

    def get_pattern(self, pattern_name: str) -> dict:
        """パターン名からワークフローテンプレートを取得"""
        return self.PATTERNS.get(pattern_name)

    def suggest_pattern(self, requirements: str) -> str:
        """要件からパターンを提案"""
        if "記事" in requirements and "要約" in requirements:
            return "search_fetch_summarize"
        elif "検索" in requirements and "要約" in requirements:
            return "search_and_summarize"
        else:
            return "api_transform_output"
```

### 3.3 実装優先度

| 優先度 | コンポーネント | 対象問題 | 工数見積 |
|--------|---------------|---------|---------|
| P0 | APIスキーマインジェクター | P1 | 2日 |
| P0 | ソースパスルールエンジン | P2 | 1日 |
| P0 | Agent制約バリデーター | P3, P4, P5 | 2日 |
| P1 | ワークフローパターンライブラリ | P8 | 3日 |
| P1 | 統合検証パイプライン | 全体 | 2日 |
| P2 | Few-shotサンプル拡充 | 全体 | 2日 |

### 3.4 成功指標

| 指標 | 現状 | 目標 |
|------|------|------|
| ワークフロー生成成功率 | 30% | 90% |
| 初回実行成功率 | 10% | 70% |
| 検証エラー検出率 | 0% | 95% |
| 記事コンテンツ要約品質 | 低（スニペットのみ） | 高（本文要約） |

### 3.5 テスト設計【必須】

#### 3.5.1 テスト戦略

| テスト種別 | カバレッジ目標 | 対象 |
|-----------|--------------|------|
| 単体テスト | 90%以上 | 各バリデーター、インジェクター |
| 結合テスト | 50%以上 | 検証パイプライン全体 |
| 受入テスト | - | エンドツーエンドワークフロー生成 |

#### 3.5.2 単体テスト設計

**SourcePathRuleEngine テスト**

```python
# tests/unit/test_source_path_rule_engine.py
import pytest
from aiagent.langgraph.jobGeneratorV2.validators import SourcePathRuleEngine


class TestSourcePathRuleEngine:
    """ソースパスルールエンジンのテスト"""

    @pytest.fixture
    def engine(self):
        return SourcePathRuleEngine()

    # 正常系テスト
    def test_validate_path_with_valid_user_input(self, engine):
        """user_input経由の参照は有効"""
        is_valid, error = engine.validate_path(":source.user_input.query")
        assert is_valid is True
        assert error == ""

    def test_validate_path_with_valid_job_params(self, engine):
        """job_params経由の参照は有効"""
        is_valid, error = engine.validate_path(":source.job_params.model_name")
        assert is_valid is True

    def test_validate_path_with_node_reference(self, engine):
        """同一ワークフロー内ノード参照は有効"""
        is_valid, error = engine.validate_path(":search_node.results")
        assert is_valid is True

    # 異常系テスト
    def test_validate_path_with_invalid_source_direct(self, engine):
        """user_input/job_params欠落は無効"""
        is_valid, error = engine.validate_path(":source.query")
        assert is_valid is False
        assert "user_input" in error or "job_params" in error

    def test_validate_path_with_invalid_source_body(self, engine):
        """source.body形式は無効"""
        is_valid, error = engine.validate_path(":source.body.field")
        assert is_valid is False

    # パス生成テスト
    def test_generate_path_previous_task(self, engine):
        """前タスク出力参照のパス生成"""
        path = engine.generate_path("previous_task", "search_results")
        assert path == ":source.user_input.search_results"

    def test_generate_path_job_params(self, engine):
        """ジョブパラメータ参照のパス生成"""
        path = engine.generate_path("job_params", "query")
        assert path == ":source.job_params.query"
```

**AgentConstraintValidator テスト**

```python
# tests/unit/test_agent_constraint_validator.py
import pytest
from aiagent.langgraph.jobGeneratorV2.validators import AgentConstraintValidator


class TestAgentConstraintValidator:
    """Agent制約バリデーターのテスト"""

    @pytest.fixture
    def validator(self):
        return AgentConstraintValidator()

    # stringTemplateAgent テスト
    def test_string_template_valid_simple(self, validator):
        """単純な変数置換は有効"""
        config = {
            "agent": "stringTemplateAgent",
            "params": {"template": "Query: ${query}"}
        }
        errors = validator.validate("stringTemplateAgent", config)
        assert len(errors) == 0

    def test_string_template_invalid_json_stringify(self, validator):
        """JSON.stringify使用は無効"""
        config = {
            "agent": "stringTemplateAgent",
            "params": {"template": "Data: ${JSON.stringify(results)}"}
        }
        errors = validator.validate("stringTemplateAgent", config)
        assert len(errors) > 0
        assert "json_stringify" in errors[0].lower() or "JavaScript" in errors[0]

    def test_string_template_invalid_map_function(self, validator):
        """配列操作関数使用は無効"""
        config = {
            "agent": "stringTemplateAgent",
            "params": {"template": "${items.map(x => x.name)}"}
        }
        errors = validator.validate("stringTemplateAgent", config)
        assert len(errors) > 0

    # timeout テスト
    def test_fetch_agent_valid_timeout(self, validator):
        """ミリ秒単位のtimeoutは有効"""
        config = {"timeout": 30000}
        errors = validator.validate("fetchAgent", config)
        assert len(errors) == 0

    def test_fetch_agent_invalid_timeout_too_small(self, validator):
        """小さすぎるtimeout（秒単位の可能性）は警告"""
        config = {"timeout": 180}  # 180ms = 秒単位の誤りの可能性
        errors = validator.validate("fetchAgent", config)
        assert len(errors) > 0
        assert "ミリ秒" in errors[0] or "milliseconds" in errors[0].lower()
```

**WorkflowSchemaValidator テスト**

```python
# tests/unit/test_workflow_schema_validator.py
import pytest
from aiagent.langgraph.jobGeneratorV2.validators import WorkflowSchemaValidator


class TestWorkflowSchemaValidator:
    """ワークフロースキーマバリデーターのテスト"""

    @pytest.fixture
    def validator(self):
        return WorkflowSchemaValidator()

    def test_valid_workflow(self, validator):
        """有効なワークフローは検証成功"""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "http://localhost:8004/api",
                        "method": "POST"
                    },
                    "timeout": 30000
                }
            }
        }
        errors = validator.validate(workflow)
        assert len(errors) == 0

    def test_invalid_env_var_in_url(self, validator):
        """URLに環境変数が含まれる場合はエラー"""
        workflow = {
            "nodes": {
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERT_AGENT_URL}/api"
                    }
                }
            }
        }
        errors = validator.validate(workflow)
        assert len(errors) > 0
        assert "環境変数" in errors[0] or "environment" in errors[0].lower()

    def test_invalid_timeout_seconds(self, validator):
        """秒単位と思われるtimeoutはエラー"""
        workflow = {
            "nodes": {
                "llm": {
                    "agent": "fetchAgent",
                    "timeout": 60  # 60ms = 秒単位の誤り
                }
            }
        }
        errors = validator.validate(workflow)
        assert len(errors) > 0
```

#### 3.5.3 結合テスト設計

```python
# tests/integration/test_validation_pipeline.py
import pytest
from aiagent.langgraph.jobGeneratorV2.validators import ValidationPipeline


class TestValidationPipeline:
    """検証パイプライン結合テスト"""

    @pytest.fixture
    def pipeline(self):
        return ValidationPipeline()

    def test_pipeline_catches_all_errors(self, pipeline):
        """複数種類のエラーを持つワークフローで全エラーを検出"""
        workflow = {
            "nodes": {
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${ENV_VAR}/api",  # P6: 環境変数
                        "query": ":source.query"  # P2: パス誤り
                    },
                    "timeout": 30  # P5: 単位誤り
                },
                "format": {
                    "agent": "stringTemplateAgent",
                    "params": {
                        "template": "${JSON.stringify(data)}"  # P3: JS式
                    }
                }
            }
        }
        errors = pipeline.validate(workflow)
        assert len(errors) >= 4  # 最低4種類のエラーを検出

    def test_pipeline_passes_valid_workflow(self, pipeline):
        """有効なワークフローは検証成功"""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "http://localhost:8004/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "queries": ":source.user_input.queries"
                        }
                    },
                    "timeout": 30000
                }
            }
        }
        errors = pipeline.validate(workflow)
        assert len(errors) == 0
```

### 3.6 ログ・監視設計【必須】

#### 3.6.1 ログ出力方針

| ログレベル | 用途 | 出力先 |
|-----------|------|--------|
| ERROR | 検証失敗（ワークフロー生成中断） | ファイル + Langfuse |
| WARNING | 検証警告（生成続行、修正推奨） | ファイル + Langfuse |
| INFO | 検証成功、パイプライン開始/終了 | ファイル |
| DEBUG | 各バリデーターの詳細結果 | ファイル（開発時のみ） |

#### 3.6.2 ログフォーマット

```python
import logging
import json
from datetime import datetime

class StructuredLogFormatter(logging.Formatter):
    """構造化ログフォーマッター"""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # 追加フィールド
        if hasattr(record, "workflow_id"):
            log_entry["workflow_id"] = record.workflow_id
        if hasattr(record, "errors"):
            log_entry["errors"] = record.errors
        if hasattr(record, "validator"):
            log_entry["validator"] = record.validator

        return json.dumps(log_entry, ensure_ascii=False)
```

#### 3.6.3 Langfuse統合

```python
from langfuse import Langfuse

class ValidationObserver:
    """検証結果をLangfuseに送信するオブザーバー"""

    def __init__(self):
        self.langfuse = Langfuse()

    def observe_validation(
        self,
        workflow_id: str,
        errors: list[str],
        duration_ms: float
    ):
        """検証結果をLangfuseに記録"""
        self.langfuse.score(
            trace_id=workflow_id,
            name="workflow_validation",
            value=1.0 if len(errors) == 0 else 0.0,
            comment=f"Errors: {len(errors)}"
        )

        if errors:
            self.langfuse.event(
                trace_id=workflow_id,
                name="validation_errors",
                metadata={
                    "errors": errors,
                    "duration_ms": duration_ms
                }
            )
```

### 3.7 セキュリティ対策

#### 3.7.1 ReDoS対策

正規表現パターンにおけるReDoS（Regular Expression Denial of Service）脆弱性を防止：

```python
import re
from typing import Pattern

# 安全な正規表現パターン（非貪欲マッチ、バックトラック制限）
SAFE_JS_PATTERNS: list[Pattern] = [
    re.compile(r"\$\{[^}]{0,100}JSON\.stringify[^}]{0,100}\}"),  # 長さ制限
    re.compile(r"\$\{[^}]{0,100}\.map\([^}]{0,50}\)\}"),
    re.compile(r"\$\{[^}]{0,100}\.filter\([^}]{0,50}\)\}"),
    re.compile(r"\$\{[^}]{0,100}\.reduce\([^}]{0,50}\)\}"),
]

def validate_template_safe(template: str, max_length: int = 10000) -> list[str]:
    """ReDoS対策付きテンプレート検証"""
    errors = []

    # 入力長制限
    if len(template) > max_length:
        return [f"テンプレートが長すぎます（最大: {max_length}文字）"]

    # タイムアウト付き正規表現マッチ
    for pattern in SAFE_JS_PATTERNS:
        try:
            if pattern.search(template):
                errors.append(
                    "JavaScript式が検出されました。"
                    "/utility/json_stringify APIを使用してください。"
                )
                break  # 1つ見つかれば十分
        except re.error:
            pass  # 正規表現エラーは無視

    return errors
```

#### 3.7.2 入力サニタイズ

```python
def sanitize_path_input(path: str, max_length: int = 500) -> str:
    """パス入力のサニタイズ"""
    if not isinstance(path, str):
        raise ValueError("パスは文字列である必要があります")

    if len(path) > max_length:
        raise ValueError(f"パスが長すぎます（最大: {max_length}文字）")

    # 危険な文字の除去
    sanitized = path.replace("\x00", "").replace("\n", "").replace("\r", "")

    return sanitized
```

---

## 第4章: 新規API仕様

### 4.1 追加されたAPI

#### `/utility/fetch_web_content`

**目的**: URLからWebページコンテンツをMarkdown形式で取得

```yaml
endpoint: /utility/fetch_web_content
method: POST
request:
  url: string (required)
  upload_to_drive: boolean (default: false)
response:
  markdown_content: string
  status: "success" | "failed"
  error: string | null
```

**使用例**:
```yaml
fetch_article:
  agent: fetchAgent
  inputs:
    url: http://localhost:8004/aiagent-api/v1/utility/fetch_web_content
    method: POST
    body:
      url: :extract_urls.article_url_1
      upload_to_drive: false
  timeout: 60000
```

#### `/utility/extract_article_urls`

**目的**: ネストされた検索結果から記事URLを抽出

```yaml
endpoint: /utility/extract_article_urls
method: POST
request:
  search_results: array (required)
  max_urls: integer (default: 2, max: 5)
response:
  article_url_1: string | null
  article_url_2: string | null
  article_url_3: string | null
  urls: array
  count: integer
```

**使用例**:
```yaml
extract_urls:
  agent: fetchAgent
  inputs:
    url: http://localhost:8004/aiagent-api/v1/utility/extract_article_urls
    method: POST
    body:
      search_results: :source.user_input.search_results
      max_urls: 2
  timeout: 30000
```

### 4.2 既存APIの補足

#### `/utility/json_stringify`

**重要性**: stringTemplateAgentでオブジェクトを扱う際に必須

```yaml
# 使用パターン
stringify_data:
  agent: fetchAgent
  inputs:
    url: http://localhost:8004/aiagent-api/v1/utility/json_stringify
    method: POST
    body:
      data: :source.user_input.complex_object  # 任意の構造
  timeout: 30000

build_prompt:
  agent: stringTemplateAgent
  inputs:
    json_data: :stringify_data.json_string  # 文字列化済み
  params:
    template: |
      データ: ${json_data}  # 正しく展開される
```

---

## 第5章: 次のアクション

### 5.1 即時対応（1週間以内）

- [ ] `GRAPHAI_WORKFLOW_GENERATION_RULES.md` にソースパスルールを追加
- [ ] `GRAPHAI_WORKFLOW_GENERATION_RULES.md` にstringTemplateAgent制限事項を追加
- [ ] `GRAPHAI_WORKFLOW_GENERATION_RULES.md` にtimeout単位を明記
- [ ] Few-shotサンプルに「記事コンテンツ要約」パターンを追加

### 5.2 短期対応（1ヶ月以内）

- [ ] APIスキーマインジェクターの実装
- [ ] ソースパスルールエンジンの実装
- [ ] Agent制約バリデーターの実装
- [ ] 検証パイプラインの統合

### 5.3 中期対応（3ヶ月以内）

- [ ] ワークフローパターンライブラリの実装
- [ ] 自動パターン選択機能の実装
- [ ] 品質メトリクス収集・分析基盤の構築

---

## 付録

### A. 関連ドキュメント

- [総合分析レポート](./comprehensive-analysis-summary.md)
- [GRAPHAI_WORKFLOW_GENERATION_RULES.md](../../../../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)
- [Job Generator V2 設計書](../v2-task-breakdown-api-design-policy.md)

### B. 変更履歴

| 日付 | バージョン | 変更内容 |
|------|-----------|---------|
| 2026-01-09 | 1.0 | 初版作成 |
| 2026-01-09 | 1.1 | アーキテクチャレビュー指摘事項を反映 |
|            |     | - 3.2.0 抽象インターフェース定義を追加 |
|            |     | - 3.5 テスト設計セクションを追加（単体・結合テスト） |
|            |     | - 3.6 ログ・監視設計セクションを追加 |
|            |     | - 3.7 セキュリティ対策セクションを追加（ReDoS対策） |
