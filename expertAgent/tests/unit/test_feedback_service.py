"""Unit tests for feedback service.

Issue #172: Feedback API Implementation
Tests for FeedbackService class and score conversion logic.
"""

from unittest.mock import patch

import pytest

from app.schemas.chat import RequirementFeedbackRequest
from app.services.feedback_service import FeedbackService


class TestScoreConversion:
    """Test score conversion logic (1-5 to 0.0-1.0)."""

    def test_score_1_converts_to_0(self):
        """Test that score 1 converts to 0.0."""
        service = FeedbackService()
        assert service._convert_score(1) == 0.0

    def test_score_5_converts_to_1(self):
        """Test that score 5 converts to 1.0."""
        service = FeedbackService()
        assert service._convert_score(5) == 1.0

    def test_score_3_converts_to_0_5(self):
        """Test that score 3 converts to 0.5."""
        service = FeedbackService()
        assert service._convert_score(3) == 0.5

    def test_score_2_converts_to_0_25(self):
        """Test that score 2 converts to 0.25."""
        service = FeedbackService()
        assert service._convert_score(2) == 0.25

    def test_score_4_converts_to_0_75(self):
        """Test that score 4 converts to 0.75."""
        service = FeedbackService()
        assert service._convert_score(4) == 0.75


class TestScoreMapping:
    """Test score name mapping (app field -> Langfuse score name)."""

    def test_score_mapping_exists(self):
        """Test that score mapping is defined correctly."""
        service = FeedbackService()
        expected_mapping = {
            "requirement_clarity": "req_def_clarity",
            "interpretation_accuracy": "req_def_accuracy",
            "response_helpfulness": "req_def_helpfulness",
            "overall_satisfaction": "req_def_overall",
        }
        assert service.SCORE_MAPPING == expected_mapping


