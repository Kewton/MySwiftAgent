"""Seed missing interfaces and associate with TaskMasters.

This script:
1. Creates missing InterfaceMaster records for common interface patterns
2. Associates TaskMasters with appropriate interfaces
3. Verifies all required TaskMasters have interface associations

Run: uv run python -m scripts.seed_missing_interfaces
"""

import asyncio
from datetime import datetime

from sqlalchemy import select
from ulid import new as ulid_new

from app.core.database import AsyncSessionLocal
from app.models.interface_master import InterfaceMaster
from app.models.task_master import TaskMaster

# Interface definitions based on implementation plan
INTERFACES_TO_CREATE = [
    {
        "name": "AnalysisResultInterface",
        "description": "Interface for info_analyzer input/output",
        "input_schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "search_results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "url": {"type": "string"},
                            "snippet": {"type": "string"},
                        },
                    },
                }
            },
            "required": ["search_results"],
        },
        "output_schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "analysis": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "key_points": {"type": "array", "items": {"type": "string"}},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "required": ["summary", "key_points"],
                }
            },
            "required": ["analysis"],
        },
    },
    {
        "name": "EmailContentInterface",
        "description": "Interface for email_sender input",
        "input_schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "to": {"type": "string", "format": "email"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
                "cc": {"type": "array", "items": {"type": "string", "format": "email"}},
                "bcc": {
                    "type": "array",
                    "items": {"type": "string", "format": "email"},
                },
                "attachments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string"},
                            "content_type": {"type": "string"},
                            "data": {"type": "string"},
                        },
                        "required": ["filename", "data"],
                    },
                },
            },
            "required": ["to", "subject", "body"],
        },
        "output_schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "message_id": {"type": "string"},
                "sent_at": {"type": "string", "format": "date-time"},
                "status": {"type": "string", "enum": ["sent", "failed"]},
            },
            "required": ["message_id", "sent_at", "status"],
        },
    },
]

# TaskMaster to Interface associations
TASK_MASTER_ASSOCIATIONS = {
    "info_analyzer": {
        "input": "AnalysisResultInterface",
        "output": "AnalysisResultInterface",
    },
    "email_sender": {
        "input": "EmailContentInterface",
        "output": "EmailContentInterface",
    },
    "report_generator": {
        "input": "AnalysisResultInterface",
        "output": "ReportInterface",  # Assumes ReportInterface already exists
    },
}


async def seed_missing_interfaces() -> None:
    """Register missing interfaces and associate with TaskMasters."""
    async with AsyncSessionLocal() as db:
        print("🚀 Starting interface seeding process...")
        print(f"⏰ Timestamp: {datetime.now().isoformat()}\n")

        # Step 1: Check existing interfaces
        print("📋 Step 1: Checking existing interfaces...")
        existing_interfaces = {}
        for interface_def in INTERFACES_TO_CREATE:
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
                existing_interfaces[interface_def["name"]] = existing.id
            else:
                print(f"  ❌ {interface_def['name']} not found - will create")

        # Check for ReportInterface (required for report_generator)
        result = await db.scalars(
            select(InterfaceMaster).where(InterfaceMaster.name == "ReportInterface")
        )
        report_interface = result.first()
        if report_interface:
            print(f"  ✅ ReportInterface already exists (ID: {report_interface.id})")
            existing_interfaces["ReportInterface"] = report_interface.id
        else:
            print(
                "  ⚠️  WARNING: ReportInterface not found - report_generator association will fail"
            )

        print()

        # Step 2: Create missing interfaces
        print("📝 Step 2: Creating missing interfaces...")
        created_count = 0
        for interface_def in INTERFACES_TO_CREATE:
            if interface_def["name"] in existing_interfaces:
                print(f"  ⏭️  Skipping {interface_def['name']} (already exists)")
                continue

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
            existing_interfaces[interface_def["name"]] = interface_id
            print(f"  ✨ Created {interface_def['name']} (ID: {interface_id})")
            created_count += 1

        if created_count > 0:
            await db.commit()
            print(f"\n✅ Created {created_count} new interface(s)")
        else:
            print("\n⏭️  No new interfaces created")

        print()

        # Step 3: Associate TaskMasters with interfaces
        print("🔗 Step 3: Associating TaskMasters with interfaces...")
        association_count = 0
        for task_name, interface_refs in TASK_MASTER_ASSOCIATIONS.items():
            # Find TaskMaster by name
            result = await db.scalars(
                select(TaskMaster).where(TaskMaster.name == task_name)
            )
            task_master_result = result.first()
            if not task_master_result:
                print(f"  ⚠️  WARNING: TaskMaster '{task_name}' not found - skipping")
                continue

            # Type narrowing for MyPy
            task_master: TaskMaster = task_master_result  # type: ignore[assignment]
            print(f"\n  📌 Processing TaskMaster: {task_name} (ID: {task_master.id})")

            # Update input_interface_id
            input_interface_name = interface_refs.get("input")
            if input_interface_name:
                if input_interface_name in existing_interfaces:
                    input_id = existing_interfaces[input_interface_name]
                    if task_master.input_interface_id != input_id:
                        task_master.input_interface_id = input_id
                        print(
                            f"    ✅ Set input_interface_id = {input_id} ({input_interface_name})"
                        )
                        association_count += 1
                    else:
                        print(f"    ⏭️  input_interface_id already set to {input_id}")
                else:
                    print(
                        f"    ⚠️  WARNING: Interface '{input_interface_name}' not found"
                    )

            # Update output_interface_id
            output_interface_name = interface_refs.get("output")
            if output_interface_name:
                if output_interface_name in existing_interfaces:
                    output_id = existing_interfaces[output_interface_name]
                    if task_master.output_interface_id != output_id:
                        task_master.output_interface_id = output_id
                        print(
                            f"    ✅ Set output_interface_id = {output_id} ({output_interface_name})"
                        )
                        association_count += 1
                    else:
                        print(f"    ⏭️  output_interface_id already set to {output_id}")
                else:
                    print(
                        f"    ⚠️  WARNING: Interface '{output_interface_name}' not found"
                    )

        if association_count > 0:
            await db.commit()
            print(f"\n✅ Created {association_count} new association(s)")
        else:
            print("\n⏭️  No new associations created")

        print()

        # Step 4: Verify all TaskMasters have interfaces
        print("🔍 Step 4: Verifying TaskMaster interface associations...")
        task_masters_result = await db.scalars(
            select(TaskMaster).where(TaskMaster.is_active)
        )
        all_masters: list[TaskMaster] = list(task_masters_result.all())

        missing_associations = []
        for master in all_masters:
            has_input = master.input_interface_id is not None
            has_output = master.output_interface_id is not None
            if not (has_input or has_output):
                missing_associations.append(master.name)

        if missing_associations:
            print(
                f"\n⚠️  WARNING: {len(missing_associations)} TaskMaster(s) still missing interface associations:"
            )
            for name in missing_associations:
                print(f"    - {name}")
        else:
            print("\n✅ All active TaskMasters have interface associations!")

        print("\n" + "=" * 70)
        print("✅ Interface seeding process completed successfully!")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(seed_missing_interfaces())
