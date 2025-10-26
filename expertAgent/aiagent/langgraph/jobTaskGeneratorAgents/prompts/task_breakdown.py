"""Prompt template for task breakdown from user requirements.

This module provides prompts and schemas for decomposing natural language
requirements into executable tasks following 4 principles:
1. Hierarchical decomposition
2. Clear dependencies
3. Specificity and executability
4. Modularity and reusability
"""

from pydantic import BaseModel, Field


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


TASK_BREAKDOWN_SYSTEM_PROMPT = """あなたはワークフロー設計の専門家です。
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

**GraphAI標準エージェント**:
- `geminiAgent`: Google Gemini APIを使用したLLM処理（推奨モデル: gemini-2.5-flash）
- `openAIAgent`: OpenAI APIを使用したLLM処理
- `fetchAgent`: HTTP APIコール（RESTful API呼び出し）
- `copyAgent`: データコピー・フォーマット変換
- `jsonParserAgent`: JSON解析（※ user_inputの解析には使用しない）

**expertAgent APIs**:
- `/api/v1/search`: 検索機能
- `/api/v1/email`: メール送信機能
- その他のDirect API

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
  description: "Gmail検索結果をPDF形式にフォーマットする。LLMを使用して自然言語処理とフォーマット生成を行う。"
  dependencies: ["task_001"]
  expected_output: "PDF形式のレポートファイル"
  recommended_apis: ["geminiAgent", "openAIAgent"]

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
{
  "tasks": [
    {
      "task_id": "task_001",
      "name": "タスク名",
      "description": "詳細な説明（使用APIの理由を含む）",
      "dependencies": [],
      "expected_output": "期待される出力",
      "priority": 5,
      "recommended_apis": ["geminiAgent", "fetchAgent"]
    }
  ],
  "overall_summary": "ワークフロー全体の概要"
}
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
