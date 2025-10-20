"""API endpoints for Job/Task Auto-Generation."""

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException

from aiagent.langgraph.jobTaskGeneratorAgents import (
    create_initial_state,
    create_job_task_generator_agent,
)
from app.schemas.job_generator import JobGeneratorRequest, JobGeneratorResponse
from core.secrets import secrets_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/job-generator",
    response_model=JobGeneratorResponse,
    summary="Job/Task Auto-Generation",
    description="Automatically generate Job and Tasks from natural language requirements using LangGraph agent",
    tags=["Job Generator"],
)
async def generate_job_and_tasks(
    request: JobGeneratorRequest,
) -> JobGeneratorResponse:
    """Generate Job and Tasks from natural language requirements.

    This endpoint uses a LangGraph agent to:
    1. Analyze user requirements and decompose into tasks
    2. Evaluate task quality and feasibility
    3. Define JSON Schema interfaces
    4. Create TaskMasters, JobMaster, and JobMasterTask associations
    5. Validate workflow interfaces
    6. Register executable Job

    Args:
        request: Job generation request with user requirement

    Returns:
        Job generation response with job_id, status, and detailed results

    Raises:
        HTTPException: If job generation fails critically
    """
    logger.info(f"Job generation request received: {request.user_requirement[:100]}...")

    try:
        # Load ANTHROPIC_API_KEY from myVault and set as environment variable
        # This is required for ChatAnthropic to work properly
        try:
            anthropic_api_key = secrets_manager.get_secret(
                "ANTHROPIC_API_KEY", project=None
            )
            os.environ["ANTHROPIC_API_KEY"] = anthropic_api_key
            logger.info(
                f"ANTHROPIC_API_KEY loaded from myVault (prefix: {anthropic_api_key[:20]}..., length: {len(anthropic_api_key)})"
            )
        except ValueError as e:
            logger.error(f"Failed to load ANTHROPIC_API_KEY from myVault: {e}")
            raise HTTPException(
                status_code=500,
                detail="ANTHROPIC_API_KEY not configured in myVault. Please add it via CommonUI.",
            ) from e

        # Create initial state
        initial_state = create_initial_state(
            user_requirement=request.user_requirement,
        )

        # Override max retry count if specified
        if request.max_retry != 5:
            logger.info(f"Using custom max_retry: {request.max_retry}")
            # Note: MAX_RETRY_COUNT is defined in agent.py (5 by default)
            # This would require agent modification to support dynamic retry count
            # For now, we log the request but use the default value

        # Create and invoke LangGraph agent
        logger.info("Creating Job/Task Generator Agent")
        agent = create_job_task_generator_agent()

        logger.info("Invoking LangGraph agent")
        # Phase 8: Set recursion_limit to 50 (default is 25)
        final_state = await agent.ainvoke(initial_state, config={"recursion_limit": 50})

        logger.info("LangGraph agent execution completed")
        logger.debug(f"Final state keys: {final_state.keys()}")

        # Extract results from final state
        return _build_response_from_state(final_state)

    except Exception as e:
        logger.error(f"Job generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Job generation failed: {str(e)}",
        ) from e


