from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings


class TestHealthAPI:
    @pytest.mark.production
    @pytest.mark.critical
    def test_health_check(self, client: TestClient):
        """ヘルスチェックAPIのテスト"""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert "timezone" in data
        assert "version" in data
        assert data["timezone"] == str(settings.tz)


class TestJobsAPI:
    @pytest.mark.production
    def test_create_cron_job(self, client: TestClient):
        """cronジョブ作成のテスト"""
        job_data = {
            "schedule_type": "cron",
            "cron": {"hour": "10", "minute": "30"},
            "target_url": "https://example.com/api/test",
            "method": "POST",
            "headers": {"Authorization": "Bearer test"},
            "body": {"test": "data"},
        }

        response = client.post("/api/v1/jobs/", json=job_data)
        assert response.status_code == 200

        data = response.json()
        assert "job_id" in data
        assert data["status"] == "scheduled"

    def test_create_interval_job(self, client: TestClient):
        """intervalジョブ作成のテスト"""
        job_data = {
            "schedule_type": "interval",
            "interval": {"minutes": 5},
            "target_url": "https://example.com/health",
            "method": "GET",
        }

        response = client.post("/api/v1/jobs/", json=job_data)
        assert response.status_code == 200

        data = response.json()
        assert "job_id" in data
        assert data["status"] == "scheduled"

    def test_create_date_job(self, client: TestClient):
        """dateジョブ作成のテスト"""
        future_time = datetime.now(settings.tz) + timedelta(hours=1)

        job_data = {
            "schedule_type": "date",
            "run_at": future_time.isoformat(),
            "target_url": "https://example.com/one-time",
            "method": "POST",
            "body": {"event": "scheduled"},
        }

        response = client.post("/api/v1/jobs/", json=job_data)
        assert response.status_code == 200

        data = response.json()
        assert "job_id" in data
        assert data["status"] == "scheduled"

    @pytest.mark.production
    @pytest.mark.critical
    def test_list_jobs_empty(self, client: TestClient):
        """空のジョブリストのテスト"""
        response = client.get("/api/v1/jobs/")
        assert response.status_code == 200

        data = response.json()
        assert "jobs" in data
        assert len(data["jobs"]) == 0

    def test_list_jobs_with_data(self, client: TestClient):
        """ジョブが存在する場合のリストテスト"""
        # まずジョブを作成
        job_data = {
            "schedule_type": "interval",
            "interval": {"minutes": 1},
            "target_url": "https://example.com/test",
            "method": "GET",
        }

        create_response = client.post("/api/v1/jobs/", json=job_data)
        assert create_response.status_code == 200
        job_id = create_response.json()["job_id"]

        # ジョブリストを取得
        response = client.get("/api/v1/jobs/")
        assert response.status_code == 200

        data = response.json()
        assert len(data["jobs"]) == 1

        job_info = data["jobs"][0]
        assert job_info["job_id"] == job_id
        assert "next_run_time" in job_info
        assert "trigger" in job_info

    def test_delete_job(self, client: TestClient):
        """ジョブ削除のテスト"""
        # まずジョブを作成
        job_data = {
            "schedule_type": "interval",
            "interval": {"seconds": 30},
            "target_url": "https://example.com/test",
            "method": "GET",
        }

        create_response = client.post("/api/v1/jobs/", json=job_data)
        job_id = create_response.json()["job_id"]

        # ジョブを削除
        delete_response = client.delete(f"/api/v1/jobs/{job_id}")
        assert delete_response.status_code == 200

        data = delete_response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "deleted"

    def test_pause_and_resume_job(self, client: TestClient):
        """ジョブ一時停止・再開のテスト"""
        # まずジョブを作成
        job_data = {
            "schedule_type": "interval",
            "interval": {"minutes": 1},
            "target_url": "https://example.com/test",
            "method": "GET",
        }

        create_response = client.post("/api/v1/jobs/", json=job_data)
        job_id = create_response.json()["job_id"]

        # ジョブを一時停止
        pause_response = client.post(f"/api/v1/jobs/{job_id}/pause")
        assert pause_response.status_code == 200

        data = pause_response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "paused"

        # ジョブを再開
        resume_response = client.post(f"/api/v1/jobs/{job_id}/resume")
        assert resume_response.status_code == 200

        data = resume_response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "resumed"

    def test_invalid_schedule_type(self, client: TestClient):
        """無効なスケジュールタイプのテスト"""
        job_data = {
            "schedule_type": "invalid",
            "target_url": "https://example.com/test",
            "method": "GET",
        }

        response = client.post("/api/v1/jobs/", json=job_data)
        assert response.status_code == 422  # Validation error

    def test_missing_cron_schedule(self, client: TestClient):
        """cronスケジュール情報が不足している場合のテスト"""
        job_data = {
            "schedule_type": "cron",
            "target_url": "https://example.com/test",
            "method": "GET",
        }

        response = client.post("/api/v1/jobs/", json=job_data)
        assert response.status_code == 400

    def test_delete_nonexistent_job(self, client: TestClient):
        """存在しないジョブの削除テスト"""
        response = client.delete("/api/v1/jobs/nonexistent-id")
        assert response.status_code == 404

    def test_pause_nonexistent_job(self, client: TestClient):
        """存在しないジョブの一時停止テスト"""
        response = client.post("/api/v1/jobs/nonexistent-id/pause")
        assert response.status_code == 404
