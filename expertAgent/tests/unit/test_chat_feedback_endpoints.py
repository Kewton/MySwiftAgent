"""Unit tests for chat feedback endpoints.

Issue #172: Feedback API Implementation
Tests for POST /v1/chat/feedback endpoint.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.schemas.chat import RequirementFeedbackResponse


class TestChatFeedbackEndpoint:
    """Test POST /v1/chat/feedback endpoint."""

    def test_submit_feedback_success(self, client: TestClient):
        """Test successful feedback submission."""
        with patch("app.api.v1.chat_endpoints.FeedbackService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.submit_feedback = AsyncMock(
                return_value=RequirementFeedbackResponse(
                    success=True,
                    message="Feedback submitted successfully",
                    feedback_id="fb_001",
                    scores_submitted=4,
                )
            )
            mock_service_class.return_value = mock_service

            response = client.post(
                "/aiagent-api/v1/chat/feedback",
                json={
                    "conversation_id": "conv_001",
                    "requirement_clarity": 5,
                    "interpretation_accuracy": 4,
                    "response_helpfulness": 3,
                    "overall_satisfaction": 4,
                    "comment": "Very helpful!",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["scores_submitted"] == 4

    def test_submit_feedback_validation_error_score_below_min(self, client: TestClient):
        """Test feedback submission with score below minimum."""
        response = client.post(
            "/aiagent-api/v1/chat/feedback",
            json={
                "conversation_id": "conv_001",
                "requirement_clarity": 0,  # Invalid: below 1
                "interpretation_accuracy": 3,
                "response_helpfulness": 3,
                "overall_satisfaction": 3,
            },
        )

        assert response.status_code == 422

    def test_submit_feedback_validation_error_score_above_max(self, client: TestClient):
        """Test feedback submission with score above maximum."""
        response = client.post(
            "/aiagent-api/v1/chat/feedback",
            json={
                "conversation_id": "conv_001",
                "requirement_clarity": 6,  # Invalid: above 5
                "interpretation_accuracy": 3,
                "response_helpfulness": 3,
                "overall_satisfaction": 3,
            },
        )

        assert response.status_code == 422

    def test_submit_feedback_validation_error_missing_fields(self, client: TestClient):
        """Test feedback submission with missing required fields."""
        response = client.post(
            "/aiagent-api/v1/chat/feedback",
            json={
                "conversation_id": "conv_001",
                # Missing all score fields
            },
        )

        assert response.status_code == 422

    def test_submit_feedback_validation_error_comment_too_long(
        self, client: TestClient
    ):
        """Test feedback submission with comment exceeding max length."""
        response = client.post(
            "/aiagent-api/v1/chat/feedback",
            json={
                "conversation_id": "conv_001",
                "requirement_clarity": 3,
                "interpretation_accuracy": 3,
                "response_helpfulness": 3,
                "overall_satisfaction": 3,
                "comment": "x" * 1001,  # Exceeds 1000 char limit
            },
        )

        assert response.status_code == 422

    def test_submit_feedback_without_comment(self, client: TestClient):
        """Test successful feedback submission without optional comment."""
        with patch("app.api.v1.chat_endpoints.FeedbackService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.submit_feedback = AsyncMock(
                return_value=RequirementFeedbackResponse(
                    success=True,
                    message="Feedback submitted successfully",
                    scores_submitted=4,
                )
            )
            mock_service_class.return_value = mock_service

            response = client.post(
                "/aiagent-api/v1/chat/feedback",
                json={
                    "conversation_id": "conv_001",
                    "requirement_clarity": 5,
                    "interpretation_accuracy": 4,
                    "response_helpfulness": 3,
                    "overall_satisfaction": 4,
                    # No comment field
                },
            )

            assert response.status_code == 200

    def test_submit_feedback_service_failure(self, client: TestClient):
        """Test feedback submission when service returns failure."""
        with patch("app.api.v1.chat_endpoints.FeedbackService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.submit_feedback = AsyncMock(
                return_value=RequirementFeedbackResponse(
                    success=False,
                    message="Failed to submit feedback",
                    scores_submitted=0,
                )
            )
            mock_service_class.return_value = mock_service

            response = client.post(
                "/aiagent-api/v1/chat/feedback",
                json={
                    "conversation_id": "conv_001",
                    "requirement_clarity": 5,
                    "interpretation_accuracy": 4,
                    "response_helpfulness": 3,
                    "overall_satisfaction": 4,
                },
            )

            # Service failure should return 500 status
            assert response.status_code == 500
            data = response.json()
            assert "Failed" in data["detail"]

    def test_submit_feedback_service_exception(self, client: TestClient):
        """Test feedback submission when service raises exception."""
        with patch("app.api.v1.chat_endpoints.FeedbackService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.submit_feedback = AsyncMock(
                side_effect=Exception("Unexpected error")
            )
            mock_service_class.return_value = mock_service

            response = client.post(
                "/aiagent-api/v1/chat/feedback",
                json={
                    "conversation_id": "conv_001",
                    "requirement_clarity": 5,
                    "interpretation_accuracy": 4,
                    "response_helpfulness": 3,
                    "overall_satisfaction": 4,
                },
            )

            assert response.status_code == 500

    def test_submit_feedback_all_minimum_scores(self, client: TestClient):
        """Test feedback submission with all minimum scores (1)."""
        with patch("app.api.v1.chat_endpoints.FeedbackService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.submit_feedback = AsyncMock(
                return_value=RequirementFeedbackResponse(
                    success=True,
                    message="Feedback submitted successfully",
                    scores_submitted=4,
                )
            )
            mock_service_class.return_value = mock_service

            response = client.post(
                "/aiagent-api/v1/chat/feedback",
                json={
                    "conversation_id": "conv_001",
                    "requirement_clarity": 1,
                    "interpretation_accuracy": 1,
                    "response_helpfulness": 1,
                    "overall_satisfaction": 1,
                },
            )

            assert response.status_code == 200

    def test_submit_feedback_all_maximum_scores(self, client: TestClient):
        """Test feedback submission with all maximum scores (5)."""
        with patch("app.api.v1.chat_endpoints.FeedbackService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.submit_feedback = AsyncMock(
                return_value=RequirementFeedbackResponse(
                    success=True,
                    message="Feedback submitted successfully",
                    scores_submitted=4,
                )
            )
            mock_service_class.return_value = mock_service

            response = client.post(
                "/aiagent-api/v1/chat/feedback",
                json={
                    "conversation_id": "conv_001",
                    "requirement_clarity": 5,
                    "interpretation_accuracy": 5,
                    "response_helpfulness": 5,
                    "overall_satisfaction": 5,
                },
            )

            assert response.status_code == 200


class TestChatFeedbackEndpointResponseFormat:
    """Test response format for chat feedback endpoint."""

    def test_response_contains_required_fields(self, client: TestClient):
        """Test that response contains all required fields."""
        with patch("app.api.v1.chat_endpoints.FeedbackService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.submit_feedback = AsyncMock(
                return_value=RequirementFeedbackResponse(
                    success=True,
                    message="Feedback submitted",
                    feedback_id="fb_123",
                    scores_submitted=4,
                )
            )
            mock_service_class.return_value = mock_service

            response = client.post(
                "/aiagent-api/v1/chat/feedback",
                json={
                    "conversation_id": "conv_001",
                    "requirement_clarity": 3,
                    "interpretation_accuracy": 3,
                    "response_helpfulness": 3,
                    "overall_satisfaction": 3,
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Check required fields exist
            assert "success" in data
            assert "message" in data
            assert "scores_submitted" in data

    def test_response_feedback_id_optional(self, client: TestClient):
        """Test that feedback_id can be null in response."""
        with patch("app.api.v1.chat_endpoints.FeedbackService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.submit_feedback = AsyncMock(
                return_value=RequirementFeedbackResponse(
                    success=True,
                    message="Feedback submitted",
                    feedback_id=None,
                    scores_submitted=4,
                )
            )
            mock_service_class.return_value = mock_service

            response = client.post(
                "/aiagent-api/v1/chat/feedback",
                json={
                    "conversation_id": "conv_001",
                    "requirement_clarity": 3,
                    "interpretation_accuracy": 3,
                    "response_helpfulness": 3,
                    "overall_satisfaction": 3,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["feedback_id"] is None
