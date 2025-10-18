"""Seed test data for Phase 1: Job Execution History UI.

This script creates:
1. InterfaceMasters for company research workflow
2. TaskMasters for various workflow steps
3. JobMaster for company research workflow
4. Jobs with various statuses (queued, running, succeeded, failed, canceled)
5. Tasks within each Job

Run: uv run python -m scripts.seed_phase1_test_data
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import select
from ulid import new as ulid_new

from app.core.database import AsyncSessionLocal
from app.models.interface_master import InterfaceMaster
from app.models.job import Job, JobStatus
from app.models.job_master import JobMaster
from app.models.task import Task, TaskStatus
from app.models.task_master import TaskMaster

# Interface definitions for company research workflow
INTERFACES = [
    {
        "name": "CompanySearchInterface",
        "description": "Interface for company search input/output",
        "input_schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "company_name": {"type": "string"},
                "country": {"type": "string"},
                "industry": {"type": "string"},
            },
            "required": ["company_name"],
        },
        "output_schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "company_id": {"type": "string"},
                "company_name": {"type": "string"},
                "website": {"type": "string"},
                "founded_year": {"type": "integer"},
                "employee_count": {"type": "integer"},
            },
            "required": ["company_id", "company_name"],
        },
    },
    {
        "name": "CompanyAnalysisInterface",
        "description": "Interface for company analysis",
        "input_schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "company_id": {"type": "string"},
                "company_name": {"type": "string"},
                "website": {"type": "string"},
            },
            "required": ["company_id"],
        },
        "output_schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "company_id": {"type": "string"},
                "analysis": {
                    "type": "object",
                    "properties": {
                        "strengths": {"type": "array", "items": {"type": "string"}},
                        "weaknesses": {"type": "array", "items": {"type": "string"}},
                        "market_position": {"type": "string"},
                        "score": {"type": "number", "minimum": 0, "maximum": 100},
                    },
                },
            },
            "required": ["company_id", "analysis"],
        },
    },
    {
        "name": "ReportGenerationInterface",
        "description": "Interface for report generation",
        "input_schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "company_id": {"type": "string"},
                "analysis": {"type": "object"},
            },
            "required": ["company_id", "analysis"],
        },
        "output_schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "report_url": {"type": "string"},
                "report_id": {"type": "string"},
                "generated_at": {"type": "string", "format": "date-time"},
            },
            "required": ["report_url", "report_id"],
        },
    },
]

# TaskMaster definitions
TASK_MASTERS = [
    {
        "name": "company_search",
        "description": "Search for company information",
        "method": "POST",
        "url": "https://api.example.com/companies/search",
        "input_interface": "CompanySearchInterface",
        "output_interface": "CompanySearchInterface",
    },
    {
        "name": "company_analysis",
        "description": "Analyze company data",
        "method": "POST",
        "url": "https://api.example.com/analysis/company",
        "input_interface": "CompanyAnalysisInterface",
        "output_interface": "CompanyAnalysisInterface",
    },
    {
        "name": "report_generation",
        "description": "Generate analysis report",
        "method": "POST",
        "url": "https://api.example.com/reports/generate",
        "input_interface": "ReportGenerationInterface",
        "output_interface": "ReportGenerationInterface",
    },
    {
        "name": "email_notification",
        "description": "Send email notification",
        "method": "POST",
        "url": "https://api.example.com/notifications/email",
        "input_interface": "ReportGenerationInterface",
        "output_interface": None,  # No output interface
    },
]

# JobMaster definition
JOB_MASTER = {
    "name": "Company Research Workflow",
    "description": "Comprehensive company research and analysis workflow",
    "method": "POST",
    "url": "https://api.example.com/workflows/company-research",
}


async def seed_phase1_test_data() -> None:
    """Seed test data for Phase 1 Job Execution History UI."""
    async with AsyncSessionLocal() as db:
        print("=" * 80)
        print("🚀 Starting Phase 1 Test Data Seeding")
        print("=" * 80)
        print(f"⏰ Timestamp: {datetime.now(UTC).isoformat()}\n")

        # Step 1: Create InterfaceMasters
        print("📋 Step 1: Creating InterfaceMasters...")
        interface_ids = {}
        for interface_def in INTERFACES:
            # Check if interface already exists
            result = await db.scalars(
                select(InterfaceMaster).where(
                    InterfaceMaster.name == interface_def["name"]
                )
            )
            existing = result.first()

            if existing:
                print(
                    f"  ✅ {interface_def['name']} already exists (ID: {existing.id})"
                )
                interface_ids[interface_def["name"]] = existing.id
            else:
                interface_id = f"if_{ulid_new()}"
                new_interface = InterfaceMaster(
                    id=interface_id,
                    name=interface_def["name"],
                    description=interface_def["description"],
                    input_schema=interface_def["input_schema"],
                    output_schema=interface_def["output_schema"],
                    is_active=True,
                )
                db.add(new_interface)
                interface_ids[interface_def["name"]] = interface_id
                print(f"  ✨ Created {interface_def['name']} (ID: {interface_id})")

        await db.commit()
        print()

        # Step 2: Create TaskMasters
        print("📝 Step 2: Creating TaskMasters...")
        task_master_ids: dict[str, str] = {}
        for task_def_raw in TASK_MASTERS:
            task_def = cast(dict[str, Any], task_def_raw)
            # Check if task master already exists
            task_master_result = await db.scalars(
                select(TaskMaster).where(TaskMaster.name == task_def["name"])
            )
            existing_task_master = task_master_result.first()

            if existing_task_master:
                print(
                    f"  ✅ {task_def['name']} already exists (ID: {existing_task_master.id})"
                )
                task_master_ids[task_def["name"]] = existing_task_master.id
            else:
                task_id = f"tm_{ulid_new()}"
                new_task_master = TaskMaster(
                    id=task_id,
                    name=task_def["name"],
                    description=task_def["description"],
                    method=task_def["method"],
                    url=task_def["url"],
                    input_interface_id=interface_ids.get(task_def["input_interface"]),
                    output_interface_id=interface_ids.get(task_def["output_interface"])
                    if task_def["output_interface"]
                    else None,
                    is_active=True,
                    current_version=1,
                )
                db.add(new_task_master)
                task_master_ids[task_def["name"]] = task_id
                print(f"  ✨ Created {task_def['name']} (ID: {task_id})")

        await db.commit()
        print()

        # Step 3: Create JobMaster
        print("🎯 Step 3: Creating JobMaster...")
        result = await db.scalars(
            select(JobMaster).where(JobMaster.name == JOB_MASTER["name"])
        )
        job_master = result.first()

        if job_master:
            print(f"  ✅ {JOB_MASTER['name']} already exists (ID: {job_master.id})")
            job_master_id = job_master.id
        else:
            job_master_id = f"jm_{ulid_new()}"
            new_job_master = JobMaster(
                id=job_master_id,
                name=JOB_MASTER["name"],
                description=JOB_MASTER["description"],
                method=JOB_MASTER["method"],
                url=JOB_MASTER["url"],
                is_active=True,
                current_version=1,
            )
            db.add(new_job_master)
            print(f"  ✨ Created {JOB_MASTER['name']} (ID: {job_master_id})")

        await db.commit()
        print()

        # Step 4: Create Jobs with various statuses
        print("💼 Step 4: Creating Jobs with various statuses...")
        job_scenarios = [
            {
                "name": "Toyota Corporation Research",
                "status": JobStatus.SUCCEEDED,
                "created_offset": timedelta(hours=5),
                "started_offset": timedelta(hours=4, minutes=55),
                "finished_offset": timedelta(hours=4, minutes=50),
                "tasks": [
                    {
                        "master": "company_search",
                        "status": TaskStatus.SUCCEEDED,
                        "input": {"company_name": "Toyota", "country": "Japan"},
                        "output": {
                            "company_id": "toyota_001",
                            "company_name": "Toyota Motor Corporation",
                            "website": "https://www.toyota.com",
                            "founded_year": 1937,
                            "employee_count": 370000,
                        },
                        "duration_ms": 2500,
                    },
                    {
                        "master": "company_analysis",
                        "status": TaskStatus.SUCCEEDED,
                        "input": {
                            "company_id": "toyota_001",
                            "company_name": "Toyota Motor Corporation",
                        },
                        "output": {
                            "company_id": "toyota_001",
                            "analysis": {
                                "strengths": [
                                    "Global market leader",
                                    "Strong brand",
                                ],
                                "weaknesses": ["EV transition lag"],
                                "market_position": "Leader",
                                "score": 85,
                            },
                        },
                        "duration_ms": 5200,
                    },
                    {
                        "master": "report_generation",
                        "status": TaskStatus.SUCCEEDED,
                        "input": {
                            "company_id": "toyota_001",
                            "analysis": {"score": 85},
                        },
                        "output": {
                            "report_url": "https://reports.example.com/toyota_001.pdf",
                            "report_id": "rpt_toyota_001",
                            "generated_at": datetime.now(UTC).isoformat(),
                        },
                        "duration_ms": 3800,
                    },
                ],
            },
            {
                "name": "Tesla Inc Research",
                "status": JobStatus.FAILED,
                "created_offset": timedelta(hours=3),
                "started_offset": timedelta(hours=2, minutes=55),
                "finished_offset": timedelta(hours=2, minutes=52),
                "tasks": [
                    {
                        "master": "company_search",
                        "status": TaskStatus.SUCCEEDED,
                        "input": {"company_name": "Tesla", "country": "USA"},
                        "output": {
                            "company_id": "tesla_001",
                            "company_name": "Tesla Inc",
                            "website": "https://www.tesla.com",
                        },
                        "duration_ms": 2100,
                    },
                    {
                        "master": "company_analysis",
                        "status": TaskStatus.FAILED,
                        "input": {"company_id": "tesla_001"},
                        "output": None,
                        "error": "Analysis service timeout after 30s",
                        "duration_ms": 30000,
                    },
                ],
            },
            {
                "name": "Microsoft Corporation Research",
                "status": JobStatus.RUNNING,
                "created_offset": timedelta(minutes=30),
                "started_offset": timedelta(minutes=25),
                "finished_offset": None,
                "tasks": [
                    {
                        "master": "company_search",
                        "status": TaskStatus.SUCCEEDED,
                        "input": {"company_name": "Microsoft", "country": "USA"},
                        "output": {
                            "company_id": "msft_001",
                            "company_name": "Microsoft Corporation",
                        },
                        "duration_ms": 1800,
                    },
                    {
                        "master": "company_analysis",
                        "status": TaskStatus.RUNNING,
                        "input": {"company_id": "msft_001"},
                        "output": None,
                        "duration_ms": None,
                    },
                ],
            },
            {
                "name": "Apple Inc Research",
                "status": JobStatus.QUEUED,
                "created_offset": timedelta(minutes=10),
                "started_offset": None,
                "finished_offset": None,
                "tasks": [],
            },
            {
                "name": "Samsung Research (Canceled)",
                "status": JobStatus.CANCELED,
                "created_offset": timedelta(hours=1),
                "started_offset": timedelta(minutes=58),
                "finished_offset": timedelta(minutes=57),
                "tasks": [
                    {
                        "master": "company_search",
                        "status": TaskStatus.SUCCEEDED,
                        "input": {"company_name": "Samsung"},
                        "output": {"company_id": "samsung_001"},
                        "duration_ms": 2000,
                    },
                ],
            },
        ]

        created_jobs = 0
        for scenario_raw in job_scenarios:
            scenario = cast(dict[str, Any], scenario_raw)
            now = datetime.now(UTC)
            created_at = now - cast(timedelta, scenario["created_offset"])
            started_at = (
                now - cast(timedelta, scenario["started_offset"])
                if scenario["started_offset"]
                else None
            )
            finished_at = (
                now - cast(timedelta, scenario["finished_offset"])
                if scenario["finished_offset"]
                else None
            )

            job_id = f"j_{ulid_new()}"
            new_job = Job(
                id=job_id,
                name=scenario["name"],
                master_id=job_master_id,
                master_version=1,
                method="POST",
                url="https://api.example.com/workflows/company-research",
                status=scenario["status"],
                created_at=created_at,
                started_at=started_at,
                finished_at=finished_at,
                next_attempt_at=created_at,
            )
            db.add(new_job)
            print(
                f"  ✨ Created Job: {scenario['name']} (Status: {scenario['status']})"
            )

            # Create tasks for the job
            for order, task_scenario_raw in enumerate(scenario["tasks"]):
                task_scenario = cast(dict[str, Any], task_scenario_raw)
                task_id = f"t_{ulid_new()}"
                new_task = Task(
                    id=task_id,
                    job_id=job_id,
                    master_id=task_master_ids[task_scenario["master"]],
                    master_version=1,
                    order=order,
                    status=task_scenario["status"],
                    input_data=task_scenario["input"],
                    output_data=task_scenario["output"],
                    error=task_scenario.get("error"),
                    duration_ms=task_scenario.get("duration_ms"),
                    attempt=0,
                    created_at=created_at,
                    started_at=started_at,
                    finished_at=finished_at
                    if task_scenario["status"] != TaskStatus.RUNNING
                    else None,
                )
                db.add(new_task)
                print(
                    f"    → Task {order}: {task_scenario['master']} (Status: {task_scenario['status']})"
                )

            created_jobs += 1

        await db.commit()
        print(f"\n  ✅ Created {created_jobs} Jobs with Tasks")
        print()

        print("=" * 80)
        print("✅ Phase 1 Test Data Seeding Completed Successfully!")
        print("=" * 80)
        print("\n📊 Summary:")
        print(f"  - InterfaceMasters: {len(INTERFACES)}")
        print(f"  - TaskMasters: {len(TASK_MASTERS)}")
        print("  - JobMaster: 1")
        print(f"  - Jobs: {created_jobs}")
        print("\n🎯 Next Steps:")
        print("  1. Access CommonUI: http://localhost:8600")
        print("  2. Navigate to: 🚀 Job Execution")
        print(f"  3. Select JobMaster: {JOB_MASTER['name']}")
        print("  4. Verify Job list and details display correctly")
        print()


if __name__ == "__main__":
    asyncio.run(seed_phase1_test_data())
