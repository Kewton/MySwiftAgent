"""Unit tests for chat feedback schemas.

Issue #172: Feedback API Implementation
Tests for RequirementFeedbackRequest and RequirementFeedbackResponse schemas.
"""

import pytest
from pydantic import ValidationError

from app.schemas.chat import RequirementFeedbackRequest, RequirementFeedbackResponse


class TestRequirementFeedbackRequest:
    """Test RequirementFeedbackRequest schema."""

    def test_valid_request_all_fields(self):
        """Test valid request with all fields."""
        request = RequirementFeedbackRequest(
            conversation_id="conv_001",
            requirement_clarity=5,
            interpretation_accuracy=4,
            response_helpfulness=3,
            overall_satisfaction=4,
            comment="Very helpful feedback",
        )

        assert request.conversation_id == "conv_001"
        assert request.requirement_clarity == 5
        assert request.interpretation_accuracy == 4
        assert request.response_helpfulness == 3
        assert request.overall_satisfaction == 4
        assert request.comment == "Very helpful feedback"

    def test_valid_request_without_comment(self):
        """Test valid request without optional comment."""
        request = RequirementFeedbackRequest(
            conversation_id="conv_002",
            requirement_clarity=3,
            interpretation_accuracy=3,
            response_helpfulness=3,
            overall_satisfaction=3,
        )

        assert request.conversation_id == "conv_002"
        assert request.comment is None

    def test_minimum_score_values(self):
        """Test minimum valid score values (1)."""
        request = RequirementFeedbackRequest(
            conversation_id="conv_003",
            requirement_clarity=1,
            interpretation_accuracy=1,
            response_helpfulness=1,
            overall_satisfaction=1,
        )

        assert request.requirement_clarity == 1
        assert request.interpretation_accuracy == 1
        assert request.response_helpfulness == 1
        assert request.overall_satisfaction == 1

    def test_maximum_score_values(self):
        """Test maximum valid score values (5)."""
        request = RequirementFeedbackRequest(
            conversation_id="conv_004",
            requirement_clarity=5,
            interpretation_accuracy=5,
            response_helpfulness=5,
            overall_satisfaction=5,
        )

        assert request.requirement_clarity == 5
        assert request.interpretation_accuracy == 5
        assert request.response_helpfulness == 5
        assert request.overall_satisfaction == 5

    def test_invalid_score_below_minimum(self):
        """Test that scores below 1 are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RequirementFeedbackRequest(
                conversation_id="conv_005",
                requirement_clarity=0,  # Invalid: below minimum
                interpretation_accuracy=3,
                response_helpfulness=3,
                overall_satisfaction=3,
            )

        assert "requirement_clarity" in str(exc_info.value)

    def test_invalid_score_above_maximum(self):
        """Test that scores above 5 are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RequirementFeedbackRequest(
                conversation_id="conv_006",
                requirement_clarity=6,  # Invalid: above maximum
                interpretation_accuracy=3,
                response_helpfulness=3,
                overall_satisfaction=3,
            )

        assert "requirement_clarity" in str(exc_info.value)

    def test_invalid_negative_score(self):
        """Test that negative scores are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RequirementFeedbackRequest(
                conversation_id="conv_007",
                requirement_clarity=-1,  # Invalid: negative
                interpretation_accuracy=3,
                response_helpfulness=3,
                overall_satisfaction=3,
            )

        assert "requirement_clarity" in str(exc_info.value)

    def test_all_scores_out_of_range(self):
        """Test that all out-of-range scores are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RequirementFeedbackRequest(
                conversation_id="conv_008",
                requirement_clarity=0,
                interpretation_accuracy=6,
                response_helpfulness=-1,
                overall_satisfaction=10,
            )

        errors = exc_info.value.errors()
        assert len(errors) >= 4

    def test_missing_required_fields(self):
        """Test that missing required fields raise errors."""
        with pytest.raises(ValidationError):
            RequirementFeedbackRequest(
                conversation_id="conv_009",
                # Missing all score fields
            )

    def test_missing_conversation_id(self):
        """Test that missing conversation_id raises error."""
        with pytest.raises(ValidationError):
            RequirementFeedbackRequest(
                requirement_clarity=3,
                interpretation_accuracy=3,
                response_helpfulness=3,
                overall_satisfaction=3,
            )

    def test_comment_max_length(self):
        """Test comment max length validation (1000 chars)."""
        # Valid: exactly 1000 characters
        long_comment = "x" * 1000
        request = RequirementFeedbackRequest(
            conversation_id="conv_010",
            requirement_clarity=3,
            interpretation_accuracy=3,
            response_helpfulness=3,
            overall_satisfaction=3,
            comment=long_comment,
        )
        assert len(request.comment) == 1000

    def test_comment_exceeds_max_length(self):
        """Test that comment exceeding max length is rejected."""
        too_long_comment = "x" * 1001  # 1001 characters
        with pytest.raises(ValidationError) as exc_info:
            RequirementFeedbackRequest(
                conversation_id="conv_011",
                requirement_clarity=3,
                interpretation_accuracy=3,
                response_helpfulness=3,
                overall_satisfaction=3,
                comment=too_long_comment,
            )

        assert "comment" in str(exc_info.value)

    def test_empty_comment_allowed(self):
        """Test that empty comment is allowed."""
        request = RequirementFeedbackRequest(
            conversation_id="conv_012",
            requirement_clarity=3,
            interpretation_accuracy=3,
            response_helpfulness=3,
            overall_satisfaction=3,
            comment="",
        )
        assert request.comment == ""


class TestRequirementFeedbackResponse:
    """Test RequirementFeedbackResponse schema."""

    def test_success_response(self):
        """Test successful response."""
        response = RequirementFeedbackResponse(
            success=True,
            message="Feedback submitted successfully",
            feedback_id="fb_001",
            scores_submitted=4,
        )

        assert response.success is True
        assert response.message == "Feedback submitted successfully"
        assert response.feedback_id == "fb_001"
        assert response.scores_submitted == 4

    def test_failure_response(self):
        """Test failure response."""
        response = RequirementFeedbackResponse(
            success=False,
            message="Failed to submit feedback",
            feedback_id=None,
            scores_submitted=0,
        )

        assert response.success is False
        assert response.message == "Failed to submit feedback"
        assert response.feedback_id is None
        assert response.scores_submitted == 0

    def test_feedback_id_optional(self):
        """Test that feedback_id is optional."""
        response = RequirementFeedbackResponse(
            success=True,
            message="Feedback submitted",
            scores_submitted=4,
        )

        assert response.feedback_id is None

    def test_missing_required_fields(self):
        """Test that missing required fields raise errors."""
        with pytest.raises(ValidationError):
            RequirementFeedbackResponse(
                success=True,
                # Missing message and scores_submitted
            )

    def test_scores_submitted_non_negative(self):
        """Test scores_submitted is valid with 0."""
        response = RequirementFeedbackResponse(
            success=False,
            message="No scores submitted",
            scores_submitted=0,
        )
        assert response.scores_submitted == 0
