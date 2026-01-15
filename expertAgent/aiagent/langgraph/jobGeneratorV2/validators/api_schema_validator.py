"""APISchemaValidator for validating API parameters in workflows.

Issue #344: API Schema validation for workflow generation.

This module validates:
- API parameter names against known schemas
- Required parameters presence
- Typo detection with suggestions

Security:
- Uses yaml.safe_load() for YAML parsing
- Path traversal protection for schema file paths
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from aiagent.langgraph.jobGeneratorV2.validators import (
    ValidationError,
    ValidationErrorCode,
    WorkflowValidator,
)

# Issue #344 Task 1.3: Parameter aliases for typo detection
# Maps common typos to correct parameter names per API
PARAMETER_ALIASES: dict[str, dict[str, str]] = {
    "/utility/google_search": {
        "query": "queries",  # Common typo: singular vs plural
        "num_results": "num",  # Common typo: verbose name
        "count": "num",  # Alternative name
        "search_query": "queries",  # Verbose name
        "q": "queries",  # Short name from other APIs
    },
    "/utility/fetch_web_content": {
        "target_url": "url",  # Verbose name
        "page_url": "url",  # Alternative name
        "upload": "upload_to_drive",  # Short name
    },
    "/utility/json_stringify": {
        "input": "data",  # Alternative name
        "json_data": "data",  # Verbose name
        "value": "data",  # Alternative name
    },
    "/utility/extract_article_urls": {
        "results": "search_results",  # Short name
        "max": "max_urls",  # Short name
        "limit": "max_urls",  # Alternative name
    },
    "/aiagent/utility/jsonoutput": {
        "prompt": "user_input",  # Alternative name
        "input": "user_input",  # Alternative name
        "model": "model_name",  # Short name
        "json": "force_json",  # Short name
    },
    "/utility/gmail/search": {
        "max": "max_results",  # Short name
        "limit": "max_results",  # Alternative name
    },
}

# Default path to API specs YAML
DEFAULT_SPECS_PATH = Path(__file__).parent.parent / "schemas" / "available_apis.yaml"


class APISchemaValidator(WorkflowValidator):
    """Validator for API parameter correctness in workflows.

    This validator:
    1. Extracts fetchAgent nodes from workflows
    2. Identifies API endpoints from URLs
    3. Validates body parameters against known schemas
    4. Suggests corrections for typos
    """

    def __init__(self, specs_path: str | Path | None = None):
        """Initialize with API specifications.

        Args:
            specs_path: Path to YAML file with API specs.
                       Defaults to schemas/available_apis.yaml
        """
        self.specs_path = Path(specs_path) if specs_path else DEFAULT_SPECS_PATH
        self._schemas = self._load_schemas()

    def _load_schemas(self) -> dict[str, dict[str, Any]]:
        """Load API schemas from YAML or use defaults.

        Returns:
            Dictionary mapping API paths to their schemas
        """
        # Security: Validate path to prevent traversal
        if self.specs_path.exists():
            try:
                resolved = self.specs_path.resolve()
                expected_parent = Path(__file__).parent.parent.resolve()
                # Allow paths within the jobGeneratorV2 directory
                if str(resolved).startswith(str(expected_parent)):
                    with open(resolved, "r", encoding="utf-8") as f:
                        # Security: Use safe_load to prevent arbitrary code execution
                        data = yaml.safe_load(f)
                        return self._normalize_schemas(data)
            except (yaml.YAMLError, OSError):
                pass

        return self._get_default_schemas()

    def _normalize_schemas(self, data: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Normalize YAML data to consistent schema format.

        Args:
            data: Raw YAML data

        Returns:
            Normalized schemas dictionary
        """
        schemas: dict[str, dict[str, Any]] = {}

        apis = data.get("apis", {})

        for path, spec in apis.items():
            if isinstance(spec, dict):
                # Convert request_schema to parameters format
                request_schema = spec.get("request_schema", {})
                parameters = {}

                for param_name, param_spec in request_schema.items():
                    if isinstance(param_spec, dict):
                        parameters[param_name] = {
                            "type": param_spec.get("type", "any"),
                            "required": param_spec.get("required", False),
                            "description": param_spec.get("description", ""),
                        }
                    else:
                        parameters[param_name] = {"type": str(param_spec)}

                schemas[path] = {
                    "path": path,
                    "parameters": parameters,
                }

        return schemas

    def _get_default_schemas(self) -> dict[str, dict[str, Any]]:
        """Get default API schemas.

        Returns:
            Dictionary with hardcoded schemas for utility endpoints
        """
        return {
            "/utility/google_search": {
                "path": "/utility/google_search",
                "parameters": {
                    "queries": {
                        "type": "array",
                        "required": True,
                        "description": "Search queries array",
                    },
                    "num": {
                        "type": "integer",
                        "required": False,
                        "description": "Number of results per query",
                    },
                },
            },
            "/utility/fetch_web_content": {
                "path": "/utility/fetch_web_content",
                "parameters": {
                    "url": {
                        "type": "string",
                        "required": True,
                        "description": "URL to fetch content from",
                    },
                    "upload_to_drive": {
                        "type": "boolean",
                        "required": False,
                        "description": "Upload to Google Drive",
                    },
                },
            },
            "/utility/json_stringify": {
                "path": "/utility/json_stringify",
                "parameters": {
                    "data": {
                        "type": "any",
                        "required": True,
                        "description": "Data to stringify",
                    },
                },
            },
            "/utility/extract_article_urls": {
                "path": "/utility/extract_article_urls",
                "parameters": {
                    "search_results": {
                        "type": "array",
                        "required": True,
                        "description": "Google search results array",
                    },
                    "max_urls": {
                        "type": "integer",
                        "required": False,
                        "description": "Maximum URLs to extract",
                    },
                },
            },
            "/aiagent/utility/jsonoutput": {
                "path": "/aiagent/utility/jsonoutput",
                "parameters": {
                    "user_input": {
                        "type": "string",
                        "required": True,
                        "description": "Prompt string",
                    },
                    "model_name": {
                        "type": "string",
                        "required": False,
                        "description": "LLM model name",
                    },
                    "force_json": {
                        "type": "boolean",
                        "required": False,
                        "description": "Force JSON output",
                    },
                },
            },
            "/utility/gmail/search": {
                "path": "/utility/gmail/search",
                "parameters": {
                    "query": {
                        "type": "string",
                        "required": True,
                        "description": "Gmail search query",
                    },
                    "max_results": {
                        "type": "integer",
                        "required": False,
                        "description": "Maximum results",
                    },
                },
            },
        }

    def get_schema(self, api_path: str) -> dict[str, Any] | None:
        """Get schema for an API path.

        Args:
            api_path: API path like "/utility/google_search"

        Returns:
            Schema dictionary or None if not found
        """
        # Try exact match
        if api_path in self._schemas:
            return self._schemas[api_path]

        # Try with/without leading slash
        alt_path = api_path.lstrip("/") if api_path.startswith("/") else f"/{api_path}"
        if alt_path in self._schemas:
            return self._schemas[alt_path]

        return None

    def validate(self, workflow: dict[str, Any]) -> list[ValidationError]:
        """Validate API parameters in workflow.

        Args:
            workflow: Workflow dictionary to validate

        Returns:
            List of ValidationError objects
        """
        errors: list[ValidationError] = []
        nodes = workflow.get("nodes", {})

        for node_name, node_def in nodes.items():
            if node_name == "source":
                continue

            if not isinstance(node_def, dict):
                continue

            agent = node_def.get("agent", "")

            # Only validate fetchAgent nodes
            if agent != "fetchAgent":
                continue

            inputs = node_def.get("inputs", {})
            url = inputs.get("url", "")

            # Extract API path from URL
            api_path = self._extract_api_path(url)
            if not api_path:
                continue

            # Get schema for this API
            schema = self.get_schema(api_path)
            if not schema:
                continue

            # Validate body parameters
            body = inputs.get("body", {})
            if not isinstance(body, dict):
                body = {}

            node_errors = self._validate_parameters(
                body,
                schema,
                api_path,
                f"nodes.{node_name}.inputs.body",
            )
            errors.extend(node_errors)

        return errors

    def _extract_api_path(self, url: str) -> str | None:
        """Extract API path from URL.

        Args:
            url: URL string

        Returns:
            API path or None if not an expertAgent API
        """
        if not url:
            return None

        # Check for expertAgent API patterns
        patterns = [
            r"\$\{EXPERTAGENT_BASE_URL\}/aiagent-api/v1(/[^\s]+)",
            r"http://localhost:8004/aiagent-api/v1(/[^\s]+)",
            r"/aiagent-api/v1(/[^\s]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def _validate_parameters(
        self,
        body: dict[str, Any],
        schema: dict[str, Any],
        api_path: str,
        location: str,
    ) -> list[ValidationError]:
        """Validate body parameters against schema.

        Args:
            body: Request body dictionary
            schema: API schema
            api_path: API path for alias lookup
            location: Error location string

        Returns:
            List of ValidationError objects
        """
        errors: list[ValidationError] = []
        schema_params = schema.get("parameters", {})
        aliases = PARAMETER_ALIASES.get(api_path, {})

        # Check for unknown parameters and typos
        for param_name in body.keys():
            if param_name not in schema_params:
                # Check if it's a known alias (typo)
                if param_name in aliases:
                    correct_name = aliases[param_name]
                    # Issue #344: Use PARAMETER_NAME_MISMATCH for typo detection
                    errors.append(
                        ValidationError(
                            code=ValidationErrorCode.PARAMETER_NAME_MISMATCH,
                            message=f"Parameter name mismatch: '{param_name}' should be '{correct_name}' for API {api_path}",
                            location=f"{location}.{param_name}",
                            suggestion=f"Did you mean '{correct_name}'? Use '{correct_name}' instead of '{param_name}'.",
                            severity="major",
                        )
                    )
                else:
                    # List valid parameters
                    valid_params = list(schema_params.keys())
                    errors.append(
                        ValidationError(
                            code=ValidationErrorCode.UNKNOWN_API_PARAMETER,
                            message=f"Unknown parameter '{param_name}' for API {api_path}",
                            location=f"{location}.{param_name}",
                            suggestion=f"Valid parameters: {', '.join(valid_params)}",
                            severity="major",
                        )
                    )

        # Check for missing required parameters
        for param_name, param_spec in schema_params.items():
            if isinstance(param_spec, dict) and param_spec.get("required", False):
                if param_name not in body:
                    errors.append(
                        ValidationError(
                            code=ValidationErrorCode.MISSING_REQUIRED_PARAMETER,
                            message=f"Missing required parameter '{param_name}' for API {api_path}",
                            location=location,
                            suggestion=f"Add '{param_name}' to the request body",
                            severity="critical",
                        )
                    )

        # Issue #344: Check for type mismatches
        for param_name, param_value in body.items():
            if param_name in schema_params:
                param_spec = schema_params[param_name]
                if isinstance(param_spec, dict):
                    expected_type = param_spec.get("type", "")

                    # Check array type
                    if expected_type == "array" and not isinstance(param_value, list):
                        # Skip if it's a reference (e.g., ":source.items")
                        if isinstance(param_value, str) and param_value.startswith(":"):
                            continue
                        errors.append(
                            ValidationError(
                                code=ValidationErrorCode.PARAMETER_TYPE_MISMATCH,
                                message=f"Type mismatch: '{param_name}' should be array, got {type(param_value).__name__}",
                                location=f"{location}.{param_name}",
                                suggestion=f"Wrap '{param_name}' value in brackets: [{param_value}]",
                                severity="major",
                            )
                        )

                    # Check integer type
                    elif expected_type == "integer":
                        if not isinstance(param_value, int):
                            # Skip if it's a reference
                            if isinstance(param_value, str) and param_value.startswith(
                                ":"
                            ):
                                continue
                            # Allow string representation of int
                            if isinstance(param_value, str) and param_value.isdigit():
                                continue
                            errors.append(
                                ValidationError(
                                    code=ValidationErrorCode.PARAMETER_TYPE_MISMATCH,
                                    message=f"Type mismatch: '{param_name}' should be integer, got {type(param_value).__name__}",
                                    location=f"{location}.{param_name}",
                                    suggestion=f"Use an integer value for '{param_name}'",
                                    severity="major",
                                )
                            )

                    # Check string type
                    elif expected_type == "string":
                        if not isinstance(param_value, str):
                            # Skip if it's a reference in a list
                            if isinstance(param_value, list):
                                continue
                            errors.append(
                                ValidationError(
                                    code=ValidationErrorCode.PARAMETER_TYPE_MISMATCH,
                                    message=f"Type mismatch: '{param_name}' should be string, got {type(param_value).__name__}",
                                    location=f"{location}.{param_name}",
                                    suggestion=f"Use a string value for '{param_name}'",
                                    severity="major",
                                )
                            )

        return errors


# Export
__all__ = ["APISchemaValidator", "PARAMETER_ALIASES"]
