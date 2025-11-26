"""Feedback service for requirement clarification feedback.

Issue #172: Feedback API Implementation
This service handles feedback submission to Langfuse for requirement clarification conversations.
"""

import logging
from typing import Dict

from app.schemas.chat import RequirementFeedbackRequest, RequirementFeedbackResponse
from app.services.conversation.conversation_store import conversation_store
from app.services.langfuse_service import langfuse_service

logger = logging.getLogger(__name__)


class FeedbackService:
    """Service for handling requirement clarification feedback.

    This service:
    1. Retrieves trace_id from conversation store
    2. Converts 1-5 scores to 0.0-1.0 range
    3. Submits scores to Langfuse with appropriate score names

    Score Mapping:
    - requirement_clarity -> req_def_clarity
    - interpretation_accuracy -> req_def_accuracy
    - response_helpfulness -> req_def_helpfulness
    - overall_satisfaction -> req_def_overall
    """

    # Mapping from request field names to Langfuse score names
    SCORE_MAPPING: Dict[str, str] = {
        "requirement_clarity": "req_def_clarity",
        "interpretation_accuracy": "req_def_accuracy",
        "response_helpfulness": "req_def_helpfulness",
        "overall_satisfaction": "req_def_overall",
    }

    def _convert_score(self, score: int) -> float:
        """Convert 1-5 score to 0.0-1.0 range.

        Formula: (score - 1) / 4

        Args:
            score: Integer score from 1 to 5

        Returns:
            Float score from 0.0 to 1.0

        Examples:
            >>> service._convert_score(1)
            0.0
            >>> service._convert_score(3)
            0.5
            >>> service._convert_score(5)
            1.0
        """
        return (score - 1) / 4

    async def submit_feedback(
        self, request: RequirementFeedbackRequest
    ) -> RequirementFeedbackResponse:
        """Submit feedback for a requirement clarification conversation.

        This method:
        1. Validates that Langfuse is enabled
        2. Retrieves the trace_id for the conversation
        3. Submits all 4 scores to Langfuse
        4. Returns the number of successfully submitted scores

        Args:
            request: Feedback request containing scores and conversation_id

        Returns:
            RequirementFeedbackResponse with submission status
        """
        try:
            # Check if Langfuse is enabled
            if not langfuse_service._is_enabled():
                logger.warning("Langfuse is not enabled, cannot submit feedback")
                return RequirementFeedbackResponse(
                    success=False,
                    message="Langfuse is not enabled",
                    feedback_id=None,
                    scores_submitted=0,
                )

            # Get conversation and trace_id
            conversation = conversation_store.get_conversation(request.conversation_id)

            if conversation is None:
                logger.warning(f"Conversation not found: {request.conversation_id}")
                return RequirementFeedbackResponse(
                    success=False,
                    message=f"Conversation not found: {request.conversation_id}",
                    feedback_id=None,
                    scores_submitted=0,
                )

            trace_id = conversation.get("trace_id")
            if not trace_id:
                logger.warning(
                    f"No trace_id found for conversation: {request.conversation_id}"
                )
                return RequirementFeedbackResponse(
                    success=False,
                    message="No trace ID associated with this conversation",
                    feedback_id=None,
                    scores_submitted=0,
                )

            # Submit scores to Langfuse
            scores_submitted = 0
            scores_to_submit = [
                ("requirement_clarity", request.requirement_clarity),
                ("interpretation_accuracy", request.interpretation_accuracy),
                ("response_helpfulness", request.response_helpfulness),
                ("overall_satisfaction", request.overall_satisfaction),
            ]

            for field_name, score_value in scores_to_submit:
                langfuse_score_name = self.SCORE_MAPPING[field_name]
                converted_value = self._convert_score(score_value)

                # Only include comment for overall_satisfaction
                comment = (
                    request.comment if field_name == "overall_satisfaction" else None
                )

                success = langfuse_service.score_trace(
                    trace_id=trace_id,
                    name=langfuse_score_name,
                    value=converted_value,
                    comment=comment,
                )

                if success:
                    scores_submitted += 1
                    logger.debug(
                        f"Submitted score {langfuse_score_name}={converted_value} "
                        f"for trace {trace_id}"
                    )
                else:
                    logger.warning(
                        f"Failed to submit score {langfuse_score_name} "
                        f"for trace {trace_id}"
                    )

            # Determine overall success
            if scores_submitted == 0:
                return RequirementFeedbackResponse(
                    success=False,
                    message="Failed to submit any scores to Langfuse",
                    feedback_id=None,
                    scores_submitted=0,
                )

            message = (
                f"Feedback submitted successfully. "
                f"{scores_submitted} of 4 scores recorded."
            )
            logger.info(
                f"Feedback submitted for conversation {request.conversation_id}: "
                f"{scores_submitted}/4 scores"
            )

            return RequirementFeedbackResponse(
                success=True,
                message=message,
                feedback_id=None,  # Langfuse doesn't return a feedback ID
                scores_submitted=scores_submitted,
            )

        except Exception as e:
            logger.exception(
                f"Error submitting feedback for conversation {request.conversation_id}: {e}"
            )
            return RequirementFeedbackResponse(
                success=False,
                message=f"Error submitting feedback: {str(e)}",
                feedback_id=None,
                scores_submitted=0,
            )
