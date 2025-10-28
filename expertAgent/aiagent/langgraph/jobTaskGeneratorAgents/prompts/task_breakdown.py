"""Prompt template for task breakdown from user requirements.

This module provides prompts and schemas for decomposing natural language
requirements into executable tasks following 4 principles:
1. Hierarchical decomposition
2. Clear dependencies
3. Specificity and executability
4. Modularity and reusability
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


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


def _build_expert_agent_capabilities() -> str:
    """Build expertAgent capabilities section from YAML config.

    Returns:
        Formatted expertAgent capabilities string
    """
    config = _load_yaml_config("expert_agent_capabilities.yaml")
    lines = ["**expertAgent Direct API一覧**:", ""]

    # Utility APIs
    utility_apis = config.get("utility_apis", [])
    if utility_apis:
        lines.append("**Utility API (Direct API)**:")
        for api in utility_apis:
            use_cases = "、".join(api.get("use_cases", []))
            lines.append(
                f"  - **{api['name']}** (`{api['endpoint']}`): "
                f"{api['description']} - {use_cases}"
            )
        lines.append("")

    # AI Agent APIs
    ai_agent_apis = config.get("ai_agent_apis", [])
    if ai_agent_apis:
        lines.append("**AI Agent API (AI処理)**:")
        for api in ai_agent_apis:
            use_cases = "、".join(api.get("use_cases", []))
            lines.append(
                f"  - **{api['name']}** (`{api['endpoint']}`): "
                f"{api['description']} - {use_cases}"
            )

    return "\n".join(lines)


class TaskBreakdownItem(BaseModel):
    """Single task in the breakdown."""

    task_id: str = Field(description="Unique task identifier (e.g., 'task_001')")
    name: str = Field(description="Short task name (e.g., 'Search Gmail')")
    description: str = Field(
        description="Detailed task description with specific requirements"
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of task_ids that must complete before this task",
    )
    expected_output: str = Field(
        description="Expected output format and content (e.g., 'JSON with email list')"
    )
    priority: int = Field(
        default=5, ge=1, le=10, description="Task priority (1=highest, 10=lowest)"
    )
    recommended_apis: list[str] = Field(
        default_factory=list,
        description="Recommended GraphAI agents or expertAgent APIs for this task (e.g., ['geminiAgent', 'fetchAgent'])",
    )


class TaskBreakdownResponse(BaseModel):
    """Task breakdown response from LLM."""

    tasks: list[TaskBreakdownItem] = Field(
        default_factory=list,
        description="List of tasks decomposed from requirements",
    )
    overall_summary: str = Field(
        default="",
        description="Summary of the entire workflow and task relationships",
    )


def _build_task_breakdown_system_prompt() -> str:
    """Build task breakdown system prompt with dynamic capability lists.

    Returns:
        Formatted task breakdown system prompt
    """
    expert_agent_capabilities = _build_expert_agent_capabilities()

    return f"""あなたはワークフロー設計の専門家です。
ユーザーの自然言語要求を、実行可能なタスクに分解します。

以下の4原則に従ってタスク分解を行ってください：

## 1. 階層的分解の原則
- 大きな要求を、小さく実行可能なタスクに分解
- 各タスクは1つの明確な責務を持つ
- 複雑なタスクは、より小さなサブタスクに分解

## 2. 依存関係の明確化
- 各タスクの依存関係を明示的に定義
- タスク間のデータフローを明確にする
- 循環依存を避ける

## 3. 具体性と実行可能性
- 各タスクは具体的かつ測定可能な成果を持つ
- 入力と出力を明確に定義
- API呼び出しやデータ処理の詳細を含む

## 4. モジュール性と再利用性
- タスクは独立して実行可能
- 他のワークフローで再利用可能な設計
- 汎用的な命名と構造

## 5. 使用想定APIの明示
各タスクについて、実装に使用する想定APIを明示的に記述してください。

### 利用可能なAPI種別

**IMPORTANT**: GraphAI標準のLLMエージェント（geminiAgent, openAIAgent, anthropicAgent, groqAgent, replicateAgent）は使用禁止です。
LLM処理には必ず expertAgent の jsonoutput API を使用してください。

**LLM処理 (expertAgent jsonoutput API)**:
- LLM処理には必ず expertAgent の jsonoutput API を使用
- URL: `http://localhost:8104/aiagent-api/v1/aiagent/utility/jsonoutput`
- fetchAgent経由で呼び出す
- 推奨モデル:
  * `gemini-2.5-flash`: Google Gemini 2.5 Flash（推奨、高速・高品質）
  * `gpt-4o-mini`: OpenAI GPT-4o mini（フォールバック）
  * `claude-3-5-sonnet`: Anthropic Claude 3.5 Sonnet（高品質）
- JSON出力保証（マークダウン自動削除）

**その他のエージェント**:
- `fetchAgent`: HTTP APIコール（expertAgent jsonoutput API含む、RESTful API呼び出し）
- `copyAgent`: データコピー・フォーマット変換
- `jsonParserAgent`: JSON解析（※ user_inputの解析には使用しない）

