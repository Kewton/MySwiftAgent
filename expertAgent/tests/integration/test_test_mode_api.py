"""Integration tests for test mode functionality across all endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
class TestMyLLMEndpointTestMode:
    """Test mode integration tests for /mylllm endpoint."""

    async def test_mylllm_test_mode_with_string(self):
        """Test mylllm endpoint with string test_response."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/aiagent-api/v1/mylllm",
                json={
                    "user_input": "test input",
                    "test_mode": True,
                    "test_response": "This is a test response",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["result"] == "This is a test response"
            assert data["text"] == "This is a test response"
            assert data["type"] == "mylllm_test"

    async def test_mylllm_test_mode_with_dict(self):
        """Test mylllm endpoint with dict test_response."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/aiagent-api/v1/mylllm",
                json={
                    "user_input": "test input",
                    "test_mode": True,
                    "test_response": {
                        "result": {"outline": [{"title": "Test"}]},
                        "custom_field": "custom value",
                    },
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert "result" in data
            assert data["custom_field"] == "custom value"

    async def test_mylllm_test_mode_without_response(self):
        """Test mylllm endpoint without test_response."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/aiagent-api/v1/mylllm",
                json={"user_input": "test input", "test_mode": True},
            )
            assert response.status_code == 200
            data = response.json()
            assert "Test mode" in data["result"]
            assert "no test_response provided" in data["result"]


@pytest.mark.asyncio
class TestUtilityEndpointsTestMode:
    """Test mode integration tests for utility endpoints."""

    async def test_jsonoutput_test_mode(self):
        """Test jsonoutput endpoint with test mode."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/aiagent-api/v1/aiagent/utility/jsonoutput",
                json={
                    "user_input": "Generate JSON",
                    "test_mode": True,
                    "test_response": {
                        "result": {
                            "outline": [
                                {"title": "Chapter 1", "overview": "Overview 1"}
                            ]
                        }
                    },
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert "result" in data
            assert "outline" in data["result"]
            assert data["result"]["outline"][0]["title"] == "Chapter 1"

    async def test_explorer_test_mode(self):
        """Test explorer endpoint with test mode."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/aiagent-api/v1/aiagent/utility/explorer",
                json={
                    "user_input": "Search for information",
                    "test_mode": True,
                    "test_response": {"result": "Detailed research report here"},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["result"] == "Detailed research report here"

    async def test_google_search_test_mode(self):
        """Test google_search endpoint with test mode."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/aiagent-api/v1/utility/google_search",
                json={
                    "queries": ["test query"],
                    "test_mode": True,
                    "test_response": {
                        "results": [
                            {
                                "title": "Test Result",
                                "url": "https://example.com",
                                "snippet": "Test snippet",
                            }
                        ]
                    },
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert data["results"][0]["title"] == "Test Result"

    async def test_google_search_overview_test_mode(self):
        """Test google_search_overview endpoint with test mode."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/aiagent-api/v1/utility/google_search_overview",
                json={
                    "queries": ["test query"],
                    "test_mode": True,
                    "test_response": {"summary": "Test summary of search results"},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["summary"] == "Test summary of search results"

    async def test_tts_and_upload_drive_test_mode(self):
        """Test tts_and_upload_drive endpoint with test mode."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/aiagent-api/v1/utility/tts_and_upload_drive",
                json={
                    "user_input": "Test script",
                    "test_mode": True,
                    "test_response": {
                        "drive_link": "https://drive.google.com/file/d/TEST_ID/view",
                        "file_id": "TEST_ID",
                    },
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert "drive_link" in data
            assert data["file_id"] == "TEST_ID"


@pytest.mark.asyncio
class TestAgentEndpointsTestMode:
    """Test mode integration tests for agent endpoints."""

    async def test_sample_agent_test_mode(self):
        """Test sample agent endpoint with test mode."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/aiagent-api/v1/aiagent/sample",
                json={
                    "user_input": "Test instruction",
                    "test_mode": True,
                    "test_response": {"result": "Sample agent result"},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["result"] == "Sample agent result"

    async def test_action_agent_test_mode(self):
        """Test action agent endpoint with test mode."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/aiagent-api/v1/aiagent/utility/action",
                json={
                    "user_input": "Send an email",
                    "test_mode": True,
                    "test_response": {
                        "result": "Email sent successfully",
                        "action": "send_email",
                    },
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["result"] == "Email sent successfully"

    async def test_playwright_agent_test_mode(self):
        """Test playwright agent endpoint with test mode."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/aiagent-api/v1/aiagent/utility/playwright",
                json={
                    "user_input": "Navigate to website",
                    "test_mode": True,
                    "test_response": {"result": "Navigation successful"},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["result"] == "Navigation successful"

    async def test_wikipedia_agent_test_mode(self):
        """Test wikipedia agent endpoint with test mode."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/aiagent-api/v1/aiagent/utility/wikipedia",
                json={
                    "user_input": "Search for topic",
                    "test_mode": True,
                    "test_response": {"summary": "Wikipedia summary"},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["summary"] == "Wikipedia summary"


@pytest.mark.asyncio
class TestComplexWorkflowSimulation:
    """Test complex workflow scenarios with test mode."""

    async def test_planner_mapper_workflow(self):
        """Test planner + mapper workflow simulation with test mode."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Step 1: Planner returns outline
            planner_response = await client.post(
                "/aiagent-api/v1/aiagent/utility/jsonoutput",
                json={
                    "user_input": "Generate outline",
                    "test_mode": True,
                    "test_response": {
                        "result": {
                            "outline": [
                                {
                                    "title": "Chapter 1",
                                    "overview": "Overview 1",
                                    "query_hint": ["query1", "query2"],
                                },
                                {
                                    "title": "Chapter 2",
                                    "overview": "Overview 2",
                                    "query_hint": ["query3", "query4"],
                                },
                            ]
                        }
                    },
                },
            )
            assert planner_response.status_code == 200
            planner_data = planner_response.json()
            outline = planner_data["result"]["outline"]

            # Step 2: Simulate mapper processing each row
            for row in outline:
                # Search for each chapter
                search_response = await client.post(
                    "/aiagent-api/v1/utility/google_search",
                    json={
                        "queries": row["query_hint"],
                        "test_mode": True,
                        "test_response": {
                            "results": [
                                {
                                    "title": f"Result for {row['title']}",
                                    "url": "https://example.com",
                                }
                            ]
                        },
                    },
                )
                assert search_response.status_code == 200

                # Explore each chapter
                explorer_response = await client.post(
                    "/aiagent-api/v1/aiagent/utility/explorer",
                    json={
                        "user_input": row["overview"],
                        "test_mode": True,
                        "test_response": {
                            "result": f"Detailed report for {row['title']}"
                        },
                    },
                )
                assert explorer_response.status_code == 200
                explorer_data = explorer_response.json()
                assert row["title"] in explorer_data["result"]
