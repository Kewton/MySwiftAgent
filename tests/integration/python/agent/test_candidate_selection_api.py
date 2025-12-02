"""Integration tests for candidate selection API.

Tests the full flow: initial message -> candidate generation -> selection -> continuation.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from app.main import app
from app.schemas.chat import RequirementCandidate
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def mock_candidate_generation():
    """Mock candidate generation for testing."""
    mock_candidates = [
        RequirementCandidate(
            candidate_id="A",
            title="簡易分析",
            data_source="CSVファイル",
            process_description="基本的な売上集計・月別レポート",
            output_format="Excelレポート",
            schedule="オンデマンド",
            confidence=0.85,
        ),
        RequirementCandidate(
            candidate_id="B",
            title="詳細分析",
            data_source="データベース接続",
            process_description="詳細なトレンド分析・予測モデル",
            output_format="インタラクティブダッシュボード",
            schedule="毎日実行",
            confidence=0.75,
        ),
    ]

    with patch(
        "app.services.conversation.candidate_generator.generate_requirement_candidates",
        new_callable=AsyncMock,
        return_value=mock_candidates,
    ):
        yield mock_candidates


@pytest.fixture
def mock_llm_stream_with_candidates():
    """Mock LLM stream that yields candidate_selection event first."""

    async def _stream(*args, **kwargs):
        # First yield candidate selection event (for initial message)
        yield {
            "type": "candidate_selection",
            "data": {
                "candidates": [
                    {
                        "candidate_id": "A",
                        "title": "簡易分析",
                        "data_source": "CSVファイル",
                        "process_description": "基本的な売上集計",
                        "output_format": "Excelレポート",
                        "schedule": "オンデマンド",
                        "confidence": 0.85,
                    },
                    {
                        "candidate_id": "B",
                        "title": "詳細分析",
                        "data_source": "データベース",
                        "process_description": "詳細なトレンド分析",
                        "output_format": "PDFレポート",
                        "schedule": "毎日実行",
                        "confidence": 0.75,
                    },
                ],
                "prompt_for_selection": "どちらの解釈がお望みに近いですか？AまたはBを選んでください。",
            },
        }

    with patch(
        "app.api.v1.chat_endpoints.stream_requirement_clarification",
        side_effect=_stream,
    ):
        yield


@pytest.fixture
def mock_llm_stream_after_selection():
    """Mock LLM stream for continuation after candidate selection."""

    async def _stream(*args, **kwargs):
        yield {"type": "message", "data": {"content": "候補Aを選択いただきました。"}}
        yield {
            "type": "message",
            "data": {"content": "追加の詳細を確認させてください。"},
        }
        yield {
            "type": "requirement_update",
            "data": {
                "requirements": {
                    "data_source": "CSVファイル",
                    "process_description": "基本的な売上集計",
                    "output_format": "Excelレポート",
                    "schedule": "オンデマンド",
                    "completeness": 0.75,
                }
            },
        }

    with patch(
        "app.api.v1.chat_endpoints.stream_requirement_clarification",
        side_effect=_stream,
    ):
        yield


@pytest.mark.asyncio
class TestInitialMessageWithCandidates:
    """Test suite for initial message triggering candidate generation."""

    async def test_initial_message_returns_candidates(self, mock_llm_stream_with_candidates):
        """Test that initial message returns candidate selection event."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "conversation_id": "test_conv_candidates_001",
                "user_message": "売上データを分析したい",
                "context": {
                    "previous_messages": [],  # Empty = initial message
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
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

            # Collect SSE events
            events = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    events.append(data)

            # Verify candidate_selection event
            candidate_events = [e for e in events if e["type"] == "candidate_selection"]
            assert len(candidate_events) == 1

            candidate_data = candidate_events[0]["data"]
            assert "candidates" in candidate_data
            assert len(candidate_data["candidates"]) == 2
            assert "prompt_for_selection" in candidate_data

    async def test_candidates_have_required_fields(self, mock_llm_stream_with_candidates):
        """Test that candidates in SSE event have all required fields."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "conversation_id": "test_conv_candidates_002",
                "user_message": "データ分析をしたい",
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

            events = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    events.append(data)

            candidate_events = [e for e in events if e["type"] == "candidate_selection"]
            candidates = candidate_events[0]["data"]["candidates"]

            for candidate in candidates:
                assert "candidate_id" in candidate
                assert "title" in candidate
                assert "data_source" in candidate
                assert "process_description" in candidate
                assert "output_format" in candidate
                assert "schedule" in candidate
                assert "confidence" in candidate

    async def test_candidates_ids_are_a_and_b(self, mock_llm_stream_with_candidates):
        """Test that candidate IDs are 'A' and 'B'."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "conversation_id": "test_conv_candidates_003",
                "user_message": "レポート作成",
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

            events = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    events.append(data)

            candidate_events = [e for e in events if e["type"] == "candidate_selection"]
            candidates = candidate_events[0]["data"]["candidates"]
            candidate_ids = [c["candidate_id"] for c in candidates]

            assert "A" in candidate_ids
            assert "B" in candidate_ids


@pytest.fixture
def setup_candidates_in_store():
    """Setup candidates in conversation store for testing."""
    from app.services.conversation.conversation_store import conversation_store

    # Create test candidates
    candidate_a = RequirementCandidate(
        candidate_id="A",
        title="簡易分析",
        data_source="CSVファイル",
        process_description="基本的な売上集計",
        output_format="Excelレポート",
        schedule="オンデマンド",
        confidence=0.85,
    )
    candidate_b = RequirementCandidate(
        candidate_id="B",
        title="詳細分析",
        data_source="データベース",
        process_description="詳細なトレンド分析",
        output_format="PDFレポート",
        schedule="毎日実行",
        confidence=0.75,
    )

    # Save candidates for test conversations
    for conv_id in [
        "test_conv_select_001",
        "test_conv_select_002",
        "test_conv_select_003",
    ]:
        conversation_store.save_candidates(conv_id, [candidate_a, candidate_b])

    yield [candidate_a, candidate_b]

    # Cleanup
    for conv_id in [
        "test_conv_select_001",
        "test_conv_select_002",
        "test_conv_select_003",
    ]:
        conversation_store.delete_conversation(conv_id)


@pytest.mark.asyncio
class TestCandidateSelectionEndpoint:
    """Test suite for POST /chat/select-candidate endpoint."""

    async def test_select_candidate_a(self, setup_candidates_in_store):
        """Test successful selection of candidate A."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "conversation_id": "test_conv_select_001",
                "selected_candidate_id": "A",
            }

            response = await client.post("/aiagent-api/v1/chat/select-candidate", json=request_data)

            assert response.status_code == 200
            result = response.json()
            assert result["selected_candidate_id"] == "A"
            assert result["requirements"]["data_source"] == "CSVファイル"

    async def test_select_candidate_b(self, setup_candidates_in_store):
        """Test successful selection of candidate B."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "conversation_id": "test_conv_select_002",
                "selected_candidate_id": "B",
            }

            response = await client.post("/aiagent-api/v1/chat/select-candidate", json=request_data)

            assert response.status_code == 200
            result = response.json()
            assert result["selected_candidate_id"] == "B"
            assert result["requirements"]["data_source"] == "データベース"

    async def test_select_invalid_candidate(self):
        """Test rejection of invalid candidate ID."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "conversation_id": "test_conv_select_003",
                "selected_candidate_id": "C",  # Invalid
            }

            response = await client.post("/aiagent-api/v1/chat/select-candidate", json=request_data)

            # Should return validation error
            assert response.status_code in [400, 422]


@pytest.mark.asyncio
class TestContinuationAfterSelection:
    """Test suite for dialogue continuation after candidate selection."""

    async def test_continuation_uses_selected_requirements(self, mock_llm_stream_after_selection):
        """Test that continuation uses requirements from selected candidate."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Simulate continuation after selection
            request_data = {
                "conversation_id": "test_conv_continue_001",
                "user_message": "はい、それでお願いします",
                "context": {
                    "previous_messages": [
                        {"role": "user", "content": "売上データを分析したい"},
                        {
                            "role": "assistant",
                            "content": "候補を提示します。どちらがよいですか？",
                        },
                    ],
                    "current_requirements": {
                        "data_source": "CSVファイル",
                        "process_description": "基本的な売上集計",
                        "output_format": "Excelレポート",
                        "schedule": "オンデマンド",
                        "completeness": 0.75,
                    },
                },
            }

            response = await client.post(
                "/aiagent-api/v1/chat/requirement-definition", json=request_data
            )

            assert response.status_code == 200

            events = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    events.append(data)

            # Should have message events (normal dialogue continuation)
            message_events = [e for e in events if e["type"] == "message"]
            assert len(message_events) >= 1


