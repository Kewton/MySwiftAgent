"""InterfaceDesignWorkflow package for Job Generator V2.

This package implements Phase C of Issue #342:
- SchemaGeneratorSubWorkflow: Generate JSON Schema from task definitions
- CompatibilityCheckerSubWorkflow: Check GraphAI compatibility
- SchemaEnricherSubWorkflow: Add derived_fields to schemas
- InterfaceDesignWorkflow: Main workflow orchestrating sub-workflows

The workflow follows the pattern:
1. Generate JSON Schema for each task's I/O
2. Check compatibility between dependent tasks
3. Enrich schemas with derived_fields for downstream tasks
4. Return InterfaceDesignOutput with appropriate status
"""

from .compatibility import CompatibilityCheckerSubWorkflow, validate_interface_response
from .enricher import SchemaEnricherSubWorkflow
from .schema_generator import (
    SchemaGeneratorSubWorkflow,
    normalize_json_schema_properties,
)
from .workflow import InterfaceDesignWorkflow

__all__ = [
    "SchemaGeneratorSubWorkflow",
    "CompatibilityCheckerSubWorkflow",
    "SchemaEnricherSubWorkflow",
    "InterfaceDesignWorkflow",
    "normalize_json_schema_properties",
    "validate_interface_response",
]
