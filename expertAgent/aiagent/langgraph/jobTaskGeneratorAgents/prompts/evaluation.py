"""Prompt template for task evaluation and feasibility analysis.

This module provides prompts and schemas for evaluating task breakdown quality
according to 6 principles:
1-4. Four principles (hierarchical, dependencies, specificity, modularity)
5. Overall consistency
6. Feasibility (implementable with GraphAI + expertAgent Direct API)
"""

import json
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator


def _load_yaml_config(filename: str) -> dict:
    """Load YAML configuration file from utils/config directory.

    Args:
        filename: YAML filename in utils/config/ directory

    Returns:
        Parsed YAML data
    """
    # Navigate to utils/config from prompts directory
    config_dir = Path(__file__).parent.parent / "utils" / "config"
    config_path = config_dir / filename
    with open(config_path, encoding="utf-8") as f:
        result = yaml.safe_load(f)
        return result if isinstance(result, dict) else {}


class InfeasibleTask(BaseModel):
    """Task that is difficult to implement."""

    task_id: str = Field(description="ID of infeasible task")
    task_name: str = Field(description="Name of infeasible task")
    reason: str = Field(description="Reason why it's difficult to implement")
    required_functionality: str = Field(
        description="Required functionality that is missing"
    )


class AlternativeProposal(BaseModel):
    """Alternative solution using existing APIs."""

    task_id: str = Field(description="ID of infeasible task")
    alternative_approach: str = Field(
        description="Alternative approach using existing APIs"
    )
    api_to_use: str = Field(description="Existing API to use (e.g., 'Gmail send')")
    implementation_note: str = Field(
        description="Notes on how to implement the alternative"
    )


class APIExtensionProposal(BaseModel):
    """Proposal for new Direct API feature."""

    task_id: str = Field(description="ID of infeasible task")
    proposed_api_name: str = Field(description="Proposed API name (e.g., 'Slack send')")
    functionality: str = Field(description="Functionality of the proposed API")
    priority: str = Field(
        description="Priority (high/medium/low)",
        pattern="^(high|medium|low)$",
    )
    rationale: str = Field(description="Rationale for the priority level")


class EvaluationResult(BaseModel):
    """Evaluation result from LLM."""

    is_valid: bool = Field(description="Whether the task breakdown is valid")
    evaluation_summary: str = Field(description="Summary of evaluation results")

    # Principle 1-4 evaluation
    hierarchical_score: int = Field(
        ge=1, le=10, description="Hierarchical decomposition score (1-10)"
    )
    dependency_score: int = Field(
        ge=1, le=10, description="Dependency clarity score (1-10)"
    )
    specificity_score: int = Field(
        ge=1, le=10, description="Specificity and executability score (1-10)"
    )
    modularity_score: int = Field(
        ge=1, le=10, description="Modularity and reusability score (1-10)"
    )
    consistency_score: int = Field(
        ge=1, le=10, description="Overall consistency score (1-10)"
    )

    # Feasibility evaluation
    all_tasks_feasible: bool = Field(
        description="Whether all tasks are feasible with current capabilities"
    )
    infeasible_tasks: list[InfeasibleTask] = Field(
        default_factory=list, description="List of infeasible tasks"
    )
    alternative_proposals: list[AlternativeProposal] = Field(
        default_factory=list, description="Alternative solutions using existing APIs"
    )
    api_extension_proposals: list[APIExtensionProposal] = Field(
        default_factory=list, description="Proposals for new Direct API features"
    )

    # Issues and improvements
    issues: list[str] = Field(
        default_factory=list, description="List of identified issues"
    )
    improvement_suggestions: list[str] = Field(
        default_factory=list, description="Suggestions for improvement"
    )

    @field_validator("issues", "improvement_suggestions", mode="before")
    @classmethod
    def parse_string_to_list(cls, v):
        """Convert string representation of list to actual list.

        This handles cases where LLM returns a JSON array as a string
        instead of an actual list, e.g., '["item1", "item2"]' instead of ["item1", "item2"].

        Args:
            v: Value to validate (can be list or string)

        Returns:
            list[str]: Parsed list or original list
        """
        if isinstance(v, str):
            # Try to parse as JSON array
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    # Ensure all elements are strings
                    return [str(item) for item in parsed]
            except (json.JSONDecodeError, ValueError):
                # If JSON parse fails, treat as single-item list
                return [v] if v.strip() else []
        return v

    @field_validator(
        "infeasible_tasks",
        "alternative_proposals",
        "api_extension_proposals",
        mode="before",
    )
    @classmethod
    def parse_json_array_field(cls, v, info):
        """Convert string representation of JSON array to actual list of objects.

        This handles cases where LLM returns a JSON array as a string
        instead of an actual list of objects.

        Args:
            v: Value to validate (can be list or string)
            info: Field validation info

        Returns:
            list: Parsed list or original list
        """
        if isinstance(v, str):
            # Try to parse as JSON array
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                # If JSON parse fails, return empty list
                return []
        return v