@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling scenarios."""

    async def test_llm_error_during_candidate_generation(self):
        """Test handling of LLM errors during candidate generation."""

        async def _failing_stream(*args, **kwargs):
            raise Exception("LLM service unavailable")

        with patch(
            "app.api.v1.chat_endpoints.stream_requirement_clarification",
            side_effect=_failing_stream,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                request_data = {
                    "conversation_id": "test_conv_error_001",
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

                # Should return SSE stream with error event
                assert response.status_code == 200

                events = []
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        events.append(data)

                error_events = [e for e in events if e["type"] == "error"]
                assert len(error_events) == 1

    async def test_missing_conversation_id_in_selection(self):
        """Test error when conversation_id is missing in selection request."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "selected_candidate_id": "A",
                # Missing conversation_id
            }

            response = await client.post("/aiagent-api/v1/chat/select-candidate", json=request_data)

            assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
class TestPerformance:
    """Performance tests for candidate generation."""

    async def test_candidate_generation_time(self, mock_llm_stream_with_candidates):
        """Test that candidate generation completes within 4 seconds."""
        import time

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "conversation_id": "test_conv_perf_001",
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

            start_time = time.time()
            response = await client.post(
                "/aiagent-api/v1/chat/requirement-definition", json=request_data
            )

            # Consume the stream
            async for _line in response.aiter_lines():
                pass

            elapsed_time = time.time() - start_time

            # Should complete within 4 seconds (with mocked LLM)
            assert elapsed_time < 4.0, f"Response took {elapsed_time:.2f}s (> 4s limit)"