def _build_response_from_state(state: dict[str, Any]) -> JobGeneratorResponse:
    """Build JobGeneratorResponse from final LangGraph state.

    Args:
        state: Final state from LangGraph agent execution

    Returns:
        JobGeneratorResponse with extracted information
    """
    # Check for error in state
    error_message = state.get("error_message")

    # Extract job information
    job_id = state.get("job_id")
    job_master_id = state.get("job_master_id")

    # Extract task breakdown
    task_breakdown = state.get("task_breakdown")

    # Extract evaluation result
    evaluation_result = state.get("evaluation_result")

    # Extract infeasible tasks and proposals from evaluation_result
    infeasible_tasks: list[dict[str, Any]] = []
    alternative_proposals: list[dict[str, Any]] = []
    api_extension_proposals: list[dict[str, Any]] = []

    if evaluation_result:
        infeasible_tasks = evaluation_result.get("infeasible_tasks", [])
        alternative_proposals = evaluation_result.get("alternative_proposals", [])
        api_extension_proposals = evaluation_result.get("api_extension_proposals", [])

    # Generate requirement relaxation suggestions (Phase 10-D: Capability-based approach)
    requirement_relaxation_suggestions = _generate_requirement_relaxation_suggestions(
        state
    )

    # Extract validation errors
    validation_result = state.get("validation_result")
    validation_errors: list[str] = []
    if validation_result and not validation_result.get("is_valid", True):
        validation_errors = validation_result.get("errors", [])

    # Determine status and generate user-friendly feedback
    if error_message:
        status = "failed"
        logger.warning(f"Job generation failed: {error_message}")
    elif job_id:
        if infeasible_tasks or api_extension_proposals:
            status = "partial_success"
            logger.info(
                f"Job generation partially successful (Job ID: {job_id}) "
                f"with {len(infeasible_tasks)} infeasible tasks"
            )

            # Generate user-friendly feedback for partial success
            feedback_parts = [
                f"Job successfully created (ID: {job_id}), but some tasks may require manual review:"
            ]

            if infeasible_tasks:
                feedback_parts.append(
                    f"\n{len(infeasible_tasks)} task(s) marked as potentially infeasible:"
                )
                for task in infeasible_tasks[:3]:  # Show first 3 tasks
                    task_name = task.get("task_name", "Unknown")
                    reason = task.get("reason", "No reason provided")
                    feedback_parts.append(f"  - {task_name}: {reason}")
                if len(infeasible_tasks) > 3:
                    feedback_parts.append(
                        f"  ... and {len(infeasible_tasks) - 3} more. See 'infeasible_tasks' for full list."
                    )

            if alternative_proposals:
                feedback_parts.append(
                    f"\n{len(alternative_proposals)} alternative proposal(s) available:"
                )
                for proposal in alternative_proposals[:3]:  # Show first 3 proposals
                    task_id = proposal.get("task_id", "unknown")
                    api = proposal.get("api_to_use", "unknown API")
                    feedback_parts.append(f"  - Task {task_id}: Consider using {api}")
                if len(alternative_proposals) > 3:
                    feedback_parts.append(
                        f"  ... and {len(alternative_proposals) - 3} more. See 'alternative_proposals' for details."
                    )

            if api_extension_proposals:
                feedback_parts.append(
                    f"\n{len(api_extension_proposals)} API extension(s) proposed for future improvement."
                )

            error_message = "\n".join(feedback_parts)
        else:
            status = "success"
            logger.info(f"Job generation successful (Job ID: {job_id})")
    else:
        # No job_id and no error_message means workflow ended before job_registration
        status = "failed"
        if not error_message:
            feedback_parts = ["Job generation did not complete successfully."]

            if infeasible_tasks:
                feedback_parts.append(
                    f"\nEvaluation detected {len(infeasible_tasks)} infeasible task(s):"
                )
                for task in infeasible_tasks[:3]:
                    task_name = task.get("task_name", "Unknown")
                    reason = task.get("reason", "No reason provided")
                    feedback_parts.append(f"  - {task_name}: {reason}")

            if alternative_proposals:
                feedback_parts.append(
                    f"\n{len(alternative_proposals)} alternative solution(s) proposed. "
                    "Consider revising requirements based on 'alternative_proposals'."
                )

            if validation_errors:
                feedback_parts.append(
                    f"\nValidation errors detected: {len(validation_errors)} error(s). "
                    "See 'validation_errors' for details."
                )

            if not infeasible_tasks and not validation_errors:
                feedback_parts.append(
                    "\nPlease check evaluation result and retry count. "
                    "Workflow may have exceeded maximum retry attempts."
                )

            error_message = "\n".join(feedback_parts)

    return JobGeneratorResponse(
        status=status,
        job_id=job_id,
        job_master_id=job_master_id,
        task_breakdown=task_breakdown,
        evaluation_result=evaluation_result,
        infeasible_tasks=infeasible_tasks,
        alternative_proposals=alternative_proposals,
        api_extension_proposals=api_extension_proposals,
        requirement_relaxation_suggestions=requirement_relaxation_suggestions,
        validation_errors=validation_errors,
        error_message=error_message,
    )


