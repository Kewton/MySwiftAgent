"""Few-shot Example Selector for Workflow Generation.

Issue #350 Task 2.3: Few-shot selector implementation.

This module provides:
- TaskPattern enum for pattern classification
- FewShotSelector class for pattern-based example selection

The selector:
1. Detects task patterns from descriptions
2. Selects appropriate few-shot examples based on engine and patterns
3. Limits examples to prevent context overflow
"""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class TaskPattern(str, Enum):
    """Task pattern classification.

    Used to select appropriate few-shot examples based on
    the type of task being generated.
    """

    API_CALL = "api_call"
    DATA_TRANSFORM = "transform"
    LLM_CHAIN = "llm_chain"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    SEARCH = "search"


class FewShotSelector:
    """Few-shot example selector.

    Selects appropriate examples based on engine type and task patterns.
    """

    # Pattern mapping: engine -> pattern -> file path
    PATTERN_MAPPING = {
        "graphai": {
            TaskPattern.API_CALL: "graphai/api_call_pattern.yaml",
            TaskPattern.LLM_CHAIN: "graphai/llm_chain_pattern.yaml",
            TaskPattern.DATA_TRANSFORM: "graphai/map_pattern.yaml",
            TaskPattern.SEARCH: "graphai/search_pattern.yaml",
        },
        "taskflow": {
            TaskPattern.API_CALL: "taskflow/api_rest_pattern.yaml",
            TaskPattern.DATA_TRANSFORM: "taskflow/transform_pattern.yaml",
            TaskPattern.PARALLEL: "taskflow/parallel_pattern.yaml",
            TaskPattern.CONDITIONAL: "taskflow/conditional_pattern.yaml",
        },
    }

    # Keywords for pattern detection
    PATTERN_KEYWORDS = {
        TaskPattern.API_CALL: [
            "api",
            "http",
            "fetch",
            "call",
            "request",
            "endpoint",
            "rest",
            "webhook",
        ],
        TaskPattern.DATA_TRANSFORM: [
            "transform",
            "convert",
            "format",
            "parse",
            "extract",
            "map",
            "filter",
        ],
        TaskPattern.LLM_CHAIN: [
            "llm",
            "ai",
            "generate",
            "analyze",
            "summarize",
            "chat",
            "gpt",
            "claude",
        ],
        TaskPattern.PARALLEL: [
            "parallel",
            "concurrent",
            "simultaneously",
            "at the same time",
            "同時",
        ],
        TaskPattern.CONDITIONAL: [
            "if",
            "condition",
            "when",
            "otherwise",
            "branch",
            "分岐",
            "条件",
        ],
        TaskPattern.SEARCH: [
            "search",
            "find",
            "query",
            "lookup",
            "検索",
        ],
    }

    def __init__(self, base_path: Path | str | None = None) -> None:
        """Initialize the selector.

        Args:
            base_path: Base path for few-shot example files.
                      If None, uses the default path relative to this file.
        """
        if base_path is None:
            # Default to the few_shot directory
            base_path = Path(__file__).parent
        elif isinstance(base_path, str):
            base_path = Path(base_path)

        self.base_path = base_path

    def select_examples(
        self,
        engine: str,
        task_patterns: list[TaskPattern],
        max_examples: int = 3,
    ) -> list[dict[str, Any]]:
        """Select few-shot examples based on engine and patterns.

        Args:
            engine: Engine type ('graphai' or 'taskflow')
            task_patterns: List of detected task patterns
            max_examples: Maximum number of examples to return

        Returns:
            List of example dictionaries loaded from YAML files
        """
        examples: list[dict[str, Any]] = []
        mapping = self.PATTERN_MAPPING.get(engine, {})

        for pattern in task_patterns[:max_examples]:
            if pattern not in mapping:
                continue

            example_path = self.base_path / mapping[pattern]
            if not example_path.exists():
                logger.debug(f"Example file not found: {example_path}")
                continue

            try:
                with open(example_path, encoding="utf-8") as f:
                    example = yaml.safe_load(f)
                    if example:
                        examples.append(example)
            except Exception as e:
                logger.warning(f"Failed to load example from {example_path}: {e}")

        return examples[:max_examples]

    def detect_patterns(
        self,
        task_definitions: list[dict[str, Any]],
    ) -> list[TaskPattern]:
        """Detect task patterns from task definitions.

        Analyzes task descriptions to determine which patterns
        are present in the workflow.

        Args:
            task_definitions: List of task definition dictionaries
                            with 'description' field

        Returns:
            List of unique detected patterns
        """
        detected: set[TaskPattern] = set()

        for task in task_definitions:
            description = task.get("description", "").lower()

            for pattern, keywords in self.PATTERN_KEYWORDS.items():
                if any(kw in description for kw in keywords):
                    detected.add(pattern)

        return list(detected)


__all__ = ["TaskPattern", "FewShotSelector"]
