"""Unit tests for TaskIdMapping class (Issue #342 Bug #1, #5).

This module tests the TaskIdMapping class that provides proper mapping
between logical task_ids (e.g., 'task_001') and task_master_ids (e.g., 'tm_xxx').

Issue #342:
- Bug #1: task_id vs task_master_id confusion in interface lookup
- Bug #5: RegistrationOutput lacks task_id_to_master_id mapping
"""

from aiagent.langgraph.jobGeneratorV2.types import (
    InterfaceSchema,
    PhaseStatus,
    RegistrationOutput,
)


class TestRegistrationOutputMapping:
    """Test RegistrationOutput task_id_to_master_id field (Bug #5)."""

    def test_registration_output_has_task_id_to_master_id_field(self) -> None:
        """Bug #5: RegistrationOutput should have task_id_to_master_id field."""
        reg_output = RegistrationOutput(
            status=PhaseStatus.SUCCESS,
            job_master_id="jm_123",
            task_master_ids=["tm_001", "tm_002"],
            task_id_to_master_id={
                "task_001": "tm_001",
                "task_002": "tm_002",
            },
        )

        assert hasattr(reg_output, "task_id_to_master_id")
        assert reg_output.task_id_to_master_id == {
            "task_001": "tm_001",
            "task_002": "tm_002",
        }

    def test_registration_output_task_id_to_master_id_default_empty(self) -> None:
        """Bug #5: task_id_to_master_id should default to empty dict."""
        reg_output = RegistrationOutput(
            status=PhaseStatus.SUCCESS,
            job_master_id="jm_123",
            task_master_ids=["tm_001"],
        )

        assert reg_output.task_id_to_master_id == {}

    def test_registration_output_mapping_preserves_all_tasks(self) -> None:
        """Bug #5: All tasks should be represented in the mapping."""
        mapping = {
            "task_001_alt": "tm_001",
            "task_002_alt": "tm_002",
            "task_003": "tm_003",
        }

        reg_output = RegistrationOutput(
            status=PhaseStatus.SUCCESS,
            job_master_id="jm_123",
            task_master_ids=["tm_001", "tm_002", "tm_003"],
            task_id_to_master_id=mapping,
        )

        assert len(reg_output.task_id_to_master_id) == 3
        assert "task_001_alt" in reg_output.task_id_to_master_id
        assert "task_002_alt" in reg_output.task_id_to_master_id
        assert "task_003" in reg_output.task_id_to_master_id


