"""API endpoints for Job/Task Auto-Generation."""

import json
import logging
import os
from typing import Any

import anthropic
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from aiagent.langgraph.jobTaskGeneratorAgents import (
    create_initial_state,
    create_job_task_generator_agent,
)
from app.schemas.job_generator import JobGeneratorRequest, JobGeneratorResponse
from core.secrets import secrets_manager

logger = logging.getLogger(__name__)


# ===== Phase 11: LLM-based Requirement Relaxation Suggestion =====
class RequirementRelaxationSuggestion(BaseModel):
    """要求緩和提案のスキーマ (Phase 11)"""

    original_requirement: str = Field(..., description="元の要求内容", min_length=1)
    relaxed_requirement: str = Field(..., description="緩和後の要求内容", min_length=1)
    relaxation_type: str = Field(
        ...,
        description="緩和タイプ",
        pattern="^(automation_level_reduction|scope_reduction|intermediate_step_skip|output_format_change|data_source_substitution|phased_implementation|api_auth_preconfiguration|file_operation_simplification|web_operation_to_llm)$",
    )
    feasibility_after_relaxation: str = Field(
        ...,
        description="緩和後の実現可能性",
        pattern="^(high|medium|low|medium-high)$",
    )
    what_is_sacrificed: str = Field(..., description="犠牲になるもの", min_length=1)
    what_is_preserved: str = Field(..., description="維持されるもの", min_length=1)
    recommendation_level: str = Field(
        ...,
        description="推奨レベル",
        pattern="^(strongly_recommended|recommended|consider)$",
    )
    implementation_note: str = Field(..., description="実装時の注意点", min_length=1)
    available_capabilities_used: list[str] = Field(
        default_factory=list, description="使用する機能リスト"
    )
    implementation_steps: list[str] = Field(
        default_factory=list, description="実装ステップ"
    )

    @field_validator("implementation_steps")
    @classmethod
    def validate_implementation_steps(cls, v: list[str]) -> list[str]:
        """実装ステップが最低3つあることを検証"""
        if len(v) < 3:
            raise ValueError("implementation_steps must contain at least 3 steps")
        return v


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
    logger.info("[DEBUG] _generate_requirement_relaxation_suggestions() called")
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

    logger.info(
        f"[DEBUG] infeasible_tasks count: {len(infeasible_tasks)}, "
        f"feasible_tasks count: {len(feasible_tasks)}"
    )

    # Phase 11: LLM-based approach doesn't strictly require feasible_tasks
    # If there are infeasible tasks, generate suggestions even without feasible_tasks
    if not infeasible_tasks:
        logger.info("[DEBUG] No infeasible_tasks found, returning empty suggestions")
        return suggestions

    logger.info(f"[DEBUG] Processing {len(infeasible_tasks)} infeasible tasks")

    # Extract available capabilities from feasible tasks
    available_capabilities = _extract_available_capabilities(feasible_tasks)
    logger.info(f"[DEBUG] Extracted capabilities: {available_capabilities}")

    # Generate relaxation suggestions for each infeasible task
    for i, infeasible_task in enumerate(infeasible_tasks, 1):
        task_name = infeasible_task.get("task_name", "")
        reason = infeasible_task.get("reason", "")

        logger.info(
            f"[DEBUG] Processing infeasible task {i}/{len(infeasible_tasks)}: "
            f"'{task_name}'"
        )

        # Analyze task intent (what the task is trying to achieve)
        task_intent = _analyze_task_intent(task_name, reason)
        logger.info(f"[DEBUG] Task intent: {task_intent}")

        # Phase 11: Generate LLM-based relaxations
        logger.info(
            f"[DEBUG] Calling _generate_llm_based_relaxation_suggestions() "
            f"for task: '{task_name}'"
        )
        relaxed_suggestions = _generate_llm_based_relaxation_suggestions(
            task_name=task_name,
            reason=reason,
            task_intent=task_intent,
            available_capabilities=available_capabilities,
            feasible_tasks=feasible_tasks,
        )

        logger.info(f"[DEBUG] Received {len(relaxed_suggestions)} suggestions from LLM")
        suggestions.extend(relaxed_suggestions)

    logger.info(f"[DEBUG] Total suggestions generated: {len(suggestions)}")
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

    # Phase 10-D Fix: Add default capabilities from graphai_capabilities.yaml
    # Since task_breakdown doesn't include "agents" field, we provide default capabilities
    # that are always available in the system
    capabilities["llm_based"].add(
        "geminiAgent"
    )  # Phase 10-A: Default recommended agent
    capabilities["llm_based"].add("anthropicAgent")
    capabilities["llm_based"].add("openAIAgent")
    capabilities["llm_based"].add("テキスト処理")
    capabilities["llm_based"].add("データ分析")
    capabilities["llm_based"].add("構造化出力")
    capabilities["api_integration"].add("fetchAgent")
    capabilities["api_integration"].add("外部API呼び出し")
    capabilities["data_transform"].add("stringTemplateAgent")
    capabilities["data_transform"].add("mapAgent")
    capabilities["data_transform"].add("arrayJoinAgent")

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


