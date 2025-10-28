"""OpenAPI Schema Collector for API Definition Automation

This module automatically collects and parses OpenAPI schemas from expertAgent
to ensure accurate API interface definitions during workflow generation.

Key features:
- Fetches OpenAPI 3.1.0 specifications from running services
- Extracts request/response schemas with field details
- Provides type-safe schema information for workflow generation
- Caches schemas to minimize HTTP requests

Usage:
    collector = OpenAPISchemaCollector("http://localhost:8104/aiagent-api")
    schema = collector.get_endpoint_schema("POST", "/v1/utility/gmail/search")
"""

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FieldSchema(BaseModel):
    """API endpoint field schema definition"""

    name: str = Field(..., description="Field name")
    type: str = Field(..., description="Field type (string, integer, boolean, etc.)")
    required: bool = Field(default=False, description="Whether field is required")
    description: Optional[str] = Field(None, description="Field description")
    default: Optional[Any] = Field(None, description="Default value if any")
    pattern: Optional[str] = Field(None, description="Regex pattern for validation")
    minimum: Optional[float] = Field(None, description="Minimum value for numbers")
    maximum: Optional[float] = Field(None, description="Maximum value for numbers")
    enum: Optional[List[str]] = Field(None, description="Allowed enum values")


class EndpointSchema(BaseModel):
    """Complete API endpoint schema"""

    method: str = Field(..., description="HTTP method (GET, POST, etc.)")
    path: str = Field(..., description="API endpoint path")
    summary: Optional[str] = Field(None, description="Endpoint summary")
    description: Optional[str] = Field(None, description="Detailed description")
    request_fields: List[FieldSchema] = Field(
        default_factory=list, description="Request body fields"
    )
    response_fields: List[FieldSchema] = Field(
        default_factory=list, description="Response body fields"
    )
    example_request: Optional[Dict[str, Any]] = Field(
        None, description="Example request"
    )
    example_response: Optional[Dict[str, Any]] = Field(
        None, description="Example response"
    )