def _build_graphai_capabilities() -> str:
    """Build GraphAI capabilities section from YAML config.

    Returns:
        Formatted GraphAI capabilities string
    """
    config = _load_yaml_config("graphai_capabilities.yaml")
    lines = ["### GraphAI 標準Agent一覧", ""]

    # LLM Agents
    llm_agents = config.get("llm_agents", [])
    if llm_agents:
        lines.append("#### 🤖 LLM Agents")
        for agent in llm_agents:
            api_key = (
                f" ({agent['api_key_name']}必要)"
                if agent.get("requires_api_key")
                else ""
            )
            lines.append(f"- `{agent['name']}`: {agent['description']}{api_key}")
        lines.append("")

    # HTTP Agents
    http_agents = config.get("http_agents", [])
    if http_agents:
        lines.append("#### 📡 HTTP/Fetch Agents")
        for agent in http_agents:
            lines.append(f"- `{agent['name']}`: {agent['description']}")
        lines.append("")

    # Data Transform Agents
    data_transform_agents = config.get("data_transform_agents", [])
    if data_transform_agents:
        lines.append("#### 🔄 データ変換 Agents")
        for agent in data_transform_agents:
            lines.append(f"- `{agent['name']}`: {agent['description']}")
        lines.append("")

    # Control Flow Agents
    control_flow_agents = config.get("control_flow_agents", [])
    if control_flow_agents:
        lines.append("#### 🔀 制御フロー Agents")
        for agent in control_flow_agents:
            lines.append(f"- `{agent['name']}`: {agent['description']}")

    return "\n".join(lines)


def _build_expert_agent_capabilities() -> str:
    """Build expertAgent capabilities section from YAML config.

    Returns:
        Formatted expertAgent capabilities string
    """
    config = _load_yaml_config("expert_agent_capabilities.yaml")
    lines = ["### expertAgent Direct API一覧", ""]

    # Utility APIs
    utility_apis = config.get("utility_apis", [])
    if utility_apis:
        lines.append("#### Utility API (Direct API)")
        lines.append("| API | エンドポイント | 用途 | 使用例 |")
        lines.append("|-----|-------------|------|-------|")
        for api in utility_apis:
            use_cases = "、".join(api.get("use_cases", []))
            lines.append(
                f"| {api['name']} | `{api['endpoint']}` | "
                f"{api['description']} | {use_cases} |"
            )
        lines.append("")

    # AI Agent APIs
    ai_agent_apis = config.get("ai_agent_apis", [])
    if ai_agent_apis:
        lines.append("#### AI Agent API (Direct API)")
        lines.append("| Agent | エンドポイント | 用途 | 使用例 |")
        lines.append("|-------|-------------|------|-------|")
        for api in ai_agent_apis:
            use_cases = "、".join(api.get("use_cases", []))
            lines.append(
                f"| {api['name']} | `{api['endpoint']}` | "
                f"{api['description']} | {use_cases} |"
            )

    return "\n".join(lines)


def _build_infeasible_tasks_table() -> str:
    """Build infeasible tasks table from YAML config.

    Returns:
        Formatted infeasible tasks table string
    """
    config = _load_yaml_config("infeasible_tasks.yaml")
    tasks = config.get("infeasible_tasks", [])

    lines = [
        "### 実現困難なタスクと代替案",
        "",
        "| 実現困難なタスク | 理由 | 代替案 | API機能追加が必要か |",
        "|---------------|------|-------|------------------|",
    ]

    for task in tasks:
        priority_label = f"{task['priority']}優先度で提案可能"
        lines.append(
            f"| **{task['task_type']}** | {task['reason']} | "
            f"{task['alternative_api']} | {priority_label} |"
        )

    return "\n".join(lines)


