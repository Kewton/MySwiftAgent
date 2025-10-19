"""GraphAI and expertAgent capability management for feasibility evaluation.

This module provides structured data about available GraphAI standard agents
and expertAgent Direct APIs, used for evaluating task feasibility.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class GraphAIAgent:
    """GraphAI standard agent capability."""

    name: str
    category: Literal["llm", "http", "data_transform", "control_flow"]
    description: str
    requires_api_key: bool = False
    api_key_name: str | None = None


@dataclass
class ExpertAgentAPI:
    """expertAgent Direct API capability."""

    name: str
    endpoint: str
    category: Literal["utility", "ai_agent"]
    description: str
    use_cases: list[str]


@dataclass
class InfeasibleTaskAlternative:
    """Alternative solution for infeasible tasks."""

    task_type: str
    reason: str
    alternative_api: str
    priority: Literal["high", "medium", "low"]
    notes: str


# ===== GraphAI Standard Agents =====

GRAPHAI_AGENTS: list[GraphAIAgent] = [
    # LLM Agents
    GraphAIAgent(
        name="anthropicAgent",
        category="llm",
        description="Claude API直接呼び出し",
        requires_api_key=True,
        api_key_name="ANTHROPIC_API_KEY",
    ),
    GraphAIAgent(
        name="geminiAgent",
        category="llm",
        description="Gemini API直接呼び出し",
        requires_api_key=True,
        api_key_name="GOOGLE_API_KEY",
    ),
    # HTTP/Fetch Agents
    GraphAIAgent(
        name="fetchAgent",
        category="http",
        description="汎用HTTP APIクライアント（expertAgent呼び出しに使用）",
    ),
    # Data Transform Agents
    GraphAIAgent(
        name="arrayJoinAgent",
        category="data_transform",
        description="配列を文字列に結合",
    ),
    GraphAIAgent(
        name="copyAgent",
        category="data_transform",
        description="値をコピー",
    ),
    GraphAIAgent(
        name="stringTemplateAgent",
        category="data_transform",
        description="テンプレート文字列生成",
    ),
    GraphAIAgent(
        name="popAgent",
        category="data_transform",
        description="配列の最後の要素を取得",
    ),
    GraphAIAgent(
        name="pushAgent",
        category="data_transform",
        description="配列に要素を追加",
    ),
    GraphAIAgent(
        name="shiftAgent",
        category="data_transform",
        description="配列の最初の要素を取得",
    ),
    GraphAIAgent(
        name="mapAgent",
        category="data_transform",
        description="配列の各要素に関数を適用",
    ),
    GraphAIAgent(
        name="filterAgent",
        category="data_transform",
        description="配列をフィルタリング",
    ),
    GraphAIAgent(
        name="sortByAgent",
        category="data_transform",
        description="配列をソート",
    ),
    # Control Flow Agents
    GraphAIAgent(
        name="nestedAgent",
        category="control_flow",
        description="入力に対してグラフ全体を実行（ループ処理）",
    ),
    GraphAIAgent(
        name="mergeNodeIdAgent",
        category="control_flow",
        description="複数ノードの結果をマージ",
    ),
    GraphAIAgent(
        name="bypassAgent",
        category="control_flow",
        description="入力をそのまま出力",
    ),
]

# ===== expertAgent Direct APIs =====

EXPERT_AGENT_APIS: list[ExpertAgentAPI] = [
    # Utility APIs
    ExpertAgentAPI(
        name="Gmail検索",
        endpoint="/v1/utility/gmail_search",
        category="utility",
        description="Gmail検索",
        use_cases=["キーワード検索", "日付範囲指定"],
    ),
    ExpertAgentAPI(
        name="Gmail送信",
        endpoint="/v1/utility/gmail_send",
        category="utility",
        description="メール送信",
        use_cases=["宛先、件名、本文を指定"],
    ),
    ExpertAgentAPI(
        name="Google検索",
        endpoint="/v1/utility/google_search",
        category="utility",
        description="Web検索",
        use_cases=["キーワード検索"],
    ),
    ExpertAgentAPI(
        name="Google Drive Upload",
        endpoint="/v1/drive/upload",
        category="utility",
        description="ファイルアップロード",
        use_cases=["PDF", "画像", "テキストファイル"],
    ),
    ExpertAgentAPI(
        name="Text-to-Speech",
        endpoint="/v1/utility/tts",
        category="utility",
        description="音声合成",
        use_cases=["テキストを音声ファイルに変換"],
    ),
    # AI Agent APIs
    ExpertAgentAPI(
        name="Explorer Agent",
        endpoint="/v1/myagent/explorer",
        category="ai_agent",
        description="ファイルシステム探索",
        use_cases=["ディレクトリ構造の取得"],
    ),
    ExpertAgentAPI(
        name="Action Agent",
        endpoint="/v1/myagent/action",
        category="ai_agent",
        description="汎用アクション実行",
        use_cases=["複数API組み合わせ"],
    ),
    ExpertAgentAPI(
        name="File Reader Agent",
        endpoint="/v1/myagent/file_reader",
        category="ai_agent",
        description="ファイル読み取り",
        use_cases=["テキスト", "PDF", "画像の読み取り"],
    ),
    ExpertAgentAPI(
        name="Playwright Agent",
        endpoint="/v1/myagent/playwright",
        category="ai_agent",
        description="ブラウザ自動化",
        use_cases=["Web scraping", "フォーム操作"],
    ),
    ExpertAgentAPI(
        name="JSON Output Agent",
        endpoint="/v1/myagent/json_output",
        category="ai_agent",
        description="構造化出力",
        use_cases=["自然言語→JSON変換"],
    ),
]

# ===== Common Infeasible Tasks and Alternatives =====

INFEASIBLE_TASKS: list[InfeasibleTaskAlternative] = [
    InfeasibleTaskAlternative(
        task_type="Slack通知",
        reason="Slack APIなし",
        alternative_api="Gmail送信 (/v1/utility/gmail_send)",
        priority="low",
        notes="Gmail送信で十分代替可能",
    ),
    InfeasibleTaskAlternative(
        task_type="Discord通知",
        reason="Discord APIなし",
        alternative_api="Gmail送信 (/v1/utility/gmail_send)",
        priority="low",
        notes="Gmail送信で十分代替可能",
    ),
    InfeasibleTaskAlternative(
        task_type="SMS送信",
        reason="SMS APIなし",
        alternative_api="Gmail送信 (/v1/utility/gmail_send)",
        priority="medium",
        notes="メール送信で代替可能だが、SMS特有の用途がある場合は中優先度",
    ),
    InfeasibleTaskAlternative(
        task_type="Trello操作",
        reason="Trello APIなし",
        alternative_api="Google DriveでCSV管理",
        priority="low",
        notes="タスク管理はCSVで代替可能",
    ),
    InfeasibleTaskAlternative(
        task_type="Notion操作",
        reason="Notion APIなし",
        alternative_api="Google DriveでMarkdown管理",
        priority="medium",
        notes="ドキュメント管理はMarkdownで代替可能",
    ),
    InfeasibleTaskAlternative(
        task_type="データベース直接操作",
        reason="DB接続APIなし",
        alternative_api="File Reader/Writer + CSV",
        priority="high",
        notes="データ永続化が必要な場合は高優先度",
    ),
    InfeasibleTaskAlternative(
        task_type="SSH接続",
        reason="SSH APIなし",
        alternative_api="実装困難",
        priority="high",
        notes="リモート操作が必要な場合は高優先度",
    ),
    InfeasibleTaskAlternative(
        task_type="ファイル削除",
        reason="削除APIなし",
        alternative_api="実装困難",
        priority="medium",
        notes="ファイル管理が必要な場合は中優先度",
    ),
]


# ===== Utility Functions =====


def get_agent_by_name(agent_name: str) -> GraphAIAgent | None:
    """Get GraphAI agent by name.

    Args:
        agent_name: Agent name to search for

    Returns:
        GraphAIAgent if found, None otherwise
    """
    for agent in GRAPHAI_AGENTS:
        if agent.name == agent_name:
            return agent
    return None


def get_api_by_name(api_name: str) -> ExpertAgentAPI | None:
    """Get expertAgent API by name.

    Args:
        api_name: API name to search for

    Returns:
        ExpertAgentAPI if found, None otherwise
    """
    for api in EXPERT_AGENT_APIS:
        if api.name == api_name:
            return api
    return None


def find_alternative_for_task(task_type: str) -> InfeasibleTaskAlternative | None:
    """Find alternative solution for infeasible task.

    Args:
        task_type: Task type (e.g., "Slack通知")

    Returns:
        InfeasibleTaskAlternative if found, None otherwise
    """
    for alt in INFEASIBLE_TASKS:
        if task_type.lower() in alt.task_type.lower():
            return alt
    return None


def list_agents_by_category(
    category: Literal["llm", "http", "data_transform", "control_flow"],
) -> list[GraphAIAgent]:
    """List GraphAI agents by category.

    Args:
        category: Agent category

    Returns:
        List of GraphAIAgents in the specified category
    """
    return [agent for agent in GRAPHAI_AGENTS if agent.category == category]


def list_apis_by_category(
    category: Literal["utility", "ai_agent"],
) -> list[ExpertAgentAPI]:
    """List expertAgent APIs by category.

    Args:
        category: API category

    Returns:
        List of ExpertAgentAPIs in the specified category
    """
    return [api for api in EXPERT_AGENT_APIS if api.category == category]


def get_all_capabilities_summary() -> dict:
    """Get summary of all available capabilities.

    Returns:
        Dictionary with GraphAI agents, expertAgent APIs, and infeasible task alternatives
    """
    return {
        "graphai_agents": {
            "total": len(GRAPHAI_AGENTS),
            "by_category": {
                "llm": len(list_agents_by_category("llm")),
                "http": len(list_agents_by_category("http")),
                "data_transform": len(list_agents_by_category("data_transform")),
                "control_flow": len(list_agents_by_category("control_flow")),
            },
        },
        "expert_agent_apis": {
            "total": len(EXPERT_AGENT_APIS),
            "by_category": {
                "utility": len(list_apis_by_category("utility")),
                "ai_agent": len(list_apis_by_category("ai_agent")),
            },
        },
        "infeasible_tasks": {
            "total": len(INFEASIBLE_TASKS),
            "by_priority": {
                "high": len([t for t in INFEASIBLE_TASKS if t.priority == "high"]),
                "medium": len([t for t in INFEASIBLE_TASKS if t.priority == "medium"]),
                "low": len([t for t in INFEASIBLE_TASKS if t.priority == "low"]),
            },
        },
    }
