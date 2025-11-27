"""AB Test API endpoints.

Issue #178: AB Test Infrastructure Implementation.
Provides REST API endpoints for managing A/B tests, variant assignment,
and statistical analysis.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.exceptions import ServiceError
from app.schemas.ab_test import (
    ABTestAssignmentRequest,
    ABTestAssignmentResponse,
    ABTestConfigCreate,
    ABTestConfigResponse,
    ABTestListResponse,
    ABTestReport,
    ABTestReportRequest,
    ABTestStatus,
    ABTestStatusResponse,
    ABTestStatusUpdate,
)
from app.services.ab_test_service import (
    ABTestNotFoundError,
    ABTestService,
    ABTestServiceError,
)
from core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ab-tests"], prefix="/ab-tests")

# Singleton service instance
_ab_test_service: ABTestService | None = None


def get_ab_test_service() -> ABTestService:
    """Get or create the shared ABTestService instance."""
    global _ab_test_service
    if _ab_test_service is None:
        _ab_test_service = ABTestService(
            valkey_host=settings.VALKEY_HOST,
            valkey_port=settings.VALKEY_PORT,
            valkey_db=settings.VALKEY_DB,
            use_valkey=settings.VALKEY_ENABLED,
        )
    return _ab_test_service


# ========================================
# Test Management Endpoints
# ========================================


@router.post(
    "",
    response_model=ABTestConfigResponse,
    status_code=201,
    summary="Create AB test",
    description="Create a new A/B test configuration with specified variants.",
)
async def create_ab_test(
    config: ABTestConfigCreate,
    service: ABTestService = Depends(get_ab_test_service),
) -> ABTestConfigResponse:
    """Create a new AB test.

    Args:
        config: Test configuration with variants.
        service: ABTestService dependency.

    Returns:
        ABTestConfigResponse: Created test configuration.

    Raises:
        HTTPException: On validation or service error.
    """
    try:
        test = await service.create_test(config)
        return ABTestConfigResponse(test=test, message="AB test created successfully")

    except ValueError as e:
        logger.error(f"Validation error creating AB test: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ServiceError as e:
        logger.exception("Service error creating AB test")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception:
        logger.exception("Unexpected error creating AB test")
        raise HTTPException(status_code=500, detail="Internal server error") from None


@router.get(
    "",
    response_model=ABTestListResponse,
    summary="List AB tests",
    description="Get a list of all AB tests with optional status filtering and pagination.",
)
async def list_ab_tests(
    status: ABTestStatus | None = Query(None, description="Filter by test status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum tests to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    service: ABTestService = Depends(get_ab_test_service),
) -> ABTestListResponse:
    """List AB tests.

    Args:
        status: Optional status filter.
        limit: Maximum number of tests to return.
        offset: Pagination offset.
        service: ABTestService dependency.

    Returns:
        ABTestListResponse: List of tests and total count.
    """
    try:
        tests, total = await service.list_tests(
            status=status, limit=limit, offset=offset
        )
        return ABTestListResponse(tests=tests, total=total)

    except ServiceError as e:
        logger.exception("Service error listing AB tests")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception:
        logger.exception("Unexpected error listing AB tests")
        raise HTTPException(status_code=500, detail="Internal server error") from None


@router.get(
    "/{test_id}",
    response_model=ABTestConfigResponse,
    summary="Get AB test",
    description="Get a specific AB test by ID.",
)
async def get_ab_test(
    test_id: str,
    service: ABTestService = Depends(get_ab_test_service),
) -> ABTestConfigResponse:
    """Get an AB test by ID.

    Args:
        test_id: Test ID.
        service: ABTestService dependency.

    Returns:
        ABTestConfigResponse: Test configuration.

    Raises:
        HTTPException: If test not found.
    """
    try:
        test = await service.get_test(test_id)
        return ABTestConfigResponse(test=test)

    except ABTestNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ServiceError as e:
        logger.exception(f"Service error getting AB test {test_id}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception:
        logger.exception(f"Unexpected error getting AB test {test_id}")
        raise HTTPException(status_code=500, detail="Internal server error") from None


@router.put(
    "/{test_id}/status",
    response_model=ABTestStatusResponse,
    summary="Update AB test status",
    description="Update the status of an AB test (draft, running, paused, completed).",
)
async def update_ab_test_status(
    test_id: str,
    update: ABTestStatusUpdate,
    service: ABTestService = Depends(get_ab_test_service),
) -> ABTestStatusResponse:
    """Update AB test status.

    Args:
        test_id: Test ID.
        update: Status update request.
        service: ABTestService dependency.

    Returns:
        ABTestStatusResponse: Status change details.

    Raises:
        HTTPException: If test not found or invalid status transition.
    """
    try:
        response = await service.update_test_status(test_id, update.status)
        return response

    except ABTestNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ServiceError as e:
        logger.exception(f"Service error updating AB test status {test_id}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception:
        logger.exception(f"Unexpected error updating AB test status {test_id}")
        raise HTTPException(status_code=500, detail="Internal server error") from None


@router.delete(
    "/{test_id}",
    status_code=204,
    summary="Delete AB test",
    description="Delete an AB test and all associated data.",
)
async def delete_ab_test(
    test_id: str,
    service: ABTestService = Depends(get_ab_test_service),
) -> None:
    """Delete an AB test.

    Args:
        test_id: Test ID.
        service: ABTestService dependency.

    Raises:
        HTTPException: If test not found.
    """
    try:
        await service.delete_test(test_id)

    except ABTestNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ServiceError as e:
        logger.exception(f"Service error deleting AB test {test_id}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception:
        logger.exception(f"Unexpected error deleting AB test {test_id}")
        raise HTTPException(status_code=500, detail="Internal server error") from None


# ========================================
# Variant Assignment Endpoints
# ========================================


@router.post(
    "/{test_id}/assignment",
    response_model=ABTestAssignmentResponse,
    summary="Get or create variant assignment",
    description="""
