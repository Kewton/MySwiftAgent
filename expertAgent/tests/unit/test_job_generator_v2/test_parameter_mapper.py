"""Unit tests for ParameterMapper - Issue #342 V2 Workflow Quality Improvement.

This module tests the ParameterMapper class that converts interface parameters
to GraphAI workflow parameters.

Test Coverage Target: 95%
"""

from __future__ import annotations

from typing import Any

import pytest


class TestMapInputParams:
    """Tests for map_input_params function."""

    def test_map_input_params_exists(self) -> None:
        """Test map_input_params function exists."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            map_input_params,
        )

        assert map_input_params is not None
        assert callable(map_input_params)

    def test_map_simple_input_params(self) -> None:
        """Test mapping simple input parameters."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            map_input_params,
        )

        interface_inputs = {
            "query": {"type": "string", "description": "Search query"},
            "count": {"type": "integer", "description": "Number of results"},
        }

        result = map_input_params(interface_inputs, source_node="user_input")

        assert "query" in result
        assert "count" in result
        assert result["query"] == ":source.user_input.query"
        assert result["count"] == ":source.user_input.count"

    def test_map_input_params_with_nested_objects(self) -> None:
        """Test mapping input params with nested objects."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            map_input_params,
        )

        interface_inputs = {
            "email": {
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                },
            }
        }

        result = map_input_params(interface_inputs, source_node="user_input")

        # Should map the whole object
        assert "email" in result
        assert result["email"] == ":source.user_input.email"

    def test_map_input_params_from_previous_node(self) -> None:
        """Test mapping input params from previous node output."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            map_input_params,
        )

        interface_inputs = {
            "search_results": {"type": "array"},
        }

        result = map_input_params(interface_inputs, source_node="search_node")

        assert result["search_results"] == ":source.search_node.search_results"

    def test_map_input_params_empty(self) -> None:
        """Test mapping empty input params."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            map_input_params,
        )

        result = map_input_params({}, source_node="user_input")

        assert result == {}


class TestMapAPIParams:
    """Tests for map_api_params function."""

    def test_map_api_params_exists(self) -> None:
        """Test map_api_params function exists."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            map_api_params,
        )

        assert map_api_params is not None
        assert callable(map_api_params)

    def test_map_api_params_gmail_send(self) -> None:
        """Test mapping API params for gmail_send."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            map_api_params,
        )

        interface_inputs = {
            "to": {"type": "string"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
        }

        result = map_api_params(
            api_name="gmail_send",
            interface_inputs=interface_inputs,
            source_node="user_input",
        )

        # Must have inputs block with url, method, body
        assert "url" in result
        assert "method" in result
        assert "body" in result

        # URL must use EXPERTAGENT_BASE_URL
        assert "${EXPERTAGENT_BASE_URL}" in result["url"]
        assert "gmail" in result["url"].lower()

        # Method must be POST
        assert result["method"] == "POST"

        # Body must have mapped params
        assert "to" in result["body"]
        assert "subject" in result["body"]
        assert "body" in result["body"]
        assert result["body"]["to"] == ":source.user_input.to"

    def test_map_api_params_google_search(self) -> None:
        """Test mapping API params for google_search."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            map_api_params,
        )

        interface_inputs = {
            "query": {"type": "string"},
            "num_results": {"type": "integer"},
        }

        result = map_api_params(
            api_name="google_search",
            interface_inputs=interface_inputs,
            source_node="user_input",
        )

        assert "url" in result
        assert "method" in result
        assert "body" in result
        assert "${EXPERTAGENT_BASE_URL}" in result["url"]
        assert "search" in result["url"].lower()

    def test_map_api_params_slack_notify(self) -> None:
        """Test mapping API params for slack_notify."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            map_api_params,
        )

        interface_inputs = {
            "channel": {"type": "string"},
            "message": {"type": "string"},
        }

        result = map_api_params(
            api_name="slack_notify",
            interface_inputs=interface_inputs,
            source_node="user_input",
        )

        assert "url" in result
        assert "method" in result
        assert "body" in result
        assert result["method"] == "POST"

    def test_map_api_params_unknown_api(self) -> None:
        """Test mapping API params for unknown API returns generic mapping."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            map_api_params,
        )

        interface_inputs = {
            "param1": {"type": "string"},
        }

        result = map_api_params(
            api_name="unknown_api",
            interface_inputs=interface_inputs,
            source_node="user_input",
        )

        # Should still return valid structure
        assert "url" in result
        assert "method" in result
        assert "body" in result

    def test_map_api_params_with_previous_node(self) -> None:
        """Test mapping API params with previous node as source."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            map_api_params,
        )

        interface_inputs = {
            "data": {"type": "object"},
        }

        result = map_api_params(
            api_name="gmail_send",
            interface_inputs=interface_inputs,
            source_node="transform_node",
        )

        assert result["body"]["data"] == ":source.transform_node.data"


class TestParameterMapperClass:
    """Tests for ParameterMapper class."""

    def test_parameter_mapper_creation(self) -> None:
        """Test ParameterMapper can be instantiated."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            ParameterMapper,
        )

        mapper = ParameterMapper()
        assert mapper is not None

    def test_create_fetchagent_inputs(self) -> None:
        """Test create_fetchagent_inputs method."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            ParameterMapper,
        )

        mapper = ParameterMapper()
        result = mapper.create_fetchagent_inputs(
            api_name="gmail_send",
            input_params={
                "to": "test@example.com",
                "subject": "Test",
                "body": "Hello",
            },
            source_node="user_input",
        )

        # Must be GraphAI spec compliant
        assert "url" in result
        assert "method" in result
        assert "body" in result
        assert "${EXPERTAGENT_BASE_URL}" in result["url"]

    def test_create_inputs_block(self) -> None:
        """Test create_inputs_block method generates GraphAI inputs block."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            ParameterMapper,
        )

        mapper = ParameterMapper()
        inputs_block = mapper.create_inputs_block(
            url="${EXPERTAGENT_BASE_URL}/v1/utility/gmail/send",
            method="POST",
            body={"to": ":source.user_input.to"},
        )

        assert inputs_block["url"] == "${EXPERTAGENT_BASE_URL}/v1/utility/gmail/send"
        assert inputs_block["method"] == "POST"
        assert inputs_block["body"]["to"] == ":source.user_input.to"

    def test_map_interface_to_body(self) -> None:
        """Test map_interface_to_body method."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            ParameterMapper,
        )

        mapper = ParameterMapper()
        interface_schema = {
            "to": {"type": "string"},
            "subject": {"type": "string"},
        }

        body = mapper.map_interface_to_body(interface_schema, "user_input")

        assert body["to"] == ":source.user_input.to"
        assert body["subject"] == ":source.user_input.subject"


class TestGraphAISpecCompliance:
    """Tests to verify GraphAI specification compliance."""

    def test_inputs_block_structure(self) -> None:
        """Test that inputs block follows GraphAI spec."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            map_api_params,
        )

        result = map_api_params(
            api_name="gmail_send",
            interface_inputs={"to": {"type": "string"}},
            source_node="user_input",
        )

        # GraphAI spec: inputs must contain url, method, body (NOT params)
        assert "url" in result
        assert "method" in result
        assert "body" in result

        # These should NOT be in params block
        # The result IS the inputs block, not a wrapper

    def test_source_reference_format(self) -> None:
        """Test source reference format follows GraphAI spec."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            map_input_params,
        )

        result = map_input_params(
            {"field": {"type": "string"}},
            source_node="previous_node",
        )

        # GraphAI spec: :source.nodeId.fieldName
        assert result["field"].startswith(":source.")
        assert "previous_node" in result["field"]

    def test_user_input_source_reference(self) -> None:
        """Test user_input source reference format."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            map_input_params,
        )

        result = map_input_params(
            {"query": {"type": "string"}},
            source_node="user_input",
        )

        # Should reference user_input node
        assert result["query"] == ":source.user_input.query"

    def test_expertagent_base_url_usage(self) -> None:
        """Test EXPERTAGENT_BASE_URL environment variable usage."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            map_api_params,
        )

        result = map_api_params(
            api_name="gmail_send",
            interface_inputs={"to": {"type": "string"}},
            source_node="user_input",
        )

        # URL must use ${EXPERTAGENT_BASE_URL} prefix
        assert result["url"].startswith("${EXPERTAGENT_BASE_URL}")


class TestParameterMapperEdgeCases:
    """Edge case tests for ParameterMapper."""

    def test_empty_interface_inputs(self) -> None:
        """Test handling empty interface inputs."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            map_api_params,
        )

        result = map_api_params(
            api_name="gmail_send",
            interface_inputs={},
            source_node="user_input",
        )

        # Should still have valid structure
        assert "url" in result
        assert "method" in result
        assert "body" in result
        assert result["body"] == {}

    def test_special_characters_in_field_names(self) -> None:
        """Test handling special characters in field names."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            map_input_params,
        )

        interface_inputs = {
            "user_email": {"type": "string"},
            "message_body": {"type": "string"},
        }

        result = map_input_params(interface_inputs, source_node="user_input")

        assert "user_email" in result
        assert "message_body" in result

    def test_array_type_handling(self) -> None:
        """Test handling array type fields."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            map_input_params,
        )

        interface_inputs = {
            "recipients": {"type": "array", "items": {"type": "string"}},
        }

        result = map_input_params(interface_inputs, source_node="user_input")

        assert "recipients" in result
        assert result["recipients"] == ":source.user_input.recipients"
