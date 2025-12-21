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
from pydantic import BaseModel, Field, field_validator

from app.services.prompt_loader import PromptLoader


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


def _build_schema_hint(api: dict) -> str:
    """Build compact schema hint for LLM prompt (Issue #270).

    Generates a hint showing required fields for the API.

    Args:
        api: API definition from YAML

    Returns:
        Formatted schema hint string (e.g., " [required: query, max_results]")
    """
    hints = []

    # Request schema hint
    if request_schema := api.get("request_schema"):
        required_fields = [
            k for k, v in request_schema.items() if v.get("required", False)
        ]
        if required_fields:
            hints.append(f"required: {', '.join(required_fields)}")

    return f" [{'; '.join(hints)}]" if hints else ""


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
            # Add schema hint (Issue #270)
            schema_hint = _build_schema_hint(api)
            lines.append(
                f"  - **{api['name']}** (`{api['endpoint']}`): "
                f"{api['description']} - {use_cases}{schema_hint}"
            )
        lines.append("")

    # AI Agent APIs
    ai_agent_apis = config.get("ai_agent_apis", [])
    if ai_agent_apis:
        lines.append("**AI Agent API (AI処理)**:")
        for api in ai_agent_apis:
            use_cases = "、".join(api.get("use_cases", []))
            # Add schema hint (Issue #270)
            schema_hint = _build_schema_hint(api)
            lines.append(
                f"  - **{api['name']}** (`{api['endpoint']}`): "
                f"{api['description']} - {use_cases}{schema_hint}"
            )

    return "\n".join(lines)


class RecommendedAPI(BaseModel):
    """Recommended API specification for a task."""

    api_name: str = Field(
        description="API名（例: 'Gmail送信', 'Text-to-Speech + Google Drive'）"
    )
    endpoint: str = Field(
        description="エンドポイントパス（例: '/v1/utility/gmail/send'）"
    )
    method: str = Field(
        default="POST",
        description="HTTPメソッド（通常はPOST）",
    )
    reason: str = Field(
        description="このAPIを選択した理由（例: '高速Direct APIで3-5秒でメール送信可能'）"
    )


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
    recommended_apis: list[RecommendedAPI] = Field(
        default_factory=list,
        description="推奨API一覧（API名、エンドポイント、理由を含む構造化形式）",
    )

    @field_validator("recommended_apis", mode="before")
    @classmethod
    def convert_string_apis_to_objects(cls, v):
        """Convert legacy string format to RecommendedAPI objects.

        This provides backward compatibility with LLM responses that use
        the old string format (e.g., ['fetchAgent']) instead of the new
        structured format.

        Args:
            v: Value to validate (can be list of strings or dicts)

        Returns:
            list: List of RecommendedAPI-compatible dicts
        """
        if not isinstance(v, list):
            return v

        result = []
        for item in v:
            if isinstance(item, str):
                # Convert legacy string format to structured format
                result.append(
                    {
                        "api_name": item,
                        "endpoint": "",  # Will be filled by LLM or set to empty
                        "method": "POST",
                        "reason": f"LLMが推奨（レガシー形式から自動変換: {item}）",
                    }
                )
            elif isinstance(item, dict):
                result.append(item)
            else:
                # Keep as-is for Pydantic to handle
                result.append(item)
        return result


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
    # Load prompt from YAML using PromptLoader
    loader = PromptLoader.create_default()
    prompt_data = loader.load_prompt("task_breakdown")

    # Get base prompt from YAML
    base_prompt = prompt_data.get("system_prompt", "")

    # Get expert_agent_capabilities to replace placeholder
    expert_agent_capabilities = _build_expert_agent_capabilities()

    # If YAML prompt is loaded, replace placeholder with capabilities
    if base_prompt:
        # Replace {expert_agent_capabilities} placeholder with actual capabilities
        base_prompt = base_prompt.replace(
            "{expert_agent_capabilities}", expert_agent_capabilities
        )
        return base_prompt

    # If no YAML prompt loaded, use fallback
    else:
        # Fallback to original hardcoded prompt
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

**重要**: `recommended_apis` は構造化された形式で記述してください。

#### 形式
```json
"recommended_apis": [
  {{
    "api_name": "API名",
    "endpoint": "エンドポイントパス",
    "method": "POST",
    "reason": "このAPIを選択した理由"
  }}
]
```

#### 禁止事項
以下の記述は**禁止**です（情報が不足しています）：
- ❌ `"recommended_apis": ["fetchAgent"]` - エンドポイントなし
- ❌ `"recommended_apis": ["fetchAgent (expertAgent jsonoutput API)"]` - 構造化されていない

#### タスク種別ごとの推奨API

| タスク種別 | 推奨API | エンドポイント |
|-----------|---------|---------------|
| 音声合成 | Text-to-Speech + Google Drive | `/v1/utility/text_to_speech_drive` |
| 音声合成（Base64） | Text-to-Speech | `/v1/utility/text_to_speech` |
| ファイルアップロード | Google Drive Upload | `/v1/utility/drive/upload` |
| メール送信 | Gmail送信 | `/v1/utility/gmail/send` |
| メール検索 | Gmail検索 | `/v1/utility/gmail/search` |
| Web検索 | Google検索 | `/v1/utility/google_search` |
| LLM処理（JSON出力） | JSON Output Agent | `/v1/aiagent/utility/jsonoutput` |
| LLM処理（汎用） | Direct LLM | `/v1/mylllm` |

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

