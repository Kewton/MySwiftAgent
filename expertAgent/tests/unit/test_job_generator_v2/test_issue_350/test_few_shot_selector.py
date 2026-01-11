"""Unit tests for selector.py - Few-shot example selector.

Issue #350 Task 2.3: Few-shot selector implementation.

Test cases (5 total):
- test_select_api_call_examples
- test_select_transform_examples
- test_detect_patterns_from_task
- test_max_examples_limit
- test_engine_specific_examples
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.few_shot.selector import (
    FewShotSelector,
    TaskPattern,
)


class TestTaskPattern:
    """Tests for TaskPattern enum."""

    def test_api_call_pattern(self) -> None:
        """Test API_CALL pattern value."""
        assert TaskPattern.API_CALL.value == "api_call"

    def test_transform_pattern(self) -> None:
        """Test DATA_TRANSFORM pattern value."""
        assert TaskPattern.DATA_TRANSFORM.value == "transform"

    def test_parallel_pattern(self) -> None:
        """Test PARALLEL pattern value."""
        assert TaskPattern.PARALLEL.value == "parallel"


class TestFewShotSelector:
    """Tests for FewShotSelector class."""

    @pytest.fixture
    def selector(self, tmp_path: Path) -> FewShotSelector:
        """Create a selector with test examples."""
        # Create test few-shot directories
        graphai_dir = tmp_path / "graphai"
        taskflow_dir = tmp_path / "taskflow"
        graphai_dir.mkdir()
        taskflow_dir.mkdir()

        # Create test example files
        (graphai_dir / "api_call_pattern.yaml").write_text(
            """
name: "GraphAI API Call Pattern"
description: "API call example for GraphAI"
example:
  version: "0.5"
  nodes:
    fetch:
      agent: fetchAgent
"""
        )

        (taskflow_dir / "api_rest_pattern.yaml").write_text(
            """
name: "TaskFlow API REST Pattern"
description: "API call example for TaskFlow"
example:
  workflow_name: "api_example"
  steps:
    - id: fetch
      type: api_rest
"""
        )

        (taskflow_dir / "transform_pattern.yaml").write_text(
            """
name: "TaskFlow Transform Pattern"
description: "Transform example for TaskFlow"
example:
  workflow_name: "transform_example"
  steps:
    - id: format
      type: transform
"""
        )

        return FewShotSelector(base_path=tmp_path)

    def test_select_api_call_examples(self, selector: FewShotSelector) -> None:
        """Test selecting API call pattern examples."""
        examples = selector.select_examples(
            engine="taskflow",
            task_patterns=[TaskPattern.API_CALL],
        )
        assert len(examples) >= 1
        assert any("api" in str(ex).lower() for ex in examples)

    def test_select_transform_examples(self, selector: FewShotSelector) -> None:
        """Test selecting transform pattern examples."""
        examples = selector.select_examples(
            engine="taskflow",
            task_patterns=[TaskPattern.DATA_TRANSFORM],
        )
        assert len(examples) >= 1
        assert any("transform" in str(ex).lower() for ex in examples)

    def test_detect_patterns_from_task(self, selector: FewShotSelector) -> None:
        """Test pattern detection from task definitions."""
        task_definitions = [
            {"description": "Fetch data from REST API"},
            {"description": "Transform and format the response"},
            {"description": "Send notification via webhook"},
        ]
        patterns = selector.detect_patterns(task_definitions)
        assert TaskPattern.API_CALL in patterns
        assert TaskPattern.DATA_TRANSFORM in patterns

    def test_max_examples_limit(self, selector: FewShotSelector) -> None:
        """Test max_examples parameter limits results."""
        examples = selector.select_examples(
            engine="taskflow",
            task_patterns=[
                TaskPattern.API_CALL,
                TaskPattern.DATA_TRANSFORM,
                TaskPattern.PARALLEL,
            ],
            max_examples=2,
        )
        assert len(examples) <= 2

    def test_engine_specific_examples(self, selector: FewShotSelector) -> None:
        """Test engine-specific example selection."""
        # TaskFlow should return TaskFlow examples
        taskflow_examples = selector.select_examples(
            engine="taskflow",
            task_patterns=[TaskPattern.API_CALL],
        )

        # GraphAI should return GraphAI examples
        graphai_examples = selector.select_examples(
            engine="graphai",
            task_patterns=[TaskPattern.API_CALL],
        )

        # Examples should be different
        if taskflow_examples and graphai_examples:
            assert taskflow_examples[0] != graphai_examples[0]


class TestPatternDetection:
    """Tests for pattern detection logic."""

    @pytest.fixture
    def selector(self, tmp_path: Path) -> FewShotSelector:
        """Create a minimal selector for pattern detection tests."""
        return FewShotSelector(base_path=tmp_path)

    def test_detect_api_keywords(self, selector: FewShotSelector) -> None:
        """Detect API patterns from keywords."""
        tasks = [
            {"description": "Call the external API to fetch user data"},
        ]
        patterns = selector.detect_patterns(tasks)
        assert TaskPattern.API_CALL in patterns

    def test_detect_http_keywords(self, selector: FewShotSelector) -> None:
        """Detect API patterns from HTTP keywords."""
        tasks = [
            {"description": "HTTP request to get weather data"},
        ]
        patterns = selector.detect_patterns(tasks)
        assert TaskPattern.API_CALL in patterns

    def test_detect_transform_keywords(self, selector: FewShotSelector) -> None:
        """Detect transform patterns from keywords."""
        tasks = [
            {"description": "Convert JSON to CSV format"},
        ]
        patterns = selector.detect_patterns(tasks)
        assert TaskPattern.DATA_TRANSFORM in patterns

    def test_detect_parallel_keywords(self, selector: FewShotSelector) -> None:
        """Detect parallel patterns from keywords."""
        tasks = [
            {"description": "Execute multiple API calls in parallel"},
        ]
        patterns = selector.detect_patterns(tasks)
        assert TaskPattern.PARALLEL in patterns

    def test_detect_conditional_keywords(self, selector: FewShotSelector) -> None:
        """Detect conditional patterns from keywords."""
        tasks = [
            {"description": "If the response is valid, proceed to next step"},
        ]
        patterns = selector.detect_patterns(tasks)
        assert TaskPattern.CONDITIONAL in patterns

    def test_no_duplicate_patterns(self, selector: FewShotSelector) -> None:
        """Detected patterns should not have duplicates."""
        tasks = [
            {"description": "Call API to fetch data"},
            {"description": "Another API call to get more data"},
        ]
        patterns = selector.detect_patterns(tasks)
        # Should only have one API_CALL pattern
        assert patterns.count(TaskPattern.API_CALL) == 1
