"""Integration tests for chat feedback flow.

Issue #172: Feedback API Implementation
Tests for end-to-end feedback submission flow.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient


class TestChatFeedbackIntegration:
    """Integration tests for chat feedback API."""

    @patch("app.services.feedback_service.conversation_store")
    @patch("app.services.feedback_service.langfuse_service")
    def test_feedback_flow_success(self, mock_langfuse, mock_store, client: TestClient):
        """Test complete feedback submission flow."""
        # Setup mocks
        mock_store.get_conversation.return_value = {
            "trace_id": "trace_integration_001",
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "How can I help?"},
            ],
        }
        mock_langfuse._is_enabled.return_value = True
        mock_langfuse.score_trace.return_value = True

        # Submit feedback
        response = client.post(
            "/aiagent-api/v1/chat/feedback",
            json={
                "conversation_id": "conv_integration_001",
                "requirement_clarity": 5,
                "interpretation_accuracy": 4,
                "response_helpfulness": 5,
                "overall_satisfaction": 5,
                "comment": "Excellent service!",
            },
        )

        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["scores_submitted"] == 4

        # Verify Langfuse calls
        assert mock_langfuse.score_trace.call_count == 4

        # Verify score names
        score_names = [call.kwargs["name"] for call in mock_langfuse.score_trace.call_args_list]
        expected_names = [
            "req_def_clarity",
            "req_def_accuracy",
            "req_def_helpfulness",
            "req_def_overall",
        ]
        for name in expected_names:
            assert name in score_names

    @patch("app.services.feedback_service.conversation_store")
    @patch("app.services.feedback_service.langfuse_service")
    def test_feedback_flow_conversation_not_found(
        self, mock_langfuse, mock_store, client: TestClient
    ):
        """Test feedback submission when conversation doesn't exist."""
        mock_store.get_conversation.return_value = None
        mock_langfuse._is_enabled.return_value = True

        response = client.post(
            "/aiagent-api/v1/chat/feedback",
            json={
                "conversation_id": "nonexistent_conv",
                "requirement_clarity": 3,
                "interpretation_accuracy": 3,
                "response_helpfulness": 3,
                "overall_satisfaction": 3,
            },
        )

        # Should return 500 (service failure)
        assert response.status_code == 500
        data = response.json()
        assert "not found" in data["detail"].lower()

    @patch("app.services.feedback_service.conversation_store")
    @patch("app.services.feedback_service.langfuse_service")
    def test_feedback_flow_langfuse_disabled(self, mock_langfuse, mock_store, client: TestClient):
        """Test feedback submission when Langfuse is disabled."""
        mock_store.get_conversation.return_value = {
            "trace_id": "trace_001",
            "messages": [],
        }
        mock_langfuse._is_enabled.return_value = False

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

        # Should return 500 (service failure)
        assert response.status_code == 500
        data = response.json()
        assert "not enabled" in data["detail"].lower()

    @patch("app.services.feedback_service.conversation_store")
    @patch("app.services.feedback_service.langfuse_service")
    def test_feedback_flow_missing_trace_id(self, mock_langfuse, mock_store, client: TestClient):
        """Test feedback submission when trace_id is missing from conversation."""
        mock_store.get_conversation.return_value = {
            "messages": [{"role": "user", "content": "Hello"}],
            # No trace_id
        }
        mock_langfuse._is_enabled.return_value = True

        response = client.post(
            "/aiagent-api/v1/chat/feedback",
            json={
                "conversation_id": "conv_no_trace",
                "requirement_clarity": 3,
                "interpretation_accuracy": 3,
                "response_helpfulness": 3,
                "overall_satisfaction": 3,
            },
        )

        # Should return 500 (service failure)
        assert response.status_code == 500
        data = response.json()
        assert "trace" in data["detail"].lower()

    @patch("app.services.feedback_service.conversation_store")
    @patch("app.services.feedback_service.langfuse_service")
    def test_feedback_flow_score_values_converted(
        self, mock_langfuse, mock_store, client: TestClient
    ):
        """Test that score values are correctly converted to 0.0-1.0 range."""
        mock_store.get_conversation.return_value = {
            "trace_id": "trace_conversion_001",
            "messages": [],
        }
        mock_langfuse._is_enabled.return_value = True
        mock_langfuse.score_trace.return_value = True

        response = client.post(
            "/aiagent-api/v1/chat/feedback",
            json={
                "conversation_id": "conv_conversion",
                "requirement_clarity": 1,  # Should convert to 0.0
                "interpretation_accuracy": 3,  # Should convert to 0.5
                "response_helpfulness": 5,  # Should convert to 1.0
                "overall_satisfaction": 2,  # Should convert to 0.25
            },
        )

        assert response.status_code == 200

        # Check converted values
        calls = mock_langfuse.score_trace.call_args_list
        call_dict = {c.kwargs["name"]: c.kwargs["value"] for c in calls}

        assert call_dict["req_def_clarity"] == 0.0
        assert call_dict["req_def_accuracy"] == 0.5
        assert call_dict["req_def_helpfulness"] == 1.0
        assert call_dict["req_def_overall"] == 0.25

    @patch("app.services.feedback_service.conversation_store")
    @patch("app.services.feedback_service.langfuse_service")
    def test_feedback_flow_multiple_feedbacks_same_conversation(
        self, mock_langfuse, mock_store, client: TestClient
    ):
        """Test multiple feedback submissions for the same conversation (edge case)."""
        mock_store.get_conversation.return_value = {
            "trace_id": "trace_multi_001",
            "messages": [],
        }
        mock_langfuse._is_enabled.return_value = True
        mock_langfuse.score_trace.return_value = True

        # First feedback
        response1 = client.post(
            "/aiagent-api/v1/chat/feedback",
            json={
                "conversation_id": "conv_multi",
                "requirement_clarity": 3,
                "interpretation_accuracy": 3,
                "response_helpfulness": 3,
                "overall_satisfaction": 3,
            },
        )

        assert response1.status_code == 200

        # Second feedback for same conversation
        response2 = client.post(
            "/aiagent-api/v1/chat/feedback",
            json={
                "conversation_id": "conv_multi",
                "requirement_clarity": 5,
                "interpretation_accuracy": 5,
                "response_helpfulness": 5,
                "overall_satisfaction": 5,
                "comment": "Updated feedback",
            },
        )

        # Should also succeed (Langfuse allows multiple scores)
        assert response2.status_code == 200

    def test_feedback_validation_errors(self, client: TestClient):
        """Test validation error cases."""
        # Score below minimum
        response = client.post(
            "/aiagent-api/v1/chat/feedback",
            json={
                "conversation_id": "conv_001",
                "requirement_clarity": 0,
                "interpretation_accuracy": 3,
                "response_helpfulness": 3,
                "overall_satisfaction": 3,
            },
        )
        assert response.status_code == 422

        # Score above maximum
        response = client.post(
            "/aiagent-api/v1/chat/feedback",
            json={
                "conversation_id": "conv_001",
                "requirement_clarity": 6,
                "interpretation_accuracy": 3,
                "response_helpfulness": 3,
                "overall_satisfaction": 3,
            },
        )
        assert response.status_code == 422

        # Missing conversation_id
        response = client.post(
            "/aiagent-api/v1/chat/feedback",
            json={
                "requirement_clarity": 3,
                "interpretation_accuracy": 3,
                "response_helpfulness": 3,
                "overall_satisfaction": 3,
            },
        )
        assert response.status_code == 422

        # Comment too long
        response = client.post(
            "/aiagent-api/v1/chat/feedback",
            json={
                "conversation_id": "conv_001",
                "requirement_clarity": 3,
                "interpretation_accuracy": 3,
                "response_helpfulness": 3,
                "overall_satisfaction": 3,
                "comment": "x" * 1001,
            },
        )
        assert response.status_code == 422


class TestChatFeedbackResponseTime:
    """Test response time requirements."""

    @patch("app.services.feedback_service.conversation_store")
    @patch("app.services.feedback_service.langfuse_service")
    def test_response_time_under_500ms(self, mock_langfuse, mock_store, client: TestClient):
        """Test that feedback submission responds within 500ms."""
        import time

        mock_store.get_conversation.return_value = {
            "trace_id": "trace_perf_001",
            "messages": [],
        }
        mock_langfuse._is_enabled.return_value = True
        mock_langfuse.score_trace.return_value = True

        start_time = time.time()

        response = client.post(
            "/aiagent-api/v1/chat/feedback",
            json={
                "conversation_id": "conv_perf",
                "requirement_clarity": 5,
                "interpretation_accuracy": 4,
                "response_helpfulness": 3,
                "overall_satisfaction": 4,
            },
        )

        elapsed_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        assert response.status_code == 200
        assert elapsed_time < 500, f"Response time {elapsed_time:.2f}ms exceeds 500ms limit"