# ===== Phase 11: LLM-based Requirement Relaxation Suggestion =====
def _call_anthropic_for_relaxation_suggestions(
    task_name: str,
    reason: str,
    task_intent: dict[str, Any],
    available_capabilities: dict[str, list[str]],
    feasible_tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Claude Haiku 4.5を使用して要求緩和提案を動的に生成（Phase 11）

    Args:
        task_name: 実現不可能なタスク名
        reason: 実現不可能な理由
        task_intent: タスク意図分析結果
        available_capabilities: 利用可能な機能一覧
        feasible_tasks: 実現可能なタスク一覧

    Returns:
        LLMが生成した要求緩和提案のリスト
    """
    # Get Anthropic API key from secrets_manager
    try:
        api_key = secrets_manager.get_secret("ANTHROPIC_API_KEY", project=None)
    except Exception as e:
        logger.warning(
            f"Failed to get ANTHROPIC_API_KEY from secrets_manager: {e}. "
            "Requirement relaxation suggestions will not be generated."
        )
        return []

    # Construct prompt for Claude Haiku 4.5
    prompt = f"""あなたは、実現不可能なタスクに対して要求緩和提案を生成する専門家です。

# 実現不可能なタスク
タスク名: {task_name}
実現不可能な理由: {reason}

# タスク意図分析
{json.dumps(task_intent, ensure_ascii=False, indent=2)}

# 利用可能な機能
{json.dumps(available_capabilities, ensure_ascii=False, indent=2)}

# 実現可能なタスク例（参考）
{json.dumps(feasible_tasks[:3] if len(feasible_tasks) > 3 else feasible_tasks, ensure_ascii=False, indent=2)}

---

# あなたのタスク
上記の情報を基に、**3-6件の具体的な要求緩和提案**を生成してください。

## 提案生成のガイドライン
1. **利用可能な機能を最大限活用**: available_capabilitiesに含まれる機能を組み合わせて提案
2. **段階的な緩和**: 自動化レベル、スコープ、出力形式などを段階的に緩和
3. **実現可能性を重視**: 緩和後は必ず実現可能であること（feasibility_after_relaxation: high or medium-high）
4. **ユーザー視点**: what_is_sacrificed（犠牲）とwhat_is_preserved（維持）を明確に
5. **実装可能性**: implementation_stepsは具体的で実行可能なステップ（最低3ステップ）

## 緩和タイプ（relaxation_type）の候補
- automation_level_reduction: 自動化レベルを下げる（例: 自動送信 → 下書き作成）
- scope_reduction: スコープを縮小（例: 5年分 → 2-3年分）
- intermediate_step_skip: 中間ステップをスキップ（例: 詳細分析 → サマリー分析）
- output_format_change: 出力形式を変更（例: Slack → Email）
- data_source_substitution: データソースを代替（例: 有料API → LLM分析）
- phased_implementation: 段階的実装（例: Phase 1: 基本機能のみ）
- api_auth_preconfiguration: API認証の事前設定を要求（例: Gmail API事前設定）
- file_operation_simplification: ファイル操作の簡略化（例: ローカルのみ対応）
- web_operation_to_llm: Web操作をLLMベースに変更（例: スクレイピング → LLM要約）

## 必須出力形式（JSON配列、**日本語で記述**）
```json
[
  {{
    "original_requirement": "元のタスク名（日本語）",
    "relaxed_requirement": "緩和後のタスク名（日本語）",
    "relaxation_type": "緩和タイプ（上記から選択）",
    "feasibility_after_relaxation": "high",
    "what_is_sacrificed": "犠牲になるもの（日本語で詳細に）",
    "what_is_preserved": "維持されるもの（日本語で詳細に）",
    "recommendation_level": "strongly_recommended",
    "implementation_note": "実装時の注意点（日本語）",
    "available_capabilities_used": ["geminiAgent", "fetchAgent", "Gmail API"],
    "implementation_steps": [
      "1. 具体的なステップ1（日本語）",
      "2. 具体的なステップ2（日本語）",
      "3. 具体的なステップ3（日本語）"
    ]
  }}
]
```

**重要**: JSON配列のみを出力してください。説明文は不要です。"""

    # Call Claude Haiku 4.5 API
    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=2048,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse JSON response
        # Anthropic API v2 returns TextBlock objects in content array
        response_text = ""
        for content_block in response.content:
            if hasattr(content_block, "text"):
                response_text += content_block.text
        response_text = response_text.strip()

        # Remove markdown code block if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        suggestions = json.loads(response_text)

        # Validate each suggestion with Pydantic
        validated_suggestions = []
        for suggestion in suggestions:
            try:
                validated = RequirementRelaxationSuggestion(**suggestion)
                validated_suggestions.append(validated.model_dump())
            except Exception as validation_error:
                logger.warning(
                    f"Failed to validate suggestion: {validation_error}. "
                    f"Suggestion: {suggestion}"
                )
                continue

        logger.info(
            f"Generated {len(validated_suggestions)} validated relaxation suggestions "
            f"for task '{task_name}' using Claude Haiku 4.5"
        )
        return validated_suggestions

    except json.JSONDecodeError as e:
        logger.error(
            f"Failed to parse JSON response from Claude API: {e}. "
            f"Response text: {response_text[:200]}"
        )
        return []
    except Exception as e:
        logger.error(
            f"Failed to call Claude API for relaxation suggestions: {e}",
            exc_info=True,
        )
        return []


def _generate_llm_based_relaxation_suggestions(
    task_name: str,
    reason: str,
    task_intent: dict[str, Any],
    available_capabilities: dict[str, list[str]],
    feasible_tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    LLMベースの要求緩和提案生成（Phase 11メイン関数）

    Args:
        task_name: 実現不可能なタスク名
        reason: 実現不可能な理由
        task_intent: タスク意図分析結果
        available_capabilities: 利用可能な機能一覧
        feasible_tasks: 実現可能なタスク一覧

    Returns:
        LLMが生成した要求緩和提案のリスト
    """
    logger.info(f"Generating LLM-based relaxation suggestions for task: '{task_name}'")

    suggestions = _call_anthropic_for_relaxation_suggestions(
        task_name=task_name,
        reason=reason,
        task_intent=task_intent,
        available_capabilities=available_capabilities,
        feasible_tasks=feasible_tasks,
    )

    if not suggestions:
        logger.warning(
            f"No relaxation suggestions generated for task '{task_name}'. "
            "Returning empty list."
        )
        return []

    logger.info(
        f"Successfully generated {len(suggestions)} relaxation suggestions "
        f"for task '{task_name}'"
    )
    return suggestions
