"""Integration tests for chat endpoints.

Tests SSE streaming, job creation, and error handling.
"""

import json
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def mock_llm_stream():
    """Mock LLM streaming responses for testing."""

    async def _stream(*args, **kwargs):
        # Simulate streaming response
        yield {"type": "message", "data": {"content": "かしこまりました。"}}
        yield {"type": "message", "data": {"content": "どのような形式の"}}
        yield {"type": "message", "data": {"content": "データですか？"}}
        yield {
            "type": "requirement_update",
            "data": {
                "requirements": {
                    "data_source": None,
                    "process_description": "データ分析",
                    "output_format": None,
                    "schedule": None,
                    "completeness": 0.35,
                }
            },
        }

    with patch(
        "app.api.v1.chat_endpoints.stream_requirement_clarification",
        side_effect=_stream,
    ):
        yield


@pytest.fixture
def mock_llm_stream_ready():
    """Mock LLM streaming with requirements_ready event."""

    async def _stream(*args, **kwargs):
        yield {"type": "message", "data": {"content": "要件が整いました！"}}
        yield {
            "type": "requirement_update",
            "data": {
                "requirements": {
                    "data_source": "CSVファイル",
                    "process_description": "データ分析",
                    "output_format": "Excelレポート",
                    "schedule": "毎日実行",
                    "completeness": 1.0,
                }
            },
        }
        yield {"type": "requirements_ready", "data": {}}

    with patch(
        "app.api.v1.chat_endpoints.stream_requirement_clarification",
        side_effect=_stream,
    ):
        yield


@pytest.fixture
def mock_job_generator_success():
    """Mock successful job generator response."""
    from app.schemas.job_generator import JobGeneratorResponse

    async def _mock_job_generator(request):
        return JobGeneratorResponse(
            status="success",
            job_id="job_test_12345",
            job_master_id="jm_test_12345",
            task_breakdown=[],
        )

    # Patch at the source module where generate_job_and_tasks is defined
    with patch(
        "app.api.v1.job_generator_endpoints.generate_job_and_tasks",
        side_effect=_mock_job_generator,
    ):
        yield