def _generate_requirement_relaxation_suggestions(
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    評価結果から要求緩和提案を生成（能力ベースアプローチ）

    【設計方針の変更】
    - 旧アプローチ: infeasible_tasksをパターンマッチングで分析
    - 新アプローチ: feasible_tasksと利用可能な機能を組み合わせて提案生成

    【アプローチ】
    1. 実現可能と判断されたタスク（feasible_tasks）を分析
    2. 利用可能な機能（graphai_capabilities.yaml）を特定
    3. 元の要求を分析し、実現可能な部分と不可能な部分を識別
    4. 利用可能な機能を組み合わせて、修正版の要求を生成

    Args:
        state: LangGraph final state with evaluation results

    Returns:
        List of requirement relaxation suggestions
    """
    suggestions: list[dict[str, Any]] = []
    evaluation_result = state.get("evaluation_result") or {}

    # Extract feasible tasks and infeasible tasks
    task_breakdown = state.get("task_breakdown", {})
    # Handle both list and dict formats for task_breakdown
    if isinstance(task_breakdown, list):
        feasible_tasks = task_breakdown
    elif isinstance(task_breakdown, dict):
        feasible_tasks = task_breakdown.get("tasks", [])
    else:
        feasible_tasks = []
    infeasible_tasks = evaluation_result.get("infeasible_tasks", [])

    if not infeasible_tasks or not feasible_tasks:
        return suggestions

    # Extract available capabilities from feasible tasks
    available_capabilities = _extract_available_capabilities(feasible_tasks)

    # Generate relaxation suggestions for each infeasible task
    for infeasible_task in infeasible_tasks:
        task_name = infeasible_task.get("task_name", "")
        reason = infeasible_task.get("reason", "")

        # Analyze task intent (what the task is trying to achieve)
        task_intent = _analyze_task_intent(task_name, reason)

        # Generate capability-based relaxations
        relaxed_suggestions = _generate_capability_based_relaxations(
            task_name=task_name,
            task_intent=task_intent,
            available_capabilities=available_capabilities,
            feasible_tasks=feasible_tasks,
        )

        suggestions.extend(relaxed_suggestions)

    return suggestions


def _extract_available_capabilities(
    feasible_tasks: list[dict[str, Any]],
) -> dict[str, list[str]]:
    """
    実現可能なタスクから利用可能な機能を抽出

    Args:
        feasible_tasks: List of feasible tasks from task_breakdown

    Returns:
        Dict[category, List[capability_name]]
        例: {
            "llm_based": ["geminiAgent", "anthropicAgent", "テキスト処理", "データ分析"],
            "api_integration": ["fetchAgent", "外部API呼び出し"],
            "data_transform": ["stringTemplateAgent", "mapAgent"],
            "external_services": ["Gmail API", "Google Drive API"]
        }
    """
    capabilities: dict[str, set[str]] = {
        "llm_based": set(),
        "api_integration": set(),
        "data_transform": set(),
        "external_services": set(),
    }

    for task in feasible_tasks:
        # Extract agents from task
        agents = task.get("agents", [])
        if isinstance(agents, str):
            agents = [agents]

        for agent in agents:
            # LLM-based agents
            if agent in ["geminiAgent", "anthropicAgent", "openAIAgent"]:
                capabilities["llm_based"].add(agent)
                capabilities["llm_based"].add("テキスト処理")
                capabilities["llm_based"].add("データ分析")
                capabilities["llm_based"].add("構造化出力")

            # API integration agents
            elif agent == "fetchAgent":
                capabilities["api_integration"].add("fetchAgent")
                capabilities["api_integration"].add("外部API呼び出し")

            # Data transform agents
            elif agent in [
                "stringTemplateAgent",
                "mapAgent",
                "filterAgent",
                "arrayJoinAgent",
                "copyAgent",
                "popAgent",
                "pushAgent",
                "shiftAgent",
                "sortByAgent",
            ]:
                capabilities["data_transform"].add(agent)

        # Detect external services from task description
        task_description = task.get("description", "").lower()
        task_name = task.get("name", "").lower()
        combined_text = f"{task_description} {task_name}"

        if "gmail" in combined_text or "メール" in combined_text:
            capabilities["external_services"].add("Gmail API")
        if "drive" in combined_text or "ドライブ" in combined_text:
            capabilities["external_services"].add("Google Drive API")
        if "calendar" in combined_text or "カレンダー" in combined_text:
            capabilities["external_services"].add("Google Calendar API")

    # Convert sets to lists
    return {k: list(v) for k, v in capabilities.items()}


def _analyze_task_intent(task_name: str, reason: str) -> dict[str, Any]:
    """
    タスクの意図を分析

    Args:
        task_name: Task name
        reason: Reason why task is infeasible

    Returns:
        {
            "primary_goal": str,  # 主要な目標（例: "データ収集", "通知", "データ処理"）
            "data_source": str,   # データソース（例: "企業財務データ", "Gmail", "PDF"）
            "output_format": str, # 出力形式（例: "メール", "JSON", "レポート"）
            "automation_level": str  # 自動化レベル（例: "全自動", "半自動", "手動"）
        }
    """
    intent = {
        "primary_goal": "不明",
        "data_source": "不明",
        "output_format": "不明",
        "automation_level": "全自動",
    }

    task_lower = task_name.lower()
    reason_lower = reason.lower()

    # Identify primary goal
    if any(keyword in task_lower for keyword in ["収集", "取得", "fetch", "get"]):
        intent["primary_goal"] = "データ収集"
    elif any(keyword in task_lower for keyword in ["分析", "analyze", "まとめ"]):
        intent["primary_goal"] = "データ分析"
    elif any(keyword in task_lower for keyword in ["送信", "通知", "send", "notify"]):
        intent["primary_goal"] = "通知・送信"
    elif any(
        keyword in task_lower for keyword in ["処理", "変換", "process", "transform"]
    ):
        intent["primary_goal"] = "データ処理"

    # Identify data source
    if "gmail" in task_lower or "メール" in task_lower:
        intent["data_source"] = "Gmail"
    elif "財務" in task_lower or "売上" in task_lower or "financial" in task_lower:
        intent["data_source"] = "企業財務データ"
    elif "pdf" in task_lower:
        intent["data_source"] = "PDF"
    elif "web" in task_lower or "url" in task_lower:
        intent["data_source"] = "Webページ"

    # Identify output format
    if "メール" in task_lower or "mail" in task_lower:
        intent["output_format"] = "メール"
    elif "json" in task_lower:
        intent["output_format"] = "JSON"
    elif "レポート" in task_lower or "report" in task_lower:
        intent["output_format"] = "レポート"
    elif "slack" in task_lower:
        intent["output_format"] = "Slack通知"
    elif "discord" in task_lower:
        intent["output_format"] = "Discord通知"

    # Identify automation level from reason
    if "api" in reason_lower or "認証" in reason_lower or "権限" in reason_lower:
        intent["automation_level"] = "半自動（API key必要）"
    elif "手動" in reason_lower or "manual" in reason_lower:
        intent["automation_level"] = "手動"

    return intent


def _generate_capability_based_relaxations(
    task_name: str,
    task_intent: dict[str, Any],
    available_capabilities: dict[str, list[str]],
    feasible_tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    利用可能な機能を組み合わせて緩和提案を生成

    【戦略】
    1. 主要目標を達成する代替手段を提案（例: メール送信 → メール下書き作成）
    2. データソースを利用可能なもので代替（例: 有料API → 無料API）
    3. 自動化レベルを調整（例: 全自動 → 半自動 → 手動確認）
    4. 出力形式を利用可能なもので代替（例: Slack通知 → メール通知）

    Args:
        task_name: Task name
        task_intent: Task intent analysis result
        available_capabilities: Available capabilities extracted from feasible tasks
        feasible_tasks: List of feasible tasks

    Returns:
        List of requirement relaxation suggestions
    """
    suggestions = []

    primary_goal = task_intent["primary_goal"]
    data_source = task_intent["data_source"]
    output_format = task_intent["output_format"]

    # Strategy 1: Reduce automation level (fully automatic → semi-automatic)
    if output_format == "メール" and "Gmail API" in available_capabilities.get(
        "external_services", []
    ):
        if available_capabilities.get("llm_based"):
            # LLM generates email body + Gmail API creates draft
            llm_agent = available_capabilities["llm_based"][0]
            suggestions.append(
                {
                    "original_requirement": task_name,
                    "relaxed_requirement": task_name.replace(
                        "送信", "下書き作成"
                    ).replace("メール送信", "メール下書き作成"),
                    "relaxation_type": "automation_level_reduction",
                    "feasibility_after_relaxation": "high",
                    "what_is_sacrificed": "自動送信機能（ユーザーが手動で送信ボタンを押す必要）",
                    "what_is_preserved": "メール本文の自動生成、データ分析、Gmail下書きの自動作成",
                    "recommendation_level": "strongly_recommended",
                    "implementation_note": f"{llm_agent}でメール本文生成 + Gmail API Draft作成",
                    "available_capabilities_used": [
                        llm_agent,
                        "Gmail API (Draft作成)",
                        "fetchAgent",
                    ],
                    "implementation_steps": [
                        f"1. {llm_agent}でメール本文を生成",
                        "2. stringTemplateAgentでメールフォーマットを整形",
                        "3. fetchAgent + Gmail API でDraft作成",
                        "4. ユーザーがGmail UIで確認・送信",
                    ],
                }
            )

    # Strategy 2: Substitute data source
    if data_source == "企業財務データ" and available_capabilities.get("llm_based"):
        # Use LLM-based analysis instead of paid API
        llm_agent = available_capabilities["llm_based"][0]
        suggestions.append(
            {
                "original_requirement": task_name,
                "relaxed_requirement": task_name.replace(
                    "過去5年", "過去2-3年"
                ).replace("詳細な", "サマリーレベルの"),
                "relaxation_type": "scope_reduction",
                "feasibility_after_relaxation": "medium",
                "what_is_sacrificed": "5年分の詳細データ、リアルタイム性、網羅性",
                "what_is_preserved": "最新2-3年のトレンド分析、ビジネスモデル変化の概要",
                "recommendation_level": "recommended",
                "implementation_note": f"{llm_agent}で公開情報をベースに分析",
                "available_capabilities_used": [
                    llm_agent,
                    "fetchAgent（企業公開情報取得）",
                ],
                "implementation_steps": [
                    "1. fetchAgentで企業の公開情報（IRページ、ニュース）を取得",
                    f"2. {llm_agent}で財務情報を抽出・分析",
                    "3. stringTemplateAgentでレポート形式に整形",
                    "4. 最新2-3年分のトレンドをサマリー化",
                ],
            }
        )

    # Strategy 3: Replace output format (external service → internal functionality)
    if output_format in ["Slack通知", "Discord通知"] or any(
        service in task_name for service in ["Slack", "Discord"]
    ):
        if available_capabilities.get(
            "llm_based"
        ) and "Gmail API" in available_capabilities.get("external_services", []):
            # Replace Slack/Discord notification with email notification
            llm_agent = available_capabilities["llm_based"][0]
            suggestions.append(
                {
                    "original_requirement": task_name,
                    "relaxed_requirement": task_name.replace("Slack", "メール").replace(
                        "Discord", "メール"
                    ),
                    "relaxation_type": "output_format_change",
                    "feasibility_after_relaxation": "high",
                    "what_is_sacrificed": "Slack/Discordへのリアルタイム通知",
                    "what_is_preserved": "通知内容、自動生成機能、データ分析結果",
                    "recommendation_level": "recommended",
                    "implementation_note": "メール通知で代替（Slack APIキー不要）",
                    "available_capabilities_used": [
                        llm_agent,
                        "Gmail API (Draft作成)",
                        "fetchAgent",
                    ],
                    "implementation_steps": [
                        f"1. {llm_agent}で通知内容を生成",
                        "2. Gmail API Draft作成で通知メールを準備",
                        "3. ユーザーが確認・送信",
                    ],
                }
            )

    # Strategy 4: Combine multiple available capabilities (phased implementation)
    if primary_goal == "データ分析" and available_capabilities.get("llm_based"):
        # Propose phased implementation for complex analysis tasks
        llm_agent = available_capabilities["llm_based"][0]
        suggestions.append(
            {
                "original_requirement": task_name,
                "relaxed_requirement": f"{task_name}（段階的実装: Phase 1は基本分析のみ）",
                "relaxation_type": "phased_implementation",
                "feasibility_after_relaxation": "high",
                "what_is_sacrificed": "Phase 1では詳細分析・高度な洞察は含まれない",
                "what_is_preserved": "基本的なデータ分析、トレンド把握、主要指標の抽出",
                "recommendation_level": "consider",
                "implementation_note": "段階的に機能を拡張（Phase 1→2→3）",
                "available_capabilities_used": [
                    llm_agent,
                    "fetchAgent",
                    "stringTemplateAgent",
                ],
                "implementation_steps": [
                    "【Phase 1: 基本分析】（即座に実装可能）",
                    f"  - {llm_agent}でサマリーレベル分析",
                    "  - 主要指標の抽出と可視化",
                    "  - 実装時間: 1-2時間、品質: 60%",
                    "",
                    "【Phase 2: 詳細分析】（API拡張後）",
                    "  - 財務データAPI統合",
                    "  - 詳細トレンド分析",
                    "  - 実装時間: 2-4週間、品質: 85%",
                    "",
                    "【Phase 3: 高度な洞察】（将来的に）",
                    "  - 予測分析・競合比較",
                    "  - 実装時間: 2-3ヶ月、品質: 100%",
                ],
            }
        )

    return suggestions
