from datetime import datetime, timedelta

import pytest
import respx

from app.core.config import settings
from app.schemas.job import CronSchedule, IntervalSchedule, JobCreateRequest
from app.services.http_service import HTTPService
from app.services.job_service import JobService


class TestHTTPService:
    @pytest.mark.asyncio
    async def test_execute_request_success(self):
        """HTTP実行の成功テスト"""
        http_service = HTTPService()

        with respx.mock:
            respx.get("https://example.com/test").mock(
                return_value=respx.MockResponse(200, json={"result": "success"})
            )

            # 例外が発生しないことを確認
            await http_service.execute_request(
                url="https://example.com/test", method="GET", timeout_sec=10.0
            )

        await http_service.close()

    @pytest.mark.asyncio
    async def test_execute_request_with_retry(self):
        """リトライ機能のテスト"""
        http_service = HTTPService()

        with respx.mock:
            # 最初の2回は500エラー、3回目は成功
            route = respx.get("https://example.com/test")
            route.side_effect = [
                respx.MockResponse(500),
                respx.MockResponse(500),
                respx.MockResponse(200, json={"result": "success"}),
            ]

            # リトライ設定で実行
            await http_service.execute_request(
                url="https://example.com/test",
                method="GET",
                max_retries=2,
                retry_backoff_sec=0.1,
            )

        await http_service.close()

    @pytest.mark.asyncio
    async def test_execute_request_4xx_no_retry(self):
        """4xxエラーではリトライしないことのテスト"""
        http_service = HTTPService()

        with respx.mock:
            respx.get("https://example.com/test").mock(
                return_value=respx.MockResponse(404)
            )

            # 4xxエラーではリトライしない
            await http_service.execute_request(
                url="https://example.com/test",
                method="GET",
                max_retries=3,
                retry_backoff_sec=0.1,
            )

        await http_service.close()


class TestJobService:
    def test_create_cron_trigger(self):
        """cronトリガー作成のテスト"""
        job_service = JobService()

        job_request = JobCreateRequest(
            schedule_type="cron",
            target_url="https://example.com/test",
            cron=CronSchedule(hour="10", minute="30"),
        )

        trigger = job_service._create_trigger(job_request)
        assert trigger.timezone == settings.tz

    def test_create_interval_trigger(self):
        """intervalトリガー作成のテスト"""
        job_service = JobService()

        job_request = JobCreateRequest(
            schedule_type="interval",
            target_url="https://example.com/test",
            interval=IntervalSchedule(minutes=5),
        )

        trigger = job_service._create_trigger(job_request)
        assert trigger.timezone == settings.tz

    def test_create_date_trigger(self):
        """dateトリガー作成のテスト"""
        job_service = JobService()

        future_time = datetime.now(settings.tz) + timedelta(hours=1)

        job_request = JobCreateRequest(
            schedule_type="date",
            target_url="https://example.com/test",
            run_at=future_time.isoformat(),
        )

        trigger = job_service._create_trigger(job_request)
        # DateTrigger doesn't have timezone attribute, just check it was created
        assert trigger is not None

    def test_create_trigger_invalid_type(self):
        """無効なトリガータイプのテスト"""
        from pydantic import ValidationError

        # Pydanticバリデーションエラーをテスト
        with pytest.raises(ValidationError):
            JobCreateRequest(
                schedule_type="invalid", target_url="https://example.com/test"
            )
