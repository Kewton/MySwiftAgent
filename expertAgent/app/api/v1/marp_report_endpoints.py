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

    # Calculate execution time if available (from error_message if present)
    execution_time = None
    # You can add logic here to parse execution time from state if needed

    return {
        "theme": "default",  # Will be overridden by request.theme
        "user_requirement": job_result.get("error_message", "")
        .split("\n")[0]
        .replace("Job generation did not complete successfully.", "")
        .strip(),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "status": job_result.get("status", "unknown"),
        "infeasible_tasks_count": len(infeasible_tasks),
        "suggestions_count": len(suggestions),
        "execution_time": execution_time,
        "suggestions": suggestions,
        "job_id": job_result.get("job_id"),
        "include_implementation_steps": True,  # Will be overridden by request
    }


def _count_slides(
    suggestions_count: int,
    include_implementation_steps: bool,  # noqa: ARG001
) -> int:
    """Calculate total number of slides.

    Args:
        suggestions_count: Number of requirement relaxation suggestions
        include_implementation_steps: Whether implementation steps are included

    Returns:
        Total number of slides
    """
    # Slide 1: Title
    # Slide 2: Summary
    # Slides 3+: Suggestions (3 slides per suggestion)
    # Last slide: Conclusion
    return 3 + (suggestions_count * 3)


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
        slide_count = _count_slides(
            suggestions_count, request.include_implementation_steps
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
