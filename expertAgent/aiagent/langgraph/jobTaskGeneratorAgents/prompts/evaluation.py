"""Prompt template for task evaluation and feasibility analysis.

This module provides prompts and schemas for evaluating task breakdown quality
according to 6 principles:
1-4. Four principles (hierarchical, dependencies, specificity, modularity)
5. Overall consistency
6. Feasibility (implementable with GraphAI + expertAgent Direct API)
"""

from pydantic import BaseModel, Field


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


# GraphAI Standard Agents capability list
GRAPHAI_CAPABILITIES = """
### GraphAI 標準Agent一覧

#### 🤖 LLM Agents
- `anthropicAgent`: Claude API直接呼び出し (ANTHROPIC_API_KEY必要)
- `geminiAgent`: Gemini API直接呼び出し (GOOGLE_API_KEY必要)

#### 📡 HTTP/Fetch Agents
- `fetchAgent`: 汎用HTTP APIクライアント（expertAgent呼び出しに使用）

#### 🔄 データ変換 Agents
- `arrayJoinAgent`: 配列を文字列に結合
- `copyAgent`: 値をコピー
- `stringTemplateAgent`: テンプレート文字列生成
- `popAgent`: 配列の最後の要素を取得
- `pushAgent`: 配列に要素を追加
- `shiftAgent`: 配列の最初の要素を取得
- `mapAgent`: 配列の各要素に関数を適用
- `filterAgent`: 配列をフィルタリング
- `sortByAgent`: 配列をソート

#### 🔀 制御フロー Agents
- `nestedAgent`: 入力に対してグラフ全体を実行（ループ処理）
- `mergeNodeIdAgent`: 複数ノードの結果をマージ
- `bypassAgent`: 入力をそのまま出力
"""

# expertAgent Direct API capability list
EXPERT_AGENT_CAPABILITIES = """
### expertAgent Direct API一覧

#### Utility API (Direct API)
| API | エンドポイント | 用途 | 使用例 |
|-----|-------------|------|-------|
| Gmail検索 | `/v1/utility/gmail_search` | Gmail検索 | キーワード検索、日付範囲指定 |
| Gmail送信 | `/v1/utility/gmail_send` | メール送信 | 宛先、件名、本文を指定 |
| Google検索 | `/v1/utility/google_search` | Web検索 | キーワード検索 |
| Google Drive Upload | `/v1/drive/upload` | ファイルアップロード | PDF、画像、テキストファイル |
| Text-to-Speech | `/v1/utility/tts` | 音声合成 | テキストを音声ファイルに変換 |

#### AI Agent API (Direct API)
| Agent | エンドポイント | 用途 | 使用例 |
|-------|-------------|------|-------|
| Explorer Agent | `/v1/myagent/explorer` | ファイルシステム探索 | ディレクトリ構造の取得 |
| Action Agent | `/v1/myagent/action` | 汎用アクション実行 | 複数API組み合わせ |
| File Reader Agent | `/v1/myagent/file_reader` | ファイル読み取り | テキスト、PDF、画像の読み取り |
| Playwright Agent | `/v1/myagent/playwright` | ブラウザ自動化 | Web scraping、フォーム操作 |
| JSON Output Agent | `/v1/myagent/json_output` | 構造化出力 | 自然言語→JSON変換 |
"""

# Common infeasible tasks and alternatives
INFEASIBLE_TASKS_TABLE = """
### 実現困難なタスクと代替案

| 実現困難なタスク | 理由 | 代替案 | API機能追加が必要か |
|---------------|------|-------|------------------|
| **Slack通知** | Slack APIなし | Gmail送信で代替 | 低優先度で提案可能 |
| **Discord通知** | Discord APIなし | Gmail送信で代替 | 低優先度で提案可能 |
| **SMS送信** | SMS APIなし | Gmail送信で代替 | 中優先度で提案可能 |
| **Trello操作** | Trello APIなし | Google DriveでCSV管理 | 低優先度で提案可能 |
| **Notion操作** | Notion APIなし | Google DriveでMarkdown管理 | 中優先度で提案可能 |
| **データベース直接操作** | DB接続APIなし | File Reader/Writer + CSV | 高優先度で提案可能 |
| **SSH接続** | SSH APIなし | 実装困難 | 高優先度で提案可能 |
| **ファイル削除** | 削除APIなし | 実装困難 | 中優先度で提案可能 |
"""

EVALUATION_SYSTEM_PROMPT = f"""あなたはワークフロー品質評価の専門家です。
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
- **重要**: 各タスクがGraphAI標準Agent + expertAgent Direct APIで実現可能かを評価

## 利用可能な機能

{GRAPHAI_CAPABILITIES}

{EXPERT_AGENT_CAPABILITIES}

{INFEASIBLE_TASKS_TABLE}

## 実現可能性評価の手順

1. **各タスクの実装方法を検討**
   - GraphAI標準Agentで実装可能か？
   - expertAgent Direct APIで実装可能か？
   - 複数APIの組み合わせで実装可能か？

2. **実現困難なタスクの検出**
   - 上記の機能リストに該当するAPIがない
   - 複数APIを組み合わせても実装困難

3. **代替案の検討** (優先度順)
   - 既存APIでの代替方法を提案
   - 例: Slack通知 → Gmail送信で代替

4. **API機能追加の提案** (代替不可の場合)
   - 新しいDirect API機能の提案
   - 優先度を判定 (high/medium/low)
   - high: ビジネス価値が高く、代替手段がない
   - medium: 有用だが、代替手段が存在する
   - low: Nice-to-have、既存機能で十分対応可能

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