def _build_evaluation_system_prompt() -> str:
    """Build evaluation system prompt with dynamic capability lists.

    Returns:
        Formatted evaluation system prompt
    """
    graphai_capabilities = _build_graphai_capabilities()
    expert_agent_capabilities = _build_expert_agent_capabilities()
    infeasible_tasks_table = _build_infeasible_tasks_table()

    return f"""あなたはワークフロー品質評価の専門家です。
タスク分割結果を6つの観点で評価します。

## 評価観点

### 1-4. 4原則の評価 (各10点満点)

#### 1. 階層的分解の原則
- タスクは適切な粒度に分解されているか
- 各タスクは単一の責務を持っているか
- 複雑なタスクはサブタスクに分解されているか

#### 2. 依存関係の明確化
- タスク間の依存関係が明示されているか
- データフローが明確か
- 循環依存がないか

#### 3. 具体性と実行可能性
- 各タスクは具体的かつ測定可能か
- 入力と出力が明確に定義されているか
- API呼び出しの詳細が含まれているか

#### 4. モジュール性と再利用性
- タスクは独立して実行可能か
- 他のワークフローで再利用可能か
- 汎用的な命名と構造か

### 5. 全体整合性 (10点満点)
- ワークフロー全体として整合性があるか
- タスク間の連携が適切か
- ユーザー要求を満たしているか

### 6. 実現可能性
- **重要**: 各タスクが以下のいずれかで実現可能かを評価
  1. GraphAI標準Agent
  2. expertAgent Direct API
  3. **LLMベース実装**（データ分析、テキスト処理、構造化出力）← Phase 9拡張
  4. **Playwright Agent実装**（限定的: URL操作・基本的なページ操作のみ）← Phase 9拡張
  5. **外部API連携**（fetchAgentによるREST API呼び出し、要API key登録）← Phase 9拡張
  6. 上記の組み合わせによる複合ワークフロー

**注意**: Playwright Agentは現状挙動が不安定なため、
「指定URLへのアクセス + 基本操作 + URL取得」程度の限定的な用途のみ実装可能と判定。
複雑なデータ収集やフォーム送信は実現困難と判定。

## 利用可能な機能

{graphai_capabilities}

{expert_agent_capabilities}

{infeasible_tasks_table}

## 実現可能性評価の手順

1. **各タスクの実装方法を検討**
   - GraphAI標準Agentで実装可能か？
   - expertAgent Direct APIで実装可能か？
   - **LLMベース実装で実装可能か？**（geminiAgent (推奨)/anthropicAgent/openAIAgentによるテキスト処理・データ分析）
   - **Playwright Agentで実装可能か？**（限定的: URL操作のみ）
   - **外部API連携で実装可能か？**（fetchAgent + user API key）
   - 複数APIの組み合わせで実装可能か？

2. **実現困難なタスクの検出**
   - 上記の機能リストに該当するAPIがない
   - 複数APIを組み合わせても実装困難
   - **LLMでも実装困難**（リアルタイム性必須、物理デバイス操作等）
   - **Playwright Agentで実装困難**（複雑なデータ収集、フォーム送信）

3. **代替案の検討** (優先度順)
   - 既存APIでの代替方法を提案
   - **LLMベース代替案**: データ分析・テキスト処理は geminiAgent で実装 (推奨: コスト効率◎)
   - **fetchAgent + FileReader Agent代替案**: Playwright不使用のデータ取得
   - **外部API連携代替案**: fetchAgent + user API key（Slack、Notion等）
   - 例: Slack通知 → Gmail送信で代替

4. **API機能追加の提案** (代替不可の場合)
   - 新しいDirect API機能の提案
   - 優先度を判定 (high/medium/low)
   - high: ビジネス価値が高く、代替手段がない
   - medium: 有用だが、代替手段が存在する
   - low: Nice-to-have、既存機能で十分対応可能（例: Slack API key登録で実装可能）

## LLMベース実装の評価基準（Phase 9）

LLMで実装可能なタスク：
- 📊 **データ分析**: 財務データ解釈、統計分析、トレンド分析
- 📝 **テキスト処理**: 要約、分類、抽出、翻訳、感情分析
- 🔧 **構造化出力**: JSON/Markdown/HTML生成、表作成
- 💡 **自然言語理解**: 意図推定、エンティティ抽出
- 💻 **コード生成**: Python/JavaScript等のコード生成

評価例：
- ✅ "売上データを分析してトレンドをまとめる" → geminiAgent で実装可能 (推奨)
- ✅ "ニュース記事を要約する" → geminiAgent で実装可能 (推奨)
- ✅ "データをMarkdown表に変換" → geminiAgent で実装可能 (推奨)
- ❌ "株価をリアルタイムで監視する" → リアルタイム性が必要で実装困難

## Playwright Agent実装の評価基準（Phase 9、制限的）

⚠️ **重要**: Playwright Agentは現状挙動が不安定なため、限定的な用途のみ実装可能と判定

Playwright Agentで実装可能なタスク：
- 🌐 **URL操作**: 指定URLへのアクセス
- 🔘 **基本的なページ操作**: クリック、入力等の単純な操作
- 🔗 **URL取得**: 操作後のURLを取得

Playwright Agentで実装困難なタスク（代替案を提案）：
- ❌ **複雑なデータ収集**: 大量データのスクレイピング → fetchAgent + FileReader Agentで代替
- ❌ **フォーム送信**: Webフォームの入力・送信 → fetchAgent (POST request) で代替
- ❌ **認証が必要なサイト**: ログインが必要な会員サイトのデータ取得 → 実装困難

評価例：
- ⚠️ "企業IRページから財務データを取得" → Google検索 + fetchAgent + FileReader Agentで実装可能（Playwright不使用）
- ✅ "特定URLにアクセスしてリンク先URLを取得" → Playwright Agentで実装可能
- ❌ "ニュース記事を大量に収集" → fetchAgent + anthropicAgentで代替推奨

## 外部API連携の評価基準（Phase 9）

fetchAgentで実装可能なタスク（要API key登録）：
- 📱 **通知サービス**: Slack、Discord、SMS（ユーザーがAPI key登録済み）
- 📊 **プロジェクト管理**: Notion、Trello（ユーザーがAPI key登録済み）
- 🔍 **専門API**: 天気、地図、翻訳等の外部サービス

評価例：
- ✅ "Slack通知を送信" → fetchAgent + Slack API (要API key) で実装可能
- ✅ "Notionにデータを保存" → fetchAgent + Notion API (要API key) で実装可能
- ⚠️ "API keyが未登録の場合" → 実現困難だが、代替案として「myVaultにAPI key登録」を提案

## 評価結果の出力

JSON形式で以下の構造で出力してください：

```json
{{
  "is_valid": true,
  "evaluation_summary": "評価サマリー",
  "hierarchical_score": 8,
  "dependency_score": 9,
  "specificity_score": 7,
  "modularity_score": 8,
  "consistency_score": 8,
  "all_tasks_feasible": false,
  "infeasible_tasks": [
    {{
      "task_id": "task_003",
      "task_name": "Slack通知",
      "reason": "Slack APIが存在しない",
      "required_functionality": "Slack channel への message post API"
    }}
  ],
  "alternative_proposals": [
    {{
      "task_id": "task_003",
      "alternative_approach": "Gmail送信で代替",
      "api_to_use": "Gmail send (/v1/utility/gmail_send)",
      "implementation_note": "Slack通知の代わりにメール送信を使用。宛先を通知対象者のメールアドレスに設定。"
    }}
  ],
  "api_extension_proposals": [
    {{
      "task_id": "task_003",
      "proposed_api_name": "Slack send",
      "functionality": "Slackチャンネルへのメッセージ投稿",
      "priority": "low",
      "rationale": "Gmail送信で十分代替可能なため、優先度は低い"
    }}
  ],
  "issues": ["問題点のリスト"],
  "improvement_suggestions": ["改善提案のリスト"]
}}
```

## 評価基準

- 各スコアが7点以上かつ all_tasks_feasible が true → is_valid: true
- 実現困難なタスクがある場合:
  - 代替案がある → is_valid: true (代替案を適用)
  - 代替案がない → is_valid: false (API機能追加が必要)
- いずれかのスコアが7点未満 → is_valid: false
"""


# Build prompt at module load time (cached)
EVALUATION_SYSTEM_PROMPT = _build_evaluation_system_prompt()


def create_evaluation_prompt(
    user_requirement: str,
    task_breakdown: list[dict],
) -> str:
    """Create evaluation prompt for LLM.

    Args:
        user_requirement: Original user requirement
        task_breakdown: Task breakdown result to evaluate

    Returns:
        Formatted prompt string for LLM
    """
    import json

    return f"""# ユーザー要求

{user_requirement}

# タスク分割結果

```json
{json.dumps(task_breakdown, ensure_ascii=False, indent=2)}
```

# 指示

上記のタスク分割結果を6つの観点で評価してください。

特に、**実現可能性評価**を重視してください：
1. 各タスクが利用可能な機能で実現可能かを確認
2. 実現困難なタスクを検出
3. 既存APIでの代替案を提案
4. 代替不可の場合、API機能追加を提案

JSON形式で評価結果を出力してください。
"""