### 例1: Gmailで特定キーワードを検索し、結果をGoogleドライブにアップロードする

```json
{{
  "tasks": [
    {{
      "task_id": "task_001",
      "name": "Gmail検索",
      "description": "指定されたキーワードでGmailを検索し、メール一覧を取得する。",
      "dependencies": [],
      "expected_output": "JSON形式のメール一覧 (件名、送信者、本文抜粋を含む)",
      "priority": 1,
      "recommended_apis": [
        {{
          "api_name": "Gmail検索",
          "endpoint": "/v1/utility/gmail/search",
          "method": "POST",
          "reason": "高速Direct API（5秒）でGmail検索が可能"
        }}
      ]
    }},
    {{
      "task_id": "task_002",
      "name": "検索結果フォーマット",
      "description": "Gmail検索結果をレポート形式にフォーマットする。LLMを使用して構造化されたレポートを生成。",
      "dependencies": ["task_001"],
      "expected_output": "レポート形式のテキストデータ",
      "priority": 2,
      "recommended_apis": [
        {{
          "api_name": "JSON Output Agent",
          "endpoint": "/v1/aiagent/utility/jsonoutput",
          "method": "POST",
          "reason": "構造化JSON出力を保証、gemini-2.5-flash推奨"
        }}
      ]
    }},
    {{
      "task_id": "task_003",
      "name": "Googleドライブアップロード",
      "description": "フォーマットされたレポートをGoogleドライブにアップロードする。",
      "dependencies": ["task_002"],
      "expected_output": "アップロード完了メッセージとファイルURL",
      "priority": 3,
      "recommended_apis": [
        {{
          "api_name": "Google Drive Upload",
          "endpoint": "/v1/utility/drive/upload",
          "method": "POST",
          "reason": "サブフォルダ自動作成・重複ファイル名回避対応"
        }}
      ]
    }}
  ],
  "overall_summary": "Gmail検索結果をレポート形式にフォーマットし、Google Driveにアップロードするワークフロー"
}}
```

### 例2: ポッドキャスト生成とメール通知

```json
{{
  "tasks": [
    {{
      "task_id": "task_001",
      "name": "ポッドキャスト構成案の作成",
      "description": "ユーザーが入力したキーワードに基づき、ポッドキャストのトピック、構成、主要なポイントを策定する。",
      "dependencies": [],
      "expected_output": "ポッドキャストのタイトル、セクションごとの要点を含むJSONデータ",
      "priority": 1,
      "recommended_apis": [
        {{
          "api_name": "JSON Output Agent",
          "endpoint": "/v1/aiagent/utility/jsonoutput",
          "method": "POST",
          "reason": "構造化された構成案をJSON形式で生成"
        }}
      ]
    }},
    {{
      "task_id": "task_002",
      "name": "音声合成用スクリプトの生成",
      "description": "作成された構成案を元に、自然な対話形式またはナレーション形式のスクリプトを作成する。",
      "dependencies": ["task_001"],
      "expected_output": "音声合成に適した正規化済みのスクリプトテキスト",
      "priority": 2,
      "recommended_apis": [
        {{
          "api_name": "JSON Output Agent",
          "endpoint": "/v1/aiagent/utility/jsonoutput",
          "method": "POST",
          "reason": "スクリプトを構造化されたJSON形式で生成"
        }}
      ]
    }},
    {{
      "task_id": "task_003",
      "name": "音声合成とGoogle Driveアップロード",
      "description": "生成されたスクリプトを音声ファイルに変換し、Google Driveにアップロードする。",
      "dependencies": ["task_002"],
      "expected_output": "音声ファイルの公開URL",
      "priority": 3,
      "recommended_apis": [
        {{
          "api_name": "Text-to-Speech + Google Drive",
          "endpoint": "/v1/utility/text_to_speech_drive",
          "method": "POST",
          "reason": "音声生成とアップロードを一括処理、公開リンクを返却"
        }}
      ]
    }},
    {{
      "task_id": "task_004",
      "name": "通知メール送信",
      "description": "ポッドキャストの完成を知らせるメールを送信する。音声ファイルのURLを含む。",
      "dependencies": ["task_003"],
      "expected_output": "送信完了ステータス",
      "priority": 4,
      "recommended_apis": [
        {{
          "api_name": "Gmail送信",
          "endpoint": "/v1/utility/gmail/send",
          "method": "POST",
          "reason": "高速Direct API（3-5秒）でメール送信可能"
        }}
      ]
    }}
  ],
  "overall_summary": "キーワードからポッドキャストを生成し、Google Driveにアップロード、完了通知をメール送信するワークフロー"
}}
```

## 出力形式

JSON形式で以下の構造で出力してください：

```json
{{
  "tasks": [
    {{
      "task_id": "task_001",
      "name": "タスク名",
      "description": "詳細な説明",
      "dependencies": [],
      "expected_output": "期待される出力",
      "priority": 1,
      "recommended_apis": [
        {{
          "api_name": "API名",
          "endpoint": "/v1/...",
          "method": "POST",
          "reason": "このAPIを選択した理由"
        }}
      ]
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
