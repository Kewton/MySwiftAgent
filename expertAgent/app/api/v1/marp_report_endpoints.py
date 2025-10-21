"""Marp Report Generation API endpoints."""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from jinja2 import Environment, FileSystemLoader  # type: ignore

from app.schemas.marp_report import MarpReportRequest, MarpReportResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize Jinja2 environment
TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates" / "marp"
jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)

# Relaxation type Japanese labels mapping
RELAXATION_TYPE_LABELS_JA = {
    "data_source_substitution": "データソース代替案",
    "intermediate_step_skip": "中間処理の簡略化",
    "output_format_change": "出力形式の変更",
    "scope_reduction": "対象範囲の縮小",
    "automation_level_reduction": "自動化レベルの調整",
    "phased_implementation": "段階的実装",
    "requirement_relaxation": "要求仕様の緩和",
}


def _get_relaxation_type_label(relaxation_type: str) -> str:
    """Get Japanese label for relaxation type.

    Args:
        relaxation_type: Relaxation type key

    Returns:
        Japanese label (or original key if not found)
    """
    return RELAXATION_TYPE_LABELS_JA.get(relaxation_type, relaxation_type)


def _group_suggestions_by_task(
    suggestions: list[dict[str, Any]], tasks: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    """Group requirement relaxation suggestions by task.

    Args:
        suggestions: List of requirement relaxation suggestions
        tasks: List of tasks from task_breakdown

    Returns:
        Dictionary mapping task names to matching suggestions
    """
    task_suggestions: dict[str, list[dict[str, Any]]] = {}

    for task in tasks:
        task_name = task.get("task_name", "")
        # Match suggestions where task_name appears in original_requirement
        matching_suggestions = [
            s
            for s in suggestions
            if task_name and task_name in s.get("original_requirement", "")
        ]
        task_suggestions[task_name] = matching_suggestions

    return task_suggestions


def _load_job_result(request: MarpReportRequest) -> dict[str, Any]:
    """Load job result from request data or file path.

    Args:
        request: Marp report request

    Returns:
        Job Generator result dictionary

    Raises:
        HTTPException: If file not found or invalid JSON
    """
    if request.job_result is not None:
        return request.job_result

    # Load from file
    file_path = Path(request.json_file_path)  # type: ignore
    if not file_path.exists():
        msg = f"JSON file not found: {file_path}"
        raise HTTPException(status_code=404, detail=msg)

    try:
        with file_path.open("r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
            return data
    except json.JSONDecodeError as e:
        msg = f"Invalid JSON file: {e}"
        logger.error(msg)
        raise HTTPException(status_code=400, detail=msg) from e


def _extract_template_data(job_result: dict[str, Any]) -> dict[str, Any]:
    """Extract template data from job result.

    Args:
        job_result: Job Generator result dictionary

    Returns:
        Dictionary with template variables
    """
    suggestions = job_result.get("requirement_relaxation_suggestions", [])
    infeasible_tasks = job_result.get("infeasible_tasks", [])

    # Extract tasks from task_breakdown (handle both dict and list formats)
    task_breakdown = job_result.get("task_breakdown", [])
    if isinstance(task_breakdown, dict):
        tasks = task_breakdown.get("tasks", [])
    elif isinstance(task_breakdown, list):
        tasks = task_breakdown
    else:
        tasks = []

    # Add Japanese labels to suggestions
    for suggestion in suggestions:
        original_type = suggestion.get("relaxation_type", "")
        suggestion["relaxation_type_ja"] = _get_relaxation_type_label(original_type)

    # Group suggestions by task
    task_suggestions_map = _group_suggestions_by_task(suggestions, tasks)

    # Calculate execution time if available (from error_message if present)
    execution_time = None
    # You can add logic here to parse execution time from state if needed

    # Extract user requirement from error_message (if present)
    error_message = job_result.get("error_message") or ""
    if error_message:
        user_requirement = (
            error_message.split("\n")[0]
            .replace("Job generation did not complete successfully.", "")
            .strip()
        )
    else:
        # Default message for success cases
        user_requirement = "Job/Task 生成が正常に完了しました"

    return {
        "theme": "default",  # Will be overridden by request.theme
        "user_requirement": user_requirement,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "status": job_result.get("status", "unknown"),
        "infeasible_tasks_count": len(infeasible_tasks),
        "suggestions_count": len(suggestions),
        "execution_time": execution_time,
        "suggestions": suggestions,
        "job_id": job_result.get("job_id"),
        "include_implementation_steps": True,  # Will be overridden by request
        "tasks": tasks,  # Task list for display
        "tasks_count": len(tasks),  # Task count
        "task_suggestions_map": task_suggestions_map,  # Map tasks to suggestions
    }


def _count_slides(
    suggestions_count: int,
    include_implementation_steps: bool,  # noqa: ARG001
    tasks_count: int = 0,
) -> int:
    """Calculate total number of slides.

    Args:
        suggestions_count: Number of requirement relaxation suggestions
        include_implementation_steps: Whether implementation steps are included
        tasks_count: Number of tasks

    Returns:
        Total number of slides
    """
    import math

    # Slide 1: Title
    # Slide 2: Summary
    # Slides 3+: Task list (5 tasks per slide)
    # Slides N+: Suggestions (3 slides per suggestion)
    # Last slide: Conclusion

    task_slides = math.ceil(tasks_count / 5) if tasks_count > 0 else 0
    suggestion_slides = suggestions_count * 3

    return 3 + task_slides + suggestion_slides


@router.post("/marp-report", response_model=MarpReportResponse)
async def generate_marp_report(request: MarpReportRequest) -> MarpReportResponse:
    """Generate Marp presentation from Job Generator result.

    Args:
        request: Marp report generation request

    Returns:
        Generated Marp Markdown and metadata

    Raises:
        HTTPException: If file not found, invalid JSON, or template rendering fails
    """
    start_time = time.time()

    try:
        # Load job result
        job_result = _load_job_result(request)

        # Extract template data
        template_data = _extract_template_data(job_result)

        # Override with request parameters
        template_data["theme"] = request.theme
        template_data["include_implementation_steps"] = (
            request.include_implementation_steps
        )

        # Render template
        template = jinja_env.get_template("job_report.md.j2")
        marp_markdown = template.render(**template_data)

        # Calculate metrics
        suggestions_count = template_data["suggestions_count"]
        tasks_count = template_data["tasks_count"]
        slide_count = _count_slides(
            suggestions_count,
            request.include_implementation_steps,
            tasks_count,
        )
        generation_time_ms = (time.time() - start_time) * 1000

        return MarpReportResponse(
            marp_markdown=marp_markdown,
            slide_count=slide_count,
            suggestions_count=suggestions_count,
            generation_time_ms=generation_time_ms,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to generate Marp report")
        msg = f"Internal server error: {e}"
        raise HTTPException(status_code=500, detail=msg) from e
