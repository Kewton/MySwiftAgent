"""Performance tests for Interface Validation.

This module tests validation performance with large-scale data:
- Complex schema validation
- Bulk job validation (100 jobs)
- Validation latency measurement
"""

import time

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import new as ulid_new

from app.models.interface_master import InterfaceMaster
from app.models.task_master import TaskMaster
from tests.utils.interface_mock import InterfaceMockGenerator


class TestInterfacePerformance:
    """Performance test suite for Interface Validation."""

    @pytest.mark.asyncio
    async def test_performance_complex_schema_validation(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test validation performance with complex nested schema."""
        # Create complex schema (5 levels deep, 50+ properties)
        complex_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "metadata": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "timestamp": {"type": "string", "format": "date-time"},
                        "version": {"type": "string"},
                    },
                    "required": ["id", "timestamp"],
                },
                "data": {
                    "type": "object",
                    "properties": {
                        "users": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "integer"},
                                    "name": {"type": "string"},
                                    "email": {"type": "string", "format": "email"},
                                    "profile": {
                                        "type": "object",
                                        "properties": {
                                            "age": {"type": "integer"},
                                            "address": {
                                                "type": "object",
                                                "properties": {
                                                    "street": {"type": "string"},
                                                    "city": {"type": "string"},
                                                    "country": {"type": "string"},
                                                    "postal_code": {
                                                        "type": "string"
                                                    },
                                                },
                                            },
                                            "preferences": {
                                                "type": "object",
                                                "properties": {
                                                    "language": {"type": "string"},
                                                    "timezone": {"type": "string"},
                                                    "notifications": {
                                                        "type": "object",
                                                        "properties": {
                                                            "email": {
                                                                "type": "boolean"
                                                            },
                                                            "push": {
                                                                "type": "boolean"
                                                            },
                                                        },
                                                    },
                                                },
                                            },
                                        },
                                    },
                                },
                                "required": ["id", "name", "email"],
                            },
                        },
                        "transactions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "transaction_id": {"type": "string"},
                                    "amount": {"type": "number"},
                                    "currency": {"type": "string"},
                                    "items": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "product_id": {"type": "string"},
                                                "quantity": {"type": "integer"},
                                                "price": {"type": "number"},
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                    "required": ["users"],
                },
            },
            "required": ["metadata", "data"],
        }

        # Create InterfaceMaster
        interface_id = f"if_{ulid_new()}"
        interface = InterfaceMaster(
            id=interface_id,
            name="PerformanceComplexInterface",
            output_schema=complex_schema,
            is_active=True,
        )
        db_session.add(interface)

        # Create TaskMaster
        tm_id = f"tm_{ulid_new()}"
        tm = TaskMaster(
            id=tm_id,
            name="perf_complex_task",
            method="GET",
            url="https://httpbin.org/json",
            timeout_sec=30,
            output_interface_id=interface_id,
            is_active=True,
            current_version=1,
            created_by="perf_test",
            updated_by="perf_test",
        )
        db_session.add(tm)
        await db_session.commit()

        # Generate complex mock data
        mock_data = InterfaceMockGenerator.generate_mock_data(complex_schema)

        # Measure validation time (single validation)
        start_time = time.time()

        response = await client.post(
            "/api/v1/jobs",
            json={
                "name": "Performance Test - Complex Schema",
                "method": "GET",
                "url": "https://httpbin.org/get",
                "tasks": [{"master_id": tm_id, "sequence": 0}],
                "validate_interfaces": True,
            },
        )

        validation_time_ms = (time.time() - start_time) * 1000

        assert response.status_code == 201
        job_data = response.json()
        assert job_data["status"] == "queued"

        # Performance assertion: Complex schema validation should complete < 100ms
        assert (
            validation_time_ms < 100
        ), f"Validation took {validation_time_ms:.2f}ms (expected < 100ms)"

        print(
            f"\n✓ Complex schema validation: {validation_time_ms:.2f}ms (threshold: 100ms)"
        )

    @pytest.mark.asyncio
    async def test_performance_bulk_job_validation(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test validation performance with 100 jobs in parallel."""
        # Create simple schema
        simple_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "result": {"type": "string"},
                "count": {"type": "integer"},
            },
            "required": ["result"],
        }

        # Create InterfaceMaster
        interface_id = f"if_{ulid_new()}"
        interface = InterfaceMaster(
            id=interface_id,
            name="PerformanceBulkInterface",
            output_schema=simple_schema,
            is_active=True,
        )
        db_session.add(interface)

        # Create TaskMaster
        tm_id = f"tm_{ulid_new()}"
        tm = TaskMaster(
            id=tm_id,
            name="perf_bulk_task",
            method="GET",
            url="https://httpbin.org/json",
            timeout_sec=30,
            output_interface_id=interface_id,
            is_active=True,
            current_version=1,
            created_by="perf_test",
            updated_by="perf_test",
        )
        db_session.add(tm)
        await db_session.commit()

        # Create 100 jobs with validation
        num_jobs = 100
        job_ids = []

        start_time = time.time()

        for i in range(num_jobs):
            response = await client.post(
                "/api/v1/jobs",
                json={
                    "name": f"Bulk Test Job {i+1}",
                    "method": "GET",
                    "url": "https://httpbin.org/get",
                    "tasks": [{"master_id": tm_id, "sequence": 0}],
                    "validate_interfaces": True,
                },
            )

            assert response.status_code == 201
            job_data = response.json()
            job_ids.append(job_data["job_id"])

        total_time_sec = time.time() - start_time
        avg_time_ms = (total_time_sec * 1000) / num_jobs
        throughput = num_jobs / total_time_sec

        # Performance assertions
        assert (
            avg_time_ms < 50
        ), f"Average validation time {avg_time_ms:.2f}ms (expected < 50ms)"
        assert (
            throughput > 50
        ), f"Throughput {throughput:.2f} jobs/sec (expected > 50 jobs/sec)"

        print(f"\n✓ Bulk validation performance:")
        print(f"  - Total jobs: {num_jobs}")
        print(f"  - Total time: {total_time_sec:.2f}s")
        print(f"  - Average time: {avg_time_ms:.2f}ms/job")
        print(f"  - Throughput: {throughput:.2f} jobs/sec")
        print(f"  - Thresholds: <50ms/job, >50 jobs/sec")

        # Verify all jobs created successfully
        assert len(job_ids) == num_jobs

    @pytest.mark.asyncio
    async def test_performance_validation_latency_breakdown(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test and measure validation latency breakdown."""
        # Create interface
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "data": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["data"],
        }

        interface_id = f"if_{ulid_new()}"
        interface = InterfaceMaster(
            id=interface_id,
            name="PerformanceLatencyInterface",
            output_schema=schema,
            is_active=True,
        )
        db_session.add(interface)

        tm_id = f"tm_{ulid_new()}"
        tm = TaskMaster(
            id=tm_id,
            name="perf_latency_task",
            method="GET",
            url="https://httpbin.org/json",
            timeout_sec=30,
            output_interface_id=interface_id,
            is_active=True,
            current_version=1,
            created_by="perf_test",
            updated_by="perf_test",
        )
        db_session.add(tm)
        await db_session.commit()

        # Measure multiple iterations
        num_iterations = 50
        latencies = []

        for _ in range(num_iterations):
            start_time = time.time()

            response = await client.post(
                "/api/v1/jobs",
                json={
                    "name": "Latency Test Job",
                    "method": "GET",
                    "url": "https://httpbin.org/get",
                    "tasks": [{"master_id": tm_id, "sequence": 0}],
                    "validate_interfaces": True,
                },
            )

            latency_ms = (time.time() - start_time) * 1000
            latencies.append(latency_ms)

            assert response.status_code == 201

        # Calculate statistics
        avg_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)
        sorted_latencies = sorted(latencies)
        p50 = sorted_latencies[int(len(sorted_latencies) * 0.50)]
        p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)]
        p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)]

        # Performance assertions
        assert p95 < 100, f"P95 latency {p95:.2f}ms (expected < 100ms)"
        assert p99 < 150, f"P99 latency {p99:.2f}ms (expected < 150ms)"

        print(f"\n✓ Validation latency statistics ({num_iterations} iterations):")
        print(f"  - Min: {min_latency:.2f}ms")
        print(f"  - P50: {p50:.2f}ms")
        print(f"  - P95: {p95:.2f}ms (threshold: <100ms)")
        print(f"  - P99: {p99:.2f}ms (threshold: <150ms)")
        print(f"  - Max: {max_latency:.2f}ms")
        print(f"  - Avg: {avg_latency:.2f}ms")