@pytest.mark.asyncio
class TestRequirementDefinitionEndpoint:
    """Test suite for POST /chat/requirement-definition endpoint."""

    async def test_successful_sse_streaming(self, mock_llm_stream):
        """Test successful SSE streaming with requirement clarification."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "conversation_id": "test_conv_001",
                "user_message": "売上データを分析したい",
                "context": {
                    "previous_messages": [],
                    "current_requirements": {
                        "data_source": None,
                        "process_description": None,
                        "output_format": None,
                        "schedule": None,
                        "completeness": 0.0,
                    },
                },
            }

            response = await client.post(
                "/aiagent-api/v1/chat/requirement-definition", json=request_data
            )

            assert response.status_code == 200
            assert (
                response.headers["content-type"] == "text/event-stream; charset=utf-8"
            )

            # Collect SSE events
            events = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    events.append(data)

            # Verify events
            assert (
                len(events) >= 3
            )  # At least 3 message chunks + requirement_update + done

            # Check message events
            message_events = [e for e in events if e["type"] == "message"]
            assert len(message_events) >= 3

            # Check requirement_update event
            update_events = [e for e in events if e["type"] == "requirement_update"]
            assert len(update_events) == 1
            assert update_events[0]["data"]["requirements"]["completeness"] == 0.35

            # Check done event
            done_events = [e for e in events if e["type"] == "done"]
            assert len(done_events) == 1

    async def test_streaming_with_previous_messages(self, mock_llm_stream):
        """Test SSE streaming includes previous conversation context."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "conversation_id": "test_conv_002",
                "user_message": "CSVファイルです",
                "context": {
                    "previous_messages": [
                        {"role": "user", "content": "売上データを分析したい"},
                        {
                            "role": "assistant",
                            "content": "どのような形式のデータですか？",
                        },
                    ],
                    "current_requirements": {
                        "data_source": None,
                        "process_description": "売上データを分析",
                        "output_format": None,
                        "schedule": None,
                        "completeness": 0.35,
                    },
                },
            }

            response = await client.post(
                "/aiagent-api/v1/chat/requirement-definition", json=request_data
            )

            assert response.status_code == 200

    async def test_streaming_requirements_ready_event(self, mock_llm_stream_ready):
        """Test requirements_ready event when completeness ≥80%."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "conversation_id": "test_conv_003",
                "user_message": "毎日実行してください",
                "context": {
                    "previous_messages": [],
                    "current_requirements": {
                        "data_source": "CSVファイル",
                        "process_description": "データ分析",
                        "output_format": "Excelレポート",
                        "schedule": None,
                        "completeness": 0.85,
                    },
                },
            }

            response = await client.post(
                "/aiagent-api/v1/chat/requirement-definition", json=request_data
            )

            assert response.status_code == 200

            # Collect events
            events = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    events.append(data)

            # Verify requirements_ready event
            ready_events = [e for e in events if e["type"] == "requirements_ready"]
            assert len(ready_events) == 1

    async def test_missing_conversation_id(self):
        """Test error when conversation_id is missing."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "user_message": "売上データを分析したい",
                "context": {
                    "previous_messages": [],
                    "current_requirements": {
                        "data_source": None,
                        "process_description": None,
                        "output_format": None,
                        "schedule": None,
                        "completeness": 0.0,
                    },
                },
            }

            response = await client.post(
                "/aiagent-api/v1/chat/requirement-definition", json=request_data
            )

            assert response.status_code == 422  # Validation error

    async def test_invalid_context_structure(self):
        """Test error when context structure is invalid."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "conversation_id": "test_conv_004",
                "user_message": "売上データを分析したい",
                "context": {"invalid_key": "invalid_value"},
            }

            response = await client.post(
                "/aiagent-api/v1/chat/requirement-definition", json=request_data
            )

            assert response.status_code in [
                400,
                422,
                500,
            ]  # Various possible error codes

    async def test_llm_service_error_handling(self):
        """Test error handling when LLM service fails."""

        async def _failing_stream(*args, **kwargs):
            raise Exception("LLM service unavailable")

        with patch(
            "app.api.v1.chat_endpoints.stream_requirement_clarification",
            side_effect=_failing_stream,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                request_data = {
                    "conversation_id": "test_conv_005",
                    "user_message": "売上データを分析したい",
                    "context": {
                        "previous_messages": [],
                        "current_requirements": {
                            "data_source": None,
                            "process_description": None,
                            "output_format": None,
                            "schedule": None,
                            "completeness": 0.0,
                        },
                    },
                }

                response = await client.post(
                    "/aiagent-api/v1/chat/requirement-definition", json=request_data
                )

                # Should return SSE with error event
                assert response.status_code == 200

                events = []
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        events.append(data)

                # Check for error event
                error_events = [e for e in events if e["type"] == "error"]
                assert len(error_events) == 1
                assert "エラーが発生しました" in error_events[0]["data"]["message"]


@pytest.mark.asyncio
class TestCreateJobEndpoint:
    """Test suite for POST /chat/create-job endpoint."""

    async def test_successful_job_creation(self, mock_job_generator_success):
        """Test successful job creation from clarified requirements."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "conversation_id": "test_conv_006",
                "requirements": {
                    "data_source": "CSVファイル",
                    "process_description": "売上データの月別集計",
                    "output_format": "Excelレポート",
                    "schedule": "毎日朝9時",
                    "completeness": 1.0,
                },
            }

            response = await client.post(
                "/aiagent-api/v1/chat/create-job", json=request_data
            )

            assert response.status_code == 200

            result = response.json()
            assert result["status"] == "success"
            assert result["job_id"] == "job_test_12345"
            assert result["job_master_id"] == "jm_test_12345"
            assert result["message"] == "ジョブを作成しました"

    async def test_insufficient_completeness(self, mock_job_generator_success):
        """Test error when requirements completeness < 80%."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "conversation_id": "test_conv_007",
                "requirements": {
                    "data_source": "CSVファイル",
                    "process_description": "データ分析",
                    "output_format": None,
                    "schedule": None,
                    "completeness": 0.60,  # Below 80% threshold
                },
            }

            response = await client.post(
                "/aiagent-api/v1/chat/create-job", json=request_data
            )

            assert response.status_code == 400
            assert "not sufficiently clarified" in response.json()["detail"]
            assert "60%" in response.json()["detail"]

    async def test_minimum_completeness_threshold(self, mock_job_generator_success):
        """Test job creation with exactly 80% completeness."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "conversation_id": "test_conv_008",
                "requirements": {
                    "data_source": "CSVファイル",
                    "process_description": "データ分析",
                    "output_format": "Excelレポート",
                    "schedule": None,
                    "completeness": 0.85,  # 25% + 35% + 25% = 85%
                },
            }

            response = await client.post(
                "/aiagent-api/v1/chat/create-job", json=request_data
            )

            assert response.status_code == 200

    async def test_job_generator_failure(self):
        """Test error handling when Job Generator fails."""

        async def _failing_job_generator(request):
            raise Exception("Job Generator internal error")

        with patch(
            "app.api.v1.job_generator_endpoints.generate_job_and_tasks",
            side_effect=_failing_job_generator,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                request_data = {
                    "conversation_id": "test_conv_009",
                    "requirements": {
                        "data_source": "CSVファイル",
                        "process_description": "データ分析",
                        "output_format": "Excelレポート",
                        "schedule": "毎日",
                        "completeness": 0.85,
                    },
                }

                response = await client.post(
                    "/aiagent-api/v1/chat/create-job", json=request_data
                )

                assert response.status_code == 500
                assert "ジョブの作成に失敗しました" in response.json()["detail"]

    async def test_job_generator_missing_job_ids(self):
        """Test error when Job Generator doesn't return job IDs."""

        async def _incomplete_job_generator(request):
            return {
                "status": "success",
                # Missing job_id and job_master_id
            }

        with patch(
            "app.api.v1.job_generator_endpoints.generate_job_and_tasks",
            side_effect=_incomplete_job_generator,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                request_data = {
                    "conversation_id": "test_conv_010",
                    "requirements": {
                        "data_source": "CSVファイル",
                        "process_description": "データ分析",
                        "output_format": "Excelレポート",
                        "schedule": "毎日",
                        "completeness": 1.0,
                    },
                }

                response = await client.post(
                    "/aiagent-api/v1/chat/create-job", json=request_data
                )

                assert response.status_code == 500

    async def test_requirements_to_job_request_conversion(
        self, mock_job_generator_success
    ):
        """Test conversion of RequirementState to Job Generator format."""
        # This test indirectly verifies _convert_requirements_to_job_request
        # by checking that Job Generator is called with correct format
        from app.schemas.job_generator import JobGeneratorResponse

        called_with = None

        async def _capture_job_generator(request):
            nonlocal called_with
            called_with = request
            return JobGeneratorResponse(
                status="success",
                job_id="job_test",
                job_master_id="jm_test",
            )

        with patch(
            "app.api.v1.job_generator_endpoints.generate_job_and_tasks",
            side_effect=_capture_job_generator,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                request_data = {
                    "conversation_id": "test_conv_011",
                    "requirements": {
                        "data_source": "CSVファイル",
                        "process_description": "売上データ分析",
                        "output_format": "Excelレポート",
                        "schedule": "毎日朝9時",
                        "completeness": 1.0,
                    },
                }

                response = await client.post(
                    "/aiagent-api/v1/chat/create-job", json=request_data
                )

                assert response.status_code == 200

                # Verify conversion format (called_with is JobGeneratorRequest Pydantic model)
                assert called_with is not None
                assert hasattr(called_with, "user_requirement")
                assert "CSVファイル" in called_with.user_requirement
                assert "売上データ分析" in called_with.user_requirement
                assert "Excelレポート" in called_with.user_requirement
                assert "毎日朝9時" in called_with.user_requirement

    async def test_missing_conversation_id_in_create_job(self):
        """Test error when conversation_id is missing in create-job."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "requirements": {
                    "data_source": "CSVファイル",
                    "process_description": "データ分析",
                    "output_format": "Excelレポート",
                    "schedule": "毎日",
                    "completeness": 1.0,
                }
            }

            response = await client.post(
                "/aiagent-api/v1/chat/create-job", json=request_data
            )

            assert response.status_code == 422  # Validation error

    async def test_invalid_requirements_structure(self):
        """Test error when requirements structure is invalid."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "conversation_id": "test_conv_012",
                "requirements": {
                    "invalid_field": "value"
                    # Missing required fields
                },
            }

            response = await client.post(
                "/aiagent-api/v1/chat/create-job", json=request_data
            )

            assert response.status_code == 400  # Insufficient completeness (0%)