{expert_agent_capabilities}

### recommended_apis の記述ルール

1. **優先順位順に記述**: 最も推奨するAPIを先頭に記載
2. **具体的に記述**: "geminiAgent" のように具体的なエージェント名を記載
3. **複数指定可能**: メインAPI + フォールバックAPIを指定可能
4. **理由を説明**: descriptionに「なぜそのAPIを使うか」を記載

## ⚠️ 重要な制約

### タスク数と優先度の制約
- **最大タスク数**: 10タスクまで
- **優先度の範囲**: 1～10 (1=最高優先度, 10=最低優先度)
- **絶対的なルール**: 優先度は必ず 1 以上 10 以下の整数であること
- 優先度11以上や0以下は**絶対に使用しないでください**（システムエラーになります）

例:
- ✅ 正しい: priority=1, priority=5, priority=10
- ❌ 間違い: priority=11, priority=0, priority=-1 (これらはシステムエラーを引き起こします)

## タスク分割の例

ユーザー要求: "Gmailで特定キーワードを検索し、結果をGoogleドライブにアップロードする"

分割結果:
```
task_001:
  name: "Gmail検索"
  description: "指定されたキーワードでGmailを検索し、メール一覧を取得する。Gmail APIを使用してHTTP経由でデータを取得。"
  dependencies: []
  expected_output: "JSON形式のメール一覧 (件名、送信者、本文抜粋を含む)"
  recommended_apis: ["fetchAgent"]

task_002:
  name: "検索結果フォーマット"
  description: "Gmail検索結果をPDF形式にフォーマットする。LLMを使用して自然言語処理とフォーマット生成を行う。expertAgent の jsonoutput API (http://localhost:8104/aiagent-api/v1/aiagent/utility/jsonoutput) を fetchAgent 経由で呼び出し、gemini-2.5-flash モデルを使用。"
  dependencies: ["task_001"]
  expected_output: "PDF形式のレポートファイル"
  recommended_apis: ["fetchAgent (expertAgent jsonoutput API)"]

task_003:
  name: "Googleドライブアップロード"
  description: "フォーマットされたレポートをGoogleドライブにアップロードする。Google Drive APIを使用してHTTP経由でアップロード。"
  dependencies: ["task_002"]
  expected_output: "アップロード完了メッセージとファイルURL"
  recommended_apis: ["fetchAgent"]
```

## 出力形式

JSON形式で以下の構造で出力してください：

```json
{{
  "tasks": [
    {{
      "task_id": "task_001",
      "name": "タスク名",
      "description": "詳細な説明（使用APIの理由を含む）。LLM処理が必要な場合は、expertAgent の jsonoutput API を fetchAgent 経由で呼び出す旨を記載。",
      "dependencies": [],
      "expected_output": "期待される出力",
      "priority": 5,
      "recommended_apis": ["fetchAgent (expertAgent jsonoutput API)"]
    }}
  ],
  "overall_summary": "ワークフロー全体の概要"
}}
```

タスクIDは必ず "task_001", "task_002", ... の形式で、ゼロパディング3桁で採番してください。
"""


def create_task_breakdown_prompt(user_requirement: str) -> str:
    """Create task breakdown prompt for LLM.

    Args:
        user_requirement: Natural language description of workflow

    Returns:
        Formatted prompt string for LLM
    """
    return f"""# ユーザー要求

{user_requirement}

# 指示

上記のユーザー要求を、4原則に従って実行可能なタスクに分解してください。

- 各タスクは独立して実行可能であること
- タスク間の依存関係を明確にすること
- 具体的な入力と出力を定義すること
- 全体として1つの完結したワークフローを構成すること

JSON形式で出力してください。
"""


def create_task_breakdown_prompt_with_feedback(
    user_requirement: str,
    evaluation_feedback: str,
) -> str:
    """Create task breakdown prompt with evaluation feedback for retry.

    Args:
        user_requirement: Natural language description of workflow
        evaluation_feedback: Feedback from evaluator about previous attempt

    Returns:
        Formatted prompt string for LLM with feedback context
    """
    return f"""# ユーザー要求

{user_requirement}

# 前回のタスク分解に対する評価フィードバック

前回のタスク分解には以下の問題が検出されました。これらの問題を解決した新しいタスク分解を生成してください。

{evaluation_feedback}

# 指示

上記のユーザー要求を、4原則に従って実行可能なタスクに分解してください。
**重要**: 前回の評価フィードバックで指摘された問題を必ず解決してください。

- 各タスクは独立して実行可能であること
- タスク間の依存関係を明確にすること
- 具体的な入力と出力を定義すること
- 全体として1つの完結したワークフローを構成すること
- **実現不可能なタスク（infeasible tasks）を含めないこと**
- **提案された代替案（alternative proposals）を考慮すること**

JSON形式で出力してください。
"""