class TestFeedbackServiceSubmit:
    """Test FeedbackService.submit_feedback method."""

    @pytest.fixture
    def feedback_service(self):
        """Create FeedbackService instance."""
        return FeedbackService()

    @pytest.fixture
    def valid_request(self):
        """Create a valid feedback request."""
        return RequirementFeedbackRequest(
            conversation_id="conv_001",
            requirement_clarity=5,
            interpretation_accuracy=4,
            response_helpfulness=3,
            overall_satisfaction=4,
            comment="Great service!",
        )

    @patch("app.services.feedback_service.conversation_store")
    @patch("app.services.feedback_service.langfuse_service")
    async def test_submit_feedback_success(
        self, mock_langfuse, mock_store, feedback_service, valid_request
    ):
        """Test successful feedback submission."""
        # Setup mocks
        mock_store.get_conversation.return_value = {
            "trace_id": "trace_001",
            "messages": [],
        }
        mock_langfuse._is_enabled.return_value = True
        mock_langfuse.score_trace.return_value = True

        # Execute
        response = await feedback_service.submit_feedback(valid_request)

        # Assert
        assert response.success is True
        assert response.scores_submitted == 4
        assert "successfully" in response.message.lower()

    @patch("app.services.feedback_service.conversation_store")
    @patch("app.services.feedback_service.langfuse_service")
    async def test_submit_feedback_langfuse_disabled(
        self, mock_langfuse, mock_store, feedback_service, valid_request
    ):
        """Test feedback submission when Langfuse is disabled."""
        mock_store.get_conversation.return_value = {
            "trace_id": "trace_001",
            "messages": [],
        }
        mock_langfuse._is_enabled.return_value = False

        response = await feedback_service.submit_feedback(valid_request)

        assert response.success is False
        assert "not enabled" in response.message.lower()
        assert response.scores_submitted == 0

    @patch("app.services.feedback_service.conversation_store")
    @patch("app.services.feedback_service.langfuse_service")
    async def test_submit_feedback_conversation_not_found(
        self, mock_langfuse, mock_store, feedback_service, valid_request
    ):
        """Test feedback submission when conversation is not found."""
        mock_store.get_conversation.return_value = None
        mock_langfuse._is_enabled.return_value = True

        response = await feedback_service.submit_feedback(valid_request)

        assert response.success is False
        assert "not found" in response.message.lower()
        assert response.scores_submitted == 0

    @patch("app.services.feedback_service.conversation_store")
    @patch("app.services.feedback_service.langfuse_service")
    async def test_submit_feedback_no_trace_id(
        self, mock_langfuse, mock_store, feedback_service, valid_request
    ):
        """Test feedback submission when trace_id is not in conversation."""
        mock_store.get_conversation.return_value = {
            "messages": [],
            # No trace_id
        }
        mock_langfuse._is_enabled.return_value = True

        response = await feedback_service.submit_feedback(valid_request)

        assert response.success is False
        assert "trace" in response.message.lower()
        assert response.scores_submitted == 0

    @patch("app.services.feedback_service.conversation_store")
    @patch("app.services.feedback_service.langfuse_service")
    async def test_submit_feedback_partial_failure(
        self, mock_langfuse, mock_store, feedback_service, valid_request
    ):
        """Test feedback submission with partial Langfuse failures."""
        mock_store.get_conversation.return_value = {
            "trace_id": "trace_001",
            "messages": [],
        }
        mock_langfuse._is_enabled.return_value = True
        # First 2 succeed, last 2 fail
        mock_langfuse.score_trace.side_effect = [True, True, False, False]

        response = await feedback_service.submit_feedback(valid_request)

        # Should still report success if at least some scores were submitted
        assert response.success is True
        assert response.scores_submitted == 2

    @patch("app.services.feedback_service.conversation_store")
    @patch("app.services.feedback_service.langfuse_service")
    async def test_submit_feedback_all_scores_fail(
        self, mock_langfuse, mock_store, feedback_service, valid_request
    ):
        """Test feedback submission when all Langfuse score submissions fail."""
        mock_store.get_conversation.return_value = {
            "trace_id": "trace_001",
            "messages": [],
        }
        mock_langfuse._is_enabled.return_value = True
        mock_langfuse.score_trace.return_value = False

        response = await feedback_service.submit_feedback(valid_request)

        assert response.success is False
        assert response.scores_submitted == 0

    @patch("app.services.feedback_service.conversation_store")
    @patch("app.services.feedback_service.langfuse_service")
    async def test_submit_feedback_with_comment(
        self, mock_langfuse, mock_store, feedback_service, valid_request
    ):
        """Test that comment is passed to Langfuse score_trace calls."""
        mock_store.get_conversation.return_value = {
            "trace_id": "trace_001",
            "messages": [],
        }
        mock_langfuse._is_enabled.return_value = True
        mock_langfuse.score_trace.return_value = True

        await feedback_service.submit_feedback(valid_request)

        # Verify comment was passed to at least one score_trace call
        calls = mock_langfuse.score_trace.call_args_list
        assert len(calls) == 4  # 4 scores
        # Check that comment was passed (only to overall_satisfaction by design)
        overall_call = [c for c in calls if c.kwargs.get("name") == "req_def_overall"]
        assert len(overall_call) == 1
        assert overall_call[0].kwargs.get("comment") == "Great service!"

    @patch("app.services.feedback_service.conversation_store")
    @patch("app.services.feedback_service.langfuse_service")
    async def test_submit_feedback_correct_score_values(
        self, mock_langfuse, mock_store, feedback_service, valid_request
    ):
        """Test that scores are correctly converted before submission."""
        mock_store.get_conversation.return_value = {
            "trace_id": "trace_001",
            "messages": [],
        }
        mock_langfuse._is_enabled.return_value = True
        mock_langfuse.score_trace.return_value = True

        await feedback_service.submit_feedback(valid_request)

        calls = mock_langfuse.score_trace.call_args_list
        call_dict = {c.kwargs["name"]: c.kwargs["value"] for c in calls}

        # requirement_clarity=5 -> 1.0
        assert call_dict["req_def_clarity"] == 1.0
        # interpretation_accuracy=4 -> 0.75
        assert call_dict["req_def_accuracy"] == 0.75
        # response_helpfulness=3 -> 0.5
        assert call_dict["req_def_helpfulness"] == 0.5
        # overall_satisfaction=4 -> 0.75
        assert call_dict["req_def_overall"] == 0.75

    @patch("app.services.feedback_service.conversation_store")
    @patch("app.services.feedback_service.langfuse_service")
    async def test_submit_feedback_correct_trace_id(
        self, mock_langfuse, mock_store, feedback_service, valid_request
    ):
        """Test that correct trace_id is used for Langfuse calls."""
        mock_store.get_conversation.return_value = {
            "trace_id": "trace_specific_123",
            "messages": [],
        }
        mock_langfuse._is_enabled.return_value = True
        mock_langfuse.score_trace.return_value = True

        await feedback_service.submit_feedback(valid_request)

        calls = mock_langfuse.score_trace.call_args_list
        for call in calls:
            assert call.kwargs["trace_id"] == "trace_specific_123"


class TestFeedbackServiceException:
    """Test FeedbackService exception handling."""

    @pytest.fixture
    def feedback_service(self):
        """Create FeedbackService instance."""
        return FeedbackService()

    @pytest.fixture
    def valid_request(self):
        """Create a valid feedback request."""
        return RequirementFeedbackRequest(
            conversation_id="conv_001",
            requirement_clarity=5,
            interpretation_accuracy=4,
            response_helpfulness=3,
            overall_satisfaction=4,
        )

    @patch("app.services.feedback_service.conversation_store")
    @patch("app.services.feedback_service.langfuse_service")
    async def test_submit_feedback_exception_handling(
        self, mock_langfuse, mock_store, feedback_service, valid_request
    ):
        """Test that exceptions are handled gracefully."""
        mock_store.get_conversation.side_effect = Exception("Database error")

        response = await feedback_service.submit_feedback(valid_request)

        assert response.success is False
        assert "error" in response.message.lower()
        assert response.scores_submitted == 0