Get the assigned variant for a session, or create a new assignment if none exists.
Variant selection uses weighted random choice based on configured weights.
Assignments are persisted in Valkey with 30-day TTL.
""",
)
async def get_or_create_assignment(
    test_id: str,
    request: ABTestAssignmentRequest,
    service: ABTestService = Depends(get_ab_test_service),
) -> ABTestAssignmentResponse:
    """Get or create variant assignment.

    Args:
        test_id: Test ID.
        request: Assignment request with session ID.
        service: ABTestService dependency.

    Returns:
        ABTestAssignmentResponse: Assignment details.

    Raises:
        HTTPException: If test not found.
    """
    try:
        assignment, is_new = await service.assign_variant(test_id, request.session_id)
        return ABTestAssignmentResponse(assignment=assignment, is_new=is_new)

    except ABTestNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ServiceError as e:
        logger.exception(f"Service error assigning variant for test {test_id}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception:
        logger.exception(f"Unexpected error assigning variant for test {test_id}")
        raise HTTPException(status_code=500, detail="Internal server error") from None


@router.get(
    "/{test_id}/assignment/{session_id}",
    response_model=ABTestAssignmentResponse,
    summary="Get existing assignment",
    description="Get the existing variant assignment for a session without creating one.",
)
async def get_assignment(
    test_id: str,
    session_id: str,
    service: ABTestService = Depends(get_ab_test_service),
) -> ABTestAssignmentResponse:
    """Get existing assignment.

    Args:
        test_id: Test ID.
        session_id: Session ID.
        service: ABTestService dependency.

    Returns:
        ABTestAssignmentResponse: Assignment if exists.

    Raises:
        HTTPException: If assignment not found.
    """
    try:
        assignment = await service.get_assignment(test_id, session_id)

        if assignment is None:
            raise HTTPException(
                status_code=404,
                detail=f"No assignment found for session {session_id} in test {test_id}",
            )

        return ABTestAssignmentResponse(assignment=assignment, is_new=False)

    except HTTPException:
        raise
    except ServiceError as e:
        logger.exception(f"Service error getting assignment for test {test_id}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception:
        logger.exception(f"Unexpected error getting assignment for test {test_id}")
        raise HTTPException(status_code=500, detail="Internal server error") from None


# ========================================
# Report Generation Endpoints
# ========================================


@router.post(
    "/{test_id}/report",
    response_model=ABTestReport,
    summary="Generate AB test report",
    description="""
Generate a comprehensive statistical report for an AB test.

The report includes:
- Per-variant metrics (sample size, mean, std, 95% CI)
- T-test results (Welch's t-test for unequal variances)
- Effect size (Cohen's d with interpretation)
- Winner determination (if significant)
- Recommendations based on analysis
- Warning messages (e.g., insufficient sample size)

Statistical requirements:
- Minimum 2 samples per variant for analysis
- Recommended minimum 30 samples per variant for reliable results
""",
)
async def generate_report(
    test_id: str,
    request: ABTestReportRequest = ABTestReportRequest(),
    service: ABTestService = Depends(get_ab_test_service),
) -> ABTestReport:
    """Generate AB test report.

    Args:
        test_id: Test ID.
        request: Report generation parameters.
        service: ABTestService dependency.

    Returns:
        ABTestReport: Comprehensive statistical report.

    Raises:
        HTTPException: If test not found.
    """
    try:
        report = await service.generate_report(test_id, request)
        return report

    except ABTestNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ABTestServiceError as e:
        logger.error(f"Statistical analysis error for test {test_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ServiceError as e:
        logger.exception(f"Service error generating report for test {test_id}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception:
        logger.exception(f"Unexpected error generating report for test {test_id}")
        raise HTTPException(status_code=500, detail="Internal server error") from None


# ========================================
# Metrics Collection Endpoint
# ========================================


@router.post(
    "/{test_id}/metrics",
    status_code=201,
    summary="Collect metric data point",
    description="Record a metric data point for a session in the AB test.",
)
async def collect_metric(
    test_id: str,
    session_id: str = Query(..., description="Session ID"),
    value: float = Query(..., description="Metric value"),
    metric_name: str = Query("quality_score", description="Metric name"),
    service: ABTestService = Depends(get_ab_test_service),
) -> dict:
    """Collect a metric data point.

    Args:
        test_id: Test ID.
        session_id: Session ID.
        value: Metric value.
        metric_name: Metric name.
        service: ABTestService dependency.

    Returns:
        Confirmation dict.

    Raises:
        HTTPException: If session not assigned to test.
    """
    try:
        data_point = await service.collect_metric(
            test_id, session_id, value, metric_name
        )
        return {
            "status": "success",
            "message": "Metric recorded",
            "data_point": {
                "session_id": data_point.session_id,
                "variant_name": data_point.variant_name,
                "metric_name": data_point.metric_name,
                "value": data_point.value,
            },
        }

    except ABTestServiceError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ServiceError as e:
        logger.exception(f"Service error collecting metric for test {test_id}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception:
        logger.exception(f"Unexpected error collecting metric for test {test_id}")
        raise HTTPException(status_code=500, detail="Internal server error") from None