class TestTaskIdMappingClass:
    """Test TaskIdMapping class (Bug #1)."""

    def test_task_id_mapping_exists(self) -> None:
        """Bug #1: TaskIdMapping class should exist."""
        from aiagent.langgraph.jobGeneratorV2.types import TaskIdMapping

        assert TaskIdMapping is not None

    def test_task_id_mapping_creation(self) -> None:
        """Bug #1: TaskIdMapping should be creatable with mappings."""
        from aiagent.langgraph.jobGeneratorV2.types import TaskIdMapping

        mapping = TaskIdMapping(
            logical_to_master={"task_001": "tm_001", "task_002": "tm_002"},
            master_to_logical={"tm_001": "task_001", "tm_002": "task_002"},
        )

        assert mapping.logical_to_master["task_001"] == "tm_001"
        assert mapping.master_to_logical["tm_001"] == "task_001"

    def test_task_id_mapping_from_registration(self) -> None:
        """Bug #1: TaskIdMapping.from_registration should create mapping from RegistrationOutput."""
        from aiagent.langgraph.jobGeneratorV2.types import TaskIdMapping

        reg_output = RegistrationOutput(
            status=PhaseStatus.SUCCESS,
            job_master_id="jm_123",
            task_master_ids=["tm_001", "tm_002"],
            task_id_to_master_id={
                "task_001_alt": "tm_001",
                "task_002_alt": "tm_002",
            },
        )

        mapping = TaskIdMapping.from_registration(reg_output)

        # Test logical_to_master
        assert mapping.logical_to_master["task_001_alt"] == "tm_001"
        assert mapping.logical_to_master["task_002_alt"] == "tm_002"

        # Test master_to_logical (reverse mapping)
        assert mapping.master_to_logical["tm_001"] == "task_001_alt"
        assert mapping.master_to_logical["tm_002"] == "task_002_alt"

    def test_task_id_mapping_get_master_id(self) -> None:
        """Bug #1: TaskIdMapping.get_master_id should return master_id for logical task_id."""
        from aiagent.langgraph.jobGeneratorV2.types import TaskIdMapping

        mapping = TaskIdMapping(
            logical_to_master={"task_001": "tm_001"},
            master_to_logical={"tm_001": "task_001"},
        )

        assert mapping.get_master_id("task_001") == "tm_001"
        assert mapping.get_master_id("unknown") is None

    def test_task_id_mapping_get_logical_id(self) -> None:
        """Bug #1: TaskIdMapping.get_logical_id should return logical_id for master_id."""
        from aiagent.langgraph.jobGeneratorV2.types import TaskIdMapping

        mapping = TaskIdMapping(
            logical_to_master={"task_001": "tm_001"},
            master_to_logical={"tm_001": "task_001"},
        )

        assert mapping.get_logical_id("tm_001") == "task_001"
        assert mapping.get_logical_id("unknown") is None

    def test_task_id_mapping_get_interface_for_master(self) -> None:
        """Bug #1: TaskIdMapping should enable correct interface lookup."""
        from aiagent.langgraph.jobGeneratorV2.types import TaskIdMapping

        # Setup: interfaces keyed by logical task_id
        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            ),
        }

        # Setup: mapping from master_id to logical_id
        mapping = TaskIdMapping(
            logical_to_master={"task_001": "tm_001", "task_002": "tm_002"},
            master_to_logical={"tm_001": "task_001", "tm_002": "task_002"},
        )

        # Bug #1 fix: Use mapping to lookup interface by master_id
        task_master_id = "tm_001"
        logical_id = mapping.get_logical_id(task_master_id)
        interface = interfaces.get(logical_id) if logical_id else None

        assert interface is not None
        assert interface.task_id == "task_001"

    def test_task_id_mapping_empty_registration(self) -> None:
        """Bug #1: TaskIdMapping should handle empty registration."""
        from aiagent.langgraph.jobGeneratorV2.types import TaskIdMapping

        reg_output = RegistrationOutput(
            status=PhaseStatus.SUCCESS,
            job_master_id="jm_123",
            task_master_ids=[],
            task_id_to_master_id={},
        )

        mapping = TaskIdMapping.from_registration(reg_output)

        assert mapping.logical_to_master == {}
        assert mapping.master_to_logical == {}

    def test_task_id_mapping_with_alternative_tasks(self) -> None:
        """Bug #1: TaskIdMapping should handle alternative task IDs correctly."""
        from aiagent.langgraph.jobGeneratorV2.types import TaskIdMapping

        # Scenario: Original task replaced with alternative
        reg_output = RegistrationOutput(
            status=PhaseStatus.SUCCESS,
            job_master_id="jm_123",
            task_master_ids=["tm_001", "tm_002_v2"],
            task_id_to_master_id={
                "task_001": "tm_001",
                "task_002_alt": "tm_002_v2",  # Alternative task
            },
        )

        mapping = TaskIdMapping.from_registration(reg_output)

        # Original task
        assert mapping.get_master_id("task_001") == "tm_001"
        assert mapping.get_logical_id("tm_001") == "task_001"

        # Alternative task
        assert mapping.get_master_id("task_002_alt") == "tm_002_v2"
        assert mapping.get_logical_id("tm_002_v2") == "task_002_alt"


class TestTaskIdMappingIntegration:
    """Integration tests for TaskIdMapping with workflow components."""

    def test_task_id_mapping_integration_with_yaml_generator(self) -> None:
        """Bug #1: TaskIdMapping should work with YAML generator interface lookup."""
        from aiagent.langgraph.jobGeneratorV2.types import TaskIdMapping

        # This test validates the fix for the interface lookup bug
        # where task_master_id was used instead of task_id for interface lookup

        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"properties": {"query": {"type": "string"}}},
                output_schema={"properties": {"results": {"type": "array"}}},
                description="Search interface",
            ),
        }

        mapping = TaskIdMapping(
            logical_to_master={"task_001": "tm_search_123"},
            master_to_logical={"tm_search_123": "task_001"},
        )

        # Simulate YAML generator looking up interface by task_master_id
        task_master_id = "tm_search_123"

        # OLD (buggy) way: interfaces.get(task_master_id) -> None
        buggy_result = interfaces.get(task_master_id)
        assert buggy_result is None, "Old buggy lookup should fail"

        # NEW (fixed) way: Use mapping to get logical_id first
        logical_id = mapping.get_logical_id(task_master_id)
        fixed_result = interfaces.get(logical_id) if logical_id else None
        assert fixed_result is not None, "Fixed lookup should succeed"
        assert fixed_result.task_id == "task_001"
