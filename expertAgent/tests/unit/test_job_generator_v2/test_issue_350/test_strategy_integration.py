"""Integration tests for Strategy Pattern in WorkflowGenWorkflow.

Issue #350 Iteration 2: Dead code fix - verify Strategy is actually used.

Test cases:
- test_workflow_with_taskflow_engine_uses_taskflow_strategy
- test_workflow_with_graphai_engine_uses_graphai_strategy
- test_workflow_strategy_property_accessible
- test_workflow_engine_property_accessible
- test_create_strategy_called_in_init
- test_adapter_passes_engine_to_workflow
"""

from __future__ import annotations

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.engine_strategy import (
    EngineType,
    GraphAIGeneratorStrategy,
    TaskFlowGeneratorStrategy,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow import (
    WorkflowGenWorkflow,
)


class TestWorkflowEngineIntegration:
    """Tests for engine parameter integration in WorkflowGenWorkflow."""

    def test_workflow_with_taskflow_engine_uses_taskflow_strategy(self) -> None:
        """WorkflowGenWorkflow with engine='taskflow' should use TaskFlowGeneratorStrategy."""
        workflow = WorkflowGenWorkflow(engine="taskflow")

        # Verify strategy is TaskFlow
        assert workflow.strategy is not None
        assert isinstance(workflow.strategy, TaskFlowGeneratorStrategy)
        assert workflow.strategy.engine_type == EngineType.TASKFLOW

    def test_workflow_with_graphai_engine_uses_graphai_strategy(self) -> None:
        """WorkflowGenWorkflow with engine='graphai' should use GraphAIGeneratorStrategy."""
        workflow = WorkflowGenWorkflow(engine="graphai")

        # Verify strategy is GraphAI
        assert workflow.strategy is not None
        assert isinstance(workflow.strategy, GraphAIGeneratorStrategy)
        assert workflow.strategy.engine_type == EngineType.GRAPHAI

    def test_workflow_default_engine_is_taskflow(self) -> None:
        """Default engine should be 'taskflow' per Issue #350 requirements."""
        workflow = WorkflowGenWorkflow()

        # Verify default is TaskFlow
        assert workflow.engine == "taskflow"
        assert isinstance(workflow.strategy, TaskFlowGeneratorStrategy)

    def test_workflow_strategy_property_accessible(self) -> None:
        """Strategy property should be accessible for testing/introspection."""
        workflow = WorkflowGenWorkflow(engine="taskflow")

        # Access strategy property
        strategy = workflow.strategy
        assert strategy is not None
        assert hasattr(strategy, "engine_type")
        assert hasattr(strategy, "output_format")
        assert hasattr(strategy, "generate")

    def test_workflow_engine_property_accessible(self) -> None:
        """Engine property should be accessible for testing/introspection."""
        workflow = WorkflowGenWorkflow(engine="graphai")

        # Access engine property
        engine = workflow.engine
        assert engine == "graphai"

    def test_create_strategy_called_in_init(self) -> None:
        """create_strategy should be called during __init__."""
        # Verify by checking strategy is set immediately after construction
        workflow = WorkflowGenWorkflow(engine="taskflow")

        # Strategy should be set
        assert hasattr(workflow, "_strategy")
        assert workflow._strategy is not None

    def test_strategy_output_format_matches_engine(self) -> None:
        """Strategy output format should match expected format for engine."""
        # TaskFlow produces JSON
        taskflow_workflow = WorkflowGenWorkflow(engine="taskflow")
        assert taskflow_workflow.strategy.output_format == "json"

        # GraphAI produces YAML
        graphai_workflow = WorkflowGenWorkflow(engine="graphai")
        assert graphai_workflow.strategy.output_format == "yaml"


class TestAdapterEngineIntegration:
    """Tests for engine parameter propagation from adapter to workflow."""

    def test_adapter_with_taskflow_engine(self) -> None:
        """Adapter with engine='taskflow' should create TaskFlow workflow."""
        from aiagent.langgraph.jobGeneratorV2.adapter import JobGeneratorV2Adapter
        from aiagent.langgraph.jobGeneratorV2.types_old import Phase

        adapter = JobGeneratorV2Adapter(engine="taskflow")

        # Get workflow from orchestrator
        workflow = adapter._orchestrator.get_workflow(Phase.WORKFLOW_GEN)

        assert workflow is not None
        assert isinstance(workflow, WorkflowGenWorkflow)
        assert workflow.engine == "taskflow"
        assert isinstance(workflow.strategy, TaskFlowGeneratorStrategy)

    def test_adapter_with_graphai_engine(self) -> None:
        """Adapter with engine='graphai' should create GraphAI workflow."""
        from aiagent.langgraph.jobGeneratorV2.adapter import JobGeneratorV2Adapter
        from aiagent.langgraph.jobGeneratorV2.types_old import Phase

        adapter = JobGeneratorV2Adapter(engine="graphai")

        # Get workflow from orchestrator
        workflow = adapter._orchestrator.get_workflow(Phase.WORKFLOW_GEN)

        assert workflow is not None
        assert isinstance(workflow, WorkflowGenWorkflow)
        assert workflow.engine == "graphai"
        assert isinstance(workflow.strategy, GraphAIGeneratorStrategy)

    def test_adapter_default_engine_is_taskflow(self) -> None:
        """Adapter default engine should be 'taskflow'."""
        from aiagent.langgraph.jobGeneratorV2.adapter import JobGeneratorV2Adapter
        from aiagent.langgraph.jobGeneratorV2.adapter_old import DEFAULT_ENGINE

        assert DEFAULT_ENGINE == "taskflow"

        adapter = JobGeneratorV2Adapter()
        assert adapter._engine == "taskflow"


class TestStrategyIntegrationWithGenerateMethod:
    """Tests for strategy usage in _generate_with_strategy method."""

    def test_generate_with_strategy_method_exists(self) -> None:
        """_generate_with_strategy method should exist."""
        workflow = WorkflowGenWorkflow(engine="taskflow")

        assert hasattr(workflow, "_generate_with_strategy")
        assert callable(workflow._generate_with_strategy)

    def test_workflow_has_all_required_strategy_attributes(self) -> None:
        """Workflow should have all strategy-related attributes."""
        workflow = WorkflowGenWorkflow(engine="taskflow")

        # Required attributes
        assert hasattr(workflow, "_engine")
        assert hasattr(workflow, "_strategy")
        assert hasattr(workflow, "engine")  # property
        assert hasattr(workflow, "strategy")  # property


class TestDeadCodeFixVerification:
    """Tests to verify the dead code fix from Issue #350 Iteration 2.

    These tests explicitly check that the Strategy Pattern code
    that was previously "dead" is now integrated and used.
    """

    def test_strategy_is_stored_in_workflow(self) -> None:
        """Strategy should be stored as instance variable, not just created."""
        workflow = WorkflowGenWorkflow(engine="taskflow")

        # _strategy should be set (not None)
        assert workflow._strategy is not None

        # Should be the correct strategy type
        assert workflow._strategy.engine_type == EngineType.TASKFLOW

    def test_strategy_is_accessible_via_property(self) -> None:
        """Strategy should be accessible via public property."""
        workflow = WorkflowGenWorkflow(engine="graphai")

        # Property should return the stored strategy
        assert workflow.strategy is workflow._strategy
        assert workflow.strategy.engine_type == EngineType.GRAPHAI

    def test_engine_parameter_flows_through_system(self) -> None:
        """Engine parameter should flow from adapter to workflow to strategy."""
        from aiagent.langgraph.jobGeneratorV2.adapter import JobGeneratorV2Adapter
        from aiagent.langgraph.jobGeneratorV2.types_old import Phase

        # Create adapter with specific engine
        adapter = JobGeneratorV2Adapter(engine="graphai")

        # Verify engine is stored in adapter
        assert adapter._engine == "graphai"

        # Get workflow from orchestrator
        workflow = adapter._orchestrator.get_workflow(Phase.WORKFLOW_GEN)
        assert workflow is not None

        # Verify engine in workflow
        assert workflow.engine == "graphai"

        # Verify strategy in workflow
        assert workflow.strategy.engine_type == EngineType.GRAPHAI

    def test_strategy_can_get_prompt_rules(self) -> None:
        """Strategy's get_prompt_rules should be callable and return rules."""
        workflow = WorkflowGenWorkflow(engine="taskflow")

        # Should be able to call get_prompt_rules
        rules = workflow.strategy.get_prompt_rules()

        assert isinstance(rules, list)
        # Rules should not be empty for TaskFlow
        assert len(rules) > 0

    def test_strategy_can_get_validator(self) -> None:
        """Strategy's get_validator should be callable and return validator."""
        workflow = WorkflowGenWorkflow(engine="taskflow")

        # Should be able to call get_validator
        validator = workflow.strategy.get_validator()

        assert validator is not None
        # TaskFlow validator should have validate method
        assert hasattr(validator, "validate")