class OpenAPISchemaCollector:
    """Collects and parses OpenAPI schemas from running services"""

    def __init__(self, base_url: str, openapi_path: str = "/openapi.json"):
        """Initialize OpenAPI schema collector

        Args:
            base_url: Base URL of the API service (e.g., http://localhost:8104/aiagent-api)
            openapi_path: Path to OpenAPI JSON spec (default: /openapi.json)
        """
        self.base_url = base_url.rstrip("/")
        self.openapi_url = urljoin(self.base_url, openapi_path)
        self._openapi_spec: Optional[Dict[str, Any]] = None
        self._schema_cache: Dict[str, EndpointSchema] = {}

    async def _fetch_openapi_spec(self) -> Dict[str, Any]:
        """Fetch OpenAPI specification from the service

        Returns:
            OpenAPI specification dictionary

        Raises:
            httpx.HTTPError: If fetching OpenAPI spec fails
        """
        if self._openapi_spec is not None:
            return self._openapi_spec

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.openapi_url)
            response.raise_for_status()
            self._openapi_spec = response.json()
            logger.info(
                "Fetched OpenAPI spec from %s (version: %s, paths: %d)",
                self.openapi_url,
                self._openapi_spec.get("openapi"),
                len(self._openapi_spec.get("paths", {})),
            )
            return self._openapi_spec

    def _parse_field_schema(
        self, field_name: str, field_def: Dict[str, Any], required_fields: List[str]
    ) -> FieldSchema:
        """Parse a single field schema from OpenAPI definition

        Args:
            field_name: Name of the field
            field_def: Field definition from OpenAPI schema
            required_fields: List of required field names

        Returns:
            Parsed FieldSchema object
        """
        # Handle anyOf types (e.g., Optional[str] = anyOf[str, null])
        field_type = field_def.get("type", "object")
        if "anyOf" in field_def:
            types = [t.get("type") for t in field_def["anyOf"] if t.get("type")]
            field_type = types[0] if types else "any"

        return FieldSchema(
            name=field_name,
            type=field_type,
            required=field_name in required_fields,
            description=field_def.get("description"),
            default=field_def.get("default"),
            pattern=field_def.get("pattern"),
            minimum=field_def.get("minimum"),
            maximum=field_def.get("maximum"),
            enum=field_def.get("enum"),
        )

    def _resolve_schema_ref(
        self, ref: str, openapi_spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve $ref pointer in OpenAPI schema

        Args:
            ref: JSON pointer reference (e.g., #/components/schemas/GmailSearchRequest)
            openapi_spec: Full OpenAPI specification

        Returns:
            Resolved schema definition
        """
        if not ref.startswith("#/"):
            logger.warning("Unsupported $ref format: %s", ref)
            return {}

        parts = ref[2:].split("/")
        current = openapi_spec
        for part in parts:
            current = current.get(part, {})
        return current

    async def get_endpoint_schema(
        self, method: str, path: str
    ) -> Optional[EndpointSchema]:
        """Get schema for a specific API endpoint

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path (e.g., /v1/utility/gmail/search)

        Returns:
            EndpointSchema if found, None otherwise
        """
        cache_key = f"{method.upper()}:{path}"
        if cache_key in self._schema_cache:
            return self._schema_cache[cache_key]

        openapi_spec = await self._fetch_openapi_spec()

        if path not in openapi_spec.get("paths", {}):
            logger.warning("Endpoint not found in OpenAPI spec: %s %s", method, path)
            return None

        endpoint_def = openapi_spec["paths"][path]
        method_def = endpoint_def.get(method.lower())

        if not method_def:
            logger.warning("Method %s not found for endpoint %s", method, path)
            return None

        # Extract request body schema
        request_fields: List[FieldSchema] = []
        example_request = None

        request_body = method_def.get("requestBody", {})
        if request_body:
            content = request_body.get("content", {}).get("application/json", {})
            schema_def = content.get("schema", {})

            # Resolve $ref if present
            if "$ref" in schema_def:
                schema_def = self._resolve_schema_ref(schema_def["$ref"], openapi_spec)

            # Parse fields
            properties = schema_def.get("properties", {})
            required_fields = schema_def.get("required", [])
            example_request = schema_def.get("example")

            for field_name, field_def in properties.items():
                field_schema = self._parse_field_schema(
                    field_name, field_def, required_fields
                )
                request_fields.append(field_schema)

        # Extract response schema (similar logic)
        response_fields: List[FieldSchema] = []
        example_response = None

        responses = method_def.get("responses", {})
        success_response = responses.get("200", {})
        if success_response:
            content = success_response.get("content", {}).get("application/json", {})
            schema_def = content.get("schema", {})

            if "$ref" in schema_def:
                schema_def = self._resolve_schema_ref(schema_def["$ref"], openapi_spec)

            properties = schema_def.get("properties", {})
            required_fields = schema_def.get("required", [])

            for field_name, field_def in properties.items():
                field_schema = self._parse_field_schema(
                    field_name, field_def, required_fields
                )
                response_fields.append(field_schema)

        endpoint_schema = EndpointSchema(
            method=method.upper(),
            path=path,
            summary=method_def.get("summary"),
            description=method_def.get("description"),
            request_fields=request_fields,
            response_fields=response_fields,
            example_request=example_request,
            example_response=example_response,
        )

        self._schema_cache[cache_key] = endpoint_schema
        logger.info(
            "Parsed endpoint schema: %s %s (%d request fields, %d response fields)",
            method.upper(),
            path,
            len(request_fields),
            len(response_fields),
        )
        return endpoint_schema

    async def get_all_endpoints(self) -> List[EndpointSchema]:
        """Get schemas for all available endpoints

        Returns:
            List of all endpoint schemas
        """
        openapi_spec = await self._fetch_openapi_spec()
        endpoints: List[EndpointSchema] = []

        for path, path_def in openapi_spec.get("paths", {}).items():
            for method in ["get", "post", "put", "patch", "delete"]:
                if method in path_def:
                    schema = await self.get_endpoint_schema(method.upper(), path)
                    if schema:
                        endpoints.append(schema)

        logger.info("Collected %d endpoint schemas", len(endpoints))
        return endpoints
