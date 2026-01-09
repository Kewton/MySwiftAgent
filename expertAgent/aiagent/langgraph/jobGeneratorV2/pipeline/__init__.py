"""Pipeline for Job Generator V2 validation.

Issue #342 Task 4.1: Validation pipeline module.

This module provides the ValidationPipeline that orchestrates
multiple validators in sequence.
"""

from aiagent.langgraph.jobGeneratorV2.pipeline.validation_pipeline import (
    ValidationPipeline,
)

__all__ = ["ValidationPipeline"]
