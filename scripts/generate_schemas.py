#!/usr/bin/env python3
"""Generate TypeScript and Pydantic schemas from JSON Schema.

Issue #357: JSON Schema Single Source of Truth.

This script generates language-specific schema definitions from the canonical
JSON Schema definition, ensuring consistency across the codebase.

Generated files:
- graphAiServer/src/engine/schemas/generated/taskflow.d.ts (TypeScript types)
- expertAgent/.../schemas/generated/taskflow_types.py (Pydantic models)

Usage:
    python scripts/generate_schemas.py

Requirements:
    - Node.js with npx (for json-schema-to-typescript)
    - Python with datamodel-code-generator
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

# Paths relative to project root
PROJECT_ROOT = Path(__file__).parent.parent
SCHEMA_DIR = PROJECT_ROOT / "shared" / "schemas" / "taskflow" / "v1"
SCHEMA_FILE = SCHEMA_DIR / "workflow.schema.json"

GRAPHAI_OUTPUT_DIR = PROJECT_ROOT / "graphAiServer" / "src" / "engine" / "schemas" / "generated"
EXPERT_OUTPUT_DIR = (
    PROJECT_ROOT
    / "expertAgent"
    / "aiagent"
    / "langgraph"
    / "jobGeneratorV2"
    / "workflows"
    / "workflow_gen"
    / "schemas"
    / "generated"
)


def validate_schema() -> dict[str, Any]:
    """Validate the JSON Schema file.

    Returns:
        The parsed schema dict.

    Raises:
        FileNotFoundError: If schema file does not exist.
        ValueError: If schema is invalid.
    """
    if not SCHEMA_FILE.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_FILE}")

    content = SCHEMA_FILE.read_text(encoding="utf-8")
    schema: dict[str, Any] = json.loads(content)

    # Basic validation
    if "$schema" not in schema:
        raise ValueError("Schema must have $schema property")
    if "properties" not in schema:
        raise ValueError("Schema must have properties")
    if "workflow_name" not in schema.get("properties", {}):
        raise ValueError("Schema must define workflow_name property")

    # Validate using jsonschema if available
    try:
        from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

        Draft202012Validator.check_schema(schema)
        print("Schema validation passed (Draft 2020-12)")
    except ImportError:
        print("Warning: jsonschema not installed, skipping schema validation")

    return schema


def generate_typescript() -> bool:
    """Generate TypeScript types from JSON Schema.

    Uses json-schema-to-typescript npm package.

    Returns:
        True if generation succeeded, False otherwise.
    """
    # Ensure output directory exists
    GRAPHAI_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = GRAPHAI_OUTPUT_DIR / "taskflow.d.ts"

    try:
        result = subprocess.run(
            [
                "npx",
                "json-schema-to-typescript",
                str(SCHEMA_FILE),
                "-o",
                str(output_file),
                "--bannerComment",
                "/* Auto-generated from JSON Schema. DO NOT EDIT. */\n/* Source: shared/schemas/taskflow/v1/workflow.schema.json */",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(PROJECT_ROOT),
        )

        if result.returncode != 0:
            print(f"TypeScript generation failed: {result.stderr}")
            return False

        print(f"Generated: {output_file}")
        return True

    except FileNotFoundError:
        print("Error: npx not found. Please install Node.js.")
        return False
    except subprocess.TimeoutExpired:
        print("Error: TypeScript generation timed out.")
        return False


def generate_python() -> bool:
    """Generate Pydantic models from JSON Schema.

    Uses datamodel-code-generator package.

    Returns:
        True if generation succeeded, False otherwise.
    """
    # Ensure output directory exists
    EXPERT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = EXPERT_OUTPUT_DIR / "taskflow_types.py"
    init_file = EXPERT_OUTPUT_DIR / "__init__.py"

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "datamodel_code_generator",
                "--input",
                str(SCHEMA_FILE),
                "--output",
                str(output_file),
                "--input-file-type",
                "jsonschema",
                "--output-model-type",
                "pydantic_v2.BaseModel",
                "--target-python-version",
                "3.11",
                "--use-standard-collections",
                "--use-union-operator",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(PROJECT_ROOT),
        )

        if result.returncode != 0:
            print(f"Python generation failed: {result.stderr}")
            return False

        # Add auto-generated header
        content = output_file.read_text(encoding="utf-8")
        header = (
            '"""Auto-generated from JSON Schema. DO NOT EDIT.\n\n'
            "Source: shared/schemas/taskflow/v1/workflow.schema.json\n"
            "Issue #357: JSON Schema Single Source of Truth\n"
            '"""\n\n'
        )
        if not content.startswith('"""Auto-generated'):
            output_file.write_text(header + content, encoding="utf-8")

        # Create __init__.py if it doesn't exist
        if not init_file.exists():
            init_file.write_text(
                '"""Generated schema types package."""\n\nfrom .taskflow_types import *  # noqa: F401, F403\n',
                encoding="utf-8",
            )

        print(f"Generated: {output_file}")
        return True

    except FileNotFoundError:
        print(
            "Error: datamodel-code-generator not found. Install with: pip install datamodel-code-generator"
        )
        return False
    except subprocess.TimeoutExpired:
        print("Error: Python generation timed out.")
        return False


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    print("=== JSON Schema to Code Generator ===")
    print(f"Schema: {SCHEMA_FILE}")
    print()

    # Step 1: Validate schema
    print("Step 1: Validating JSON Schema...")
    try:
        validate_schema()
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        print(f"Error: {e}")
        return 1

    print()

    # Step 2: Generate TypeScript
    print("Step 2: Generating TypeScript types...")
    ts_success = generate_typescript()

    print()

    # Step 3: Generate Python
    print("Step 3: Generating Pydantic models...")
    py_success = generate_python()

    print()

    # Summary
    print("=== Generation Summary ===")
    print(f"TypeScript: {'Success' if ts_success else 'Failed'}")
    print(f"Python: {'Success' if py_success else 'Failed'}")

    if ts_success and py_success:
        print("\nSchema generation completed successfully!")
        return 0
    else:
        print("\nSome generations failed. See errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
