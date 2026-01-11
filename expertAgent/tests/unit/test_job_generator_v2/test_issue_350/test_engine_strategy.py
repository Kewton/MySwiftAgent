"""Unit tests for engine_strategy.py - Strategy Pattern foundation.

Issue #350 Task 1.1: Strategy Pattern base classes.

Test cases:
- test_graphai_strategy_protocol_compliance
- test_taskflow_strategy_protocol_compliance
- test_create_strategy_taskflow_default
- test_create_strategy_graphai_explicit
- test_unknown_engine_raises_error
"""

from __future__ import annotations

import pytest

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.engine_strategy import (
    EngineType,
    WorkflowGeneratorStrategy,
    create_strategy,
)


class TestEngineType:
    """Tests for EngineType enum."""

    def test_engine_type_graphai(self) -> None:
        """Test EngineType.GRAPHAI value."""
        assert EngineType.GRAPHAI.value == "graphai"

    def test_engine_type_taskflow(self) -> None:
        """Test EngineType.TASKFLOW value."""
        assert EngineType.TASKFLOW.value == "taskflow"


class TestCreateStrategy:
    """Tests for create_strategy factory function."""

    def test_create_strategy_taskflow_default(self) -> None:
        """Default engine should be TaskFlow."""
        strategy = create_strategy()
        assert strategy is not None
        assert isinstance(strategy, WorkflowGeneratorStrategy)
        assert strategy.engine_type == EngineType.TASKFLOW

    def test_create_strategy_graphai_explicit(self) -> None:
        """Explicit graphai engine should return GraphAI strategy."""
        strategy = create_strategy(EngineType.GRAPHAI)
        assert strategy is not None
        assert isinstance(strategy, WorkflowGeneratorStrategy)
        assert strategy.engine_type == EngineType.GRAPHAI

    def test_create_strategy_taskflow_explicit(self) -> None:
        """Explicit taskflow engine should return TaskFlow strategy."""
        strategy = create_strategy(EngineType.TASKFLOW)
        assert strategy is not None
        assert isinstance(strategy, WorkflowGeneratorStrategy)
        assert strategy.engine_type == EngineType.TASKFLOW

    def test_unknown_engine_raises_error(self) -> None:
        """Unknown engine should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown engine"):
            create_strategy("unknown")  # type: ignore[arg-type]


class TestGraphAIStrategyProtocol:
    """Tests for GraphAI Strategy Protocol compliance."""

    def test_graphai_strategy_has_generate_method(self) -> None:
        """GraphAI strategy should have generate method."""
        strategy = create_strategy(EngineType.GRAPHAI)
        assert hasattr(strategy, "generate")
        assert callable(getattr(strategy, "generate"))

    def test_graphai_strategy_has_get_prompt_rules_method(self) -> None:
        """GraphAI strategy should have get_prompt_rules method."""
        strategy = create_strategy(EngineType.GRAPHAI)
        assert hasattr(strategy, "get_prompt_rules")
        rules = strategy.get_prompt_rules()
        assert isinstance(rules, list)

    def test_graphai_strategy_has_get_validator_method(self) -> None:
        """GraphAI strategy should have get_validator method."""
        strategy = create_strategy(EngineType.GRAPHAI)
        assert hasattr(strategy, "get_validator")
        validator = strategy.get_validator()
        assert validator is not None

    def test_graphai_strategy_output_format(self) -> None:
        """GraphAI strategy should output YAML format."""
        strategy = create_strategy(EngineType.GRAPHAI)
        assert strategy.output_format == "yaml"


class TestTaskFlowStrategyProtocol:
    """Tests for TaskFlow Strategy Protocol compliance."""

    def test_taskflow_strategy_has_generate_method(self) -> None:
        """TaskFlow strategy should have generate method."""
        strategy = create_strategy(EngineType.TASKFLOW)
        assert hasattr(strategy, "generate")
        assert callable(getattr(strategy, "generate"))

    def test_taskflow_strategy_has_get_prompt_rules_method(self) -> None:
        """TaskFlow strategy should have get_prompt_rules method."""
        strategy = create_strategy(EngineType.TASKFLOW)
        assert hasattr(strategy, "get_prompt_rules")
        rules = strategy.get_prompt_rules()
        assert isinstance(rules, list)

    def test_taskflow_strategy_has_get_validator_method(self) -> None:
        """TaskFlow strategy should have get_validator method."""
        strategy = create_strategy(EngineType.TASKFLOW)
        assert hasattr(strategy, "get_validator")
        validator = strategy.get_validator()
        assert validator is not None

    def test_taskflow_strategy_output_format(self) -> None:
        """TaskFlow strategy should output JSON format."""
        strategy = create_strategy(EngineType.TASKFLOW)
        assert strategy.output_format == "json"
