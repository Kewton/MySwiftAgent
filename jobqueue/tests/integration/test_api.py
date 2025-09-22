"""Integration tests for API endpoints."""

import pytest
from httpx import AsyncClient


class TestHealthAPI:
    """Test health and root endpoints."""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint."""
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "JobQueue API is running"}

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestJobAPI:
    """Test job API endpoints."""

    @pytest.mark.asyncio
    async def test_create_job_minimal(self, client: AsyncClient):
        """Test creating a minimal job."""
        job_data = {
            "method": "GET",
            "url": "https://httpbin.org/get",
        }

        response = await client.post("/api/v1/jobs", json=job_data)
        assert response.status_code == 201

        data = response.json()
        assert "job_id" in data
        assert data["job_id"].startswith("j_")
        assert data["status"] == "queued"

    @pytest.mark.asyncio
    async def test_create_job_full(self, client: AsyncClient):
        """Test creating a job with all parameters."""
        job_data = {
            "method": "POST",
            "url": "https://httpbin.org/post",
            "headers": {"Content-Type": "application/json"},
            "params": {"debug": "1"},
            "body": {"message": "hello"},
            "timeout_sec": 15,
            "priority": 3,
            "max_attempts": 2,
            "backoff_strategy": "linear",
            "backoff_seconds": 10.0,
            "ttl_seconds": 3600,
            "tags": ["test", "integration"],
        }

        response = await client.post("/api/v1/jobs", json=job_data)
        assert response.status_code == 201

        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"

    @pytest.mark.asyncio
    async def test_create_job_invalid_method(self, client: AsyncClient):
        """Test creating a job with invalid HTTP method."""
        job_data = {
            "method": "INVALID",
            "url": "https://httpbin.org/get",
        }

        response = await client.post("/api/v1/jobs", json=job_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_job_invalid_url(self, client: AsyncClient):
        """Test creating a job with invalid URL."""
        job_data = {
            "method": "GET",
            "url": "not-a-valid-url",
        }

        response = await client.post("/api/v1/jobs", json=job_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_job_details(self, client: AsyncClient):
        """Test getting job details."""
        # First create a job
        job_data = {
            "method": "GET",
            "url": "https://httpbin.org/get",
            "priority": 7,
            "tags": ["test"],
        }

        create_response = await client.post("/api/v1/jobs", json=job_data)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]

        # Get job details
        response = await client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "queued"
        assert data["attempt"] == 1
        assert data["max_attempts"] == 1
        assert data["priority"] == 7
        assert data["method"] == "GET"
        assert data["url"] == "https://httpbin.org/get"
        assert data["tags"] == ["test"]
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_nonexistent_job(self, client: AsyncClient):
        """Test getting details for non-existent job."""
        response = await client.get("/api/v1/jobs/j_nonexistent")
        assert response.status_code == 404
        assert response.json()["detail"] == "Job not found"

    @pytest.mark.asyncio
    async def test_get_job_result_no_execution(self, client: AsyncClient):
        """Test getting result for job that hasn't been executed."""
        # Create a job
        job_data = {
            "method": "GET",
            "url": "https://httpbin.org/get",
        }

        create_response = await client.post("/api/v1/jobs", json=job_data)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]

        # Get job result
        response = await client.get(f"/api/v1/jobs/{job_id}/result")
        assert response.status_code == 200

        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "queued"
        assert data["response_status"] is None
        assert data["response_headers"] is None
        assert data["response_body"] is None
        assert data["error"] is None
        assert data["duration_ms"] is None

    @pytest.mark.asyncio
    async def test_get_result_nonexistent_job(self, client: AsyncClient):
        """Test getting result for non-existent job."""
        response = await client.get("/api/v1/jobs/j_nonexistent/result")
        assert response.status_code == 404
        assert response.json()["detail"] == "Job not found"

    @pytest.mark.asyncio
    async def test_cancel_job(self, client: AsyncClient):
        """Test canceling a queued job."""
        # Create a job
        job_data = {
            "method": "GET",
            "url": "https://httpbin.org/get",
        }

        create_response = await client.post("/api/v1/jobs", json=job_data)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]

        # Cancel the job
        response = await client.post(f"/api/v1/jobs/{job_id}/cancel")
        assert response.status_code == 200

        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "canceled"

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_job(self, client: AsyncClient):
        """Test canceling non-existent job."""
        response = await client.post("/api/v1/jobs/j_nonexistent/cancel")
        assert response.status_code == 404
        assert response.json()["detail"] == "Job not found"

    @pytest.mark.asyncio
    async def test_cancel_already_canceled_job(self, client: AsyncClient):
        """Test canceling already canceled job."""
        # Create and cancel a job
        job_data = {
            "method": "GET",
            "url": "https://httpbin.org/get",
        }

        create_response = await client.post("/api/v1/jobs", json=job_data)
        job_id = create_response.json()["job_id"]

        await client.post(f"/api/v1/jobs/{job_id}/cancel")

        # Try to cancel again
        response = await client.post(f"/api/v1/jobs/{job_id}/cancel")
        assert response.status_code == 400
        assert "Cannot cancel job with status" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_jobs_empty(self, client: AsyncClient):
        """Test listing jobs when none exist."""
        response = await client.get("/api/v1/jobs")
        assert response.status_code == 200

        data = response.json()
        assert data["jobs"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["size"] == 20

    @pytest.mark.asyncio
    async def test_list_jobs_with_data(self, client: AsyncClient):
        """Test listing jobs with existing data."""
        # Create multiple jobs
        job_ids = []
        for i in range(3):
            job_data = {
                "method": "GET",
                "url": f"https://httpbin.org/get?test={i}",
                "tags": ["test", f"job-{i}"],
            }
            create_response = await client.post("/api/v1/jobs", json=job_data)
            job_ids.append(create_response.json()["job_id"])

        # List all jobs
        response = await client.get("/api/v1/jobs")
        assert response.status_code == 200

        data = response.json()
        assert len(data["jobs"]) == 3
        assert data["total"] == 3
        assert data["page"] == 1
        assert data["size"] == 20

        # Verify job IDs are present
        returned_job_ids = [job["job_id"] for job in data["jobs"]]
        for job_id in job_ids:
            assert job_id in returned_job_ids

    @pytest.mark.asyncio
    async def test_list_jobs_pagination(self, client: AsyncClient):
        """Test job list pagination."""
        # Create multiple jobs
        for i in range(5):
            job_data = {
                "method": "GET",
                "url": f"https://httpbin.org/get?test={i}",
            }
            await client.post("/api/v1/jobs", json=job_data)

        # Test first page with size 2
        response = await client.get("/api/v1/jobs?page=1&size=2")
        assert response.status_code == 200

        data = response.json()
        assert len(data["jobs"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["size"] == 2

        # Test second page
        response = await client.get("/api/v1/jobs?page=2&size=2")
        assert response.status_code == 200

        data = response.json()
        assert len(data["jobs"]) == 2
        assert data["total"] == 5
        assert data["page"] == 2
        assert data["size"] == 2

    @pytest.mark.asyncio
    async def test_list_jobs_filter_by_status(self, client: AsyncClient):
        """Test filtering jobs by status."""
        # Create and cancel some jobs
        job_data = {
            "method": "GET",
            "url": "https://httpbin.org/get",
        }

        # Create 2 jobs and cancel 1
        create_response1 = await client.post("/api/v1/jobs", json=job_data)
        job_id1 = create_response1.json()["job_id"]

        create_response2 = await client.post("/api/v1/jobs", json=job_data)
        job_id2 = create_response2.json()["job_id"]

        await client.post(f"/api/v1/jobs/{job_id1}/cancel")

        # Filter by queued status
        response = await client.get("/api/v1/jobs?status=queued")
        assert response.status_code == 200

        data = response.json()
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["job_id"] == job_id2
        assert data["jobs"][0]["status"] == "queued"

        # Filter by canceled status
        response = await client.get("/api/v1/jobs?status=canceled")
        assert response.status_code == 200

        data = response.json()
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["job_id"] == job_id1
        assert data["jobs"][0]["status"] == "canceled"