@pytest.mark.asyncio
class TestSSECandidateSelectionEvent:
    """Test SSE candidate_selection event integration."""

    async def test_sse_candidate_selection_event_structure(self, mock_llm_stream_with_candidates):
        """Test that SSE candidate_selection event has correct structure."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "conversation_id": "test_conv_sse_001",
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

            events = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    events.append(data)

            # Find candidate_selection event
            candidate_events = [e for e in events if e["type"] == "candidate_selection"]
            assert len(candidate_events) >= 1

            event = candidate_events[0]
            assert "type" in event
            assert event["type"] == "candidate_selection"
            assert "data" in event
            assert "candidates" in event["data"]
            assert "prompt_for_selection" in event["data"]

    async def test_complete_flow_with_sse(self, mock_llm_stream_with_candidates):
        """Test complete flow: SSE candidate_selection -> selection -> continuation."""
        from app.services.conversation.conversation_store import conversation_store

        transport = ASGITransport(app=app)

        # Step 1: Initial message triggers candidate_selection SSE event
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "conversation_id": "test_conv_complete_flow_001",
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

            events = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    events.append(data)

            # Verify candidate_selection event exists
            candidate_events = [e for e in events if e["type"] == "candidate_selection"]
            assert len(candidate_events) >= 1

        # Step 2: Setup candidates in store for selection
        candidate_a = RequirementCandidate(
            candidate_id="A",
            title="簡易分析",
            data_source="CSVファイル",
            process_description="基本的な売上集計",
            output_format="Excelレポート",
            schedule="オンデマンド",
            confidence=0.85,
        )
        candidate_b = RequirementCandidate(
            candidate_id="B",
            title="詳細分析",
            data_source="データベース",
            process_description="詳細なトレンド分析",
            output_format="PDFレポート",
            schedule="毎日実行",
            confidence=0.75,
        )
        conversation_store.save_candidates(
            "test_conv_complete_flow_001", [candidate_a, candidate_b]
        )

        # Step 3: Select candidate A
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            select_request = {
                "conversation_id": "test_conv_complete_flow_001",
                "selected_candidate_id": "A",
            }

            response = await client.post(
                "/aiagent-api/v1/chat/select-candidate", json=select_request
            )

            assert response.status_code == 200
            result = response.json()
            assert result["selected_candidate_id"] == "A"
            assert result["requirements"]["data_source"] == "CSVファイル"

        # Cleanup
        conversation_store.delete_conversation("test_conv_complete_flow_001")


@pytest.mark.asyncio
class TestErrorHandlingInSelectionFlow:
    """Test error handling in candidate selection flow."""

    async def test_select_candidate_not_found_conversation(self):
        """Test error when selecting from non-existent conversation."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "conversation_id": "non_existent_conversation_12345",
                "selected_candidate_id": "A",
            }

            response = await client.post("/aiagent-api/v1/chat/select-candidate", json=request_data)

            # Should return 404 for not found conversation
            assert response.status_code == 404

    async def test_select_candidate_not_in_list(self, setup_candidates_in_store):
        """Test error when selected candidate not in stored candidates."""
        from app.services.conversation.conversation_store import conversation_store

        # Create a conversation with only candidate A
        candidate_a = RequirementCandidate(
            candidate_id="A",
            title="候補A",
            data_source="CSV",
            process_description="処理",
            output_format="Excel",
            schedule="毎日",
            confidence=0.8,
        )
        conversation_store.save_candidates("test_conv_single_candidate_001", [candidate_a])

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "conversation_id": "test_conv_single_candidate_001",
                "selected_candidate_id": "B",  # Not in list
            }

            response = await client.post("/aiagent-api/v1/chat/select-candidate", json=request_data)

            # Should return 400 for candidate not found
            assert response.status_code == 400

        # Cleanup
        conversation_store.delete_conversation("test_conv_single_candidate_001")

    async def test_sse_error_event_on_exception(self):
        """Test that SSE error event is sent on exception."""

        async def _error_stream(*args, **kwargs):
            raise Exception("Simulated error")

        with patch(
            "app.api.v1.chat_endpoints.stream_requirement_clarification",
            side_effect=_error_stream,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                request_data = {
                    "conversation_id": "test_conv_error_sse_001",
                    "user_message": "エラーテスト",
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

                events = []
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        events.append(data)

                # Should contain an error event
                error_events = [e for e in events if e["type"] == "error"]
                assert len(error_events) == 1
                assert "message" in error_events[0]["data"]


@pytest.mark.asyncio
class TestConversationStoreIntegration:
    """Test integration with conversation store."""

    async def test_candidates_saved_to_store(self, setup_candidates_in_store):
        """Test that candidates are saved to conversation store."""
        from app.services.conversation.conversation_store import conversation_store

        # Verify candidates exist in store
        candidates = conversation_store.get_candidates("test_conv_select_001")
        assert candidates is not None
        assert len(candidates) == 2
        assert candidates[0].candidate_id == "A"
        assert candidates[1].candidate_id == "B"

    async def test_selected_candidate_saved_to_store(self, setup_candidates_in_store):
        """Test that selected candidate is saved to store."""
        from app.services.conversation.conversation_store import conversation_store

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "conversation_id": "test_conv_select_001",
                "selected_candidate_id": "A",
            }

            response = await client.post("/aiagent-api/v1/chat/select-candidate", json=request_data)

            assert response.status_code == 200

        # Verify selected candidate is saved
        selected = conversation_store.get_selected_candidate("test_conv_select_001")
        assert selected == "A"

    async def test_conversation_messages_saved(self, mock_llm_stream_after_selection):
        """Test that conversation messages are saved to store."""
        from app.services.conversation.conversation_store import conversation_store

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "conversation_id": "test_conv_messages_001",
                "user_message": "テストメッセージ",
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

            # Consume stream
            async for _line in response.aiter_lines():
                pass

        # Verify message saved
        messages = conversation_store.get_messages("test_conv_messages_001")
        assert len(messages) >= 1
        assert any(m["role"] == "user" for m in messages)

        # Cleanup
        conversation_store.delete_conversation("test_conv_messages_001")

    async def test_select_candidate_internal_error(self):
        """Test handling of internal error during candidate selection."""
        from app.services.conversation.conversation_store import conversation_store

        # Save candidates to the store
        candidate_a = RequirementCandidate(
            candidate_id="A",
            title="候補A",
            data_source="CSV",
            process_description="処理",
            output_format="Excel",
            schedule="毎日",
            confidence=0.8,
        )
        conversation_store.save_candidates("test_conv_internal_error_001", [candidate_a])

        # Mock candidate_to_requirement_state_dict to raise an error
        with patch(
            "app.api.v1.chat_endpoints.candidate_to_requirement_state_dict",
            side_effect=Exception("Internal processing error"),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                request_data = {
                    "conversation_id": "test_conv_internal_error_001",
                    "selected_candidate_id": "A",
                }

                response = await client.post(
                    "/aiagent-api/v1/chat/select-candidate", json=request_data
                )

                # Should return 500 internal server error
                assert response.status_code == 500
                assert "候補の選択に失敗しました" in response.json()["detail"]

        # Cleanup
        conversation_store.delete_conversation("test_conv_internal_error_001")
