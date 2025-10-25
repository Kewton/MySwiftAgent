"""LLM Factory for Job Task Generator.

This module provides a factory function to create LLM instances based on model names.
Supports multiple LLM providers:
- Claude (Anthropic): claude-*, haiku-*, sonnet-*, opus-*
- GPT (OpenAI): gpt-*
- Gemini (Google): gemini-*

API Keys are managed by MyVault and read from environment variables:
- ANTHROPIC_API_KEY for Claude
- OPENAI_API_KEY for GPT
- GOOGLE_API_KEY for Gemini

Enhanced Features (Issue #111):
- Automatic fallback mechanism when primary model fails
- Model performance tracking (response time, token usage)
- Cost tracking and reporting
"""

import logging
import time
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from core.secrets import secrets_manager

logger = logging.getLogger(__name__)


def create_llm(
    model_name: str,
    temperature: float = 0.0,
    max_tokens: int = 8192,
) -> BaseChatModel:
    """Create LLM instance based on model name.

    This factory function detects the LLM provider from the model name prefix
    and creates the appropriate LLM client instance.

    Provider Detection:
        - Claude (Anthropic): claude-*, haiku-*, sonnet-*, opus-*
        - GPT (OpenAI): gpt-*
        - Gemini (Google): gemini-*

    Args:
        model_name: Model name (e.g., "claude-haiku-4-5", "gpt-4o-mini", "gemini-2.5-flash")
        temperature: Temperature parameter for response generation (default: 0.0)
            - 0.0 = deterministic (recommended for structured output)
            - 1.0 = creative
        max_tokens: Maximum tokens in response (default: 8192)

    Returns:
        LLM instance (ChatAnthropic, ChatOpenAI, or ChatGoogleGenerativeAI)

    Raises:
        ValueError: If model name is invalid or provider is not supported

    Examples:
        >>> # Claude model
        >>> llm = create_llm("claude-haiku-4-5", temperature=0.0, max_tokens=8192)
        >>> isinstance(llm, ChatAnthropic)
        True

        >>> # GPT model
        >>> llm = create_llm("gpt-4o-mini", temperature=0.0, max_tokens=8192)
        >>> isinstance(llm, ChatOpenAI)
        True

        >>> # Gemini model
        >>> llm = create_llm("gemini-2.5-flash", temperature=0.0, max_tokens=8192)
        >>> isinstance(llm, ChatGoogleGenerativeAI)
        True

        >>> # Invalid model name
        >>> llm = create_llm("invalid-model")
        Traceback (most recent call last):
        ...
        ValueError: Unsupported model: invalid-model...
    """
    if not model_name or not isinstance(model_name, str):
        raise ValueError(
            f"Invalid model_name: {model_name}. Must be a non-empty string."
        )

    model_lower = model_name.lower()

    # Detect Claude/Anthropic models
    if any(
        model_lower.startswith(prefix)
        for prefix in ["claude-", "haiku-", "sonnet-", "opus-"]
    ):
        logger.debug(
            f"Creating ChatAnthropic instance: model={model_name}, "
            f"temperature={temperature}, max_tokens={max_tokens}"
        )

        # Retrieve API key from MyVault
        try:
            anthropic_api_key = secrets_manager.get_secret(
                "ANTHROPIC_API_KEY", project=None
            )
        except ValueError as e:
            raise ValueError(
                f"Failed to initialize Claude model '{model_name}': {e}. "
                f"Please ensure ANTHROPIC_API_KEY is set in MyVault for default project"
            ) from e

        return ChatAnthropic(  # type: ignore[call-arg]
            model_name=model_name,
            temperature=temperature,
            max_tokens_to_sample=max_tokens,
            api_key=SecretStr(anthropic_api_key),
        )

    # Detect OpenAI GPT models
    if model_lower.startswith("gpt-"):
        logger.debug(
            f"Creating ChatOpenAI instance: model={model_name}, "
            f"temperature={temperature}, max_tokens={max_tokens}"
        )

        # Retrieve API key from MyVault
        try:
            openai_api_key = secrets_manager.get_secret("OPENAI_API_KEY", project=None)
        except ValueError as e:
            raise ValueError(
                f"Failed to initialize OpenAI model '{model_name}': {e}. "
                f"Please ensure OPENAI_API_KEY is set in MyVault for default project"
            ) from e

        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_completion_tokens=max_tokens,
            api_key=SecretStr(openai_api_key),
        )

    # Detect Google Gemini models
    if model_lower.startswith("gemini-"):
        logger.debug(
            f"Creating ChatGoogleGenerativeAI instance: model={model_name}, "
            f"temperature={temperature}, max_tokens={max_tokens}"
        )

        # Retrieve API key from MyVault
        try:
            google_api_key = secrets_manager.get_secret("GOOGLE_API_KEY", project=None)
        except ValueError as e:
            raise ValueError(
                f"Failed to initialize Gemini model '{model_name}': {e}. "
                f"Please ensure GOOGLE_API_KEY is set in MyVault for default project"
            ) from e

        return ChatGoogleGenerativeAI(  # type: ignore[call-arg]
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            google_api_key=google_api_key,
        )

    # Unsupported model
    raise ValueError(
        f"Unsupported model: {model_name}. "
        f"Supported prefixes: claude-*, haiku-*, sonnet-*, opus-*, gpt-*, gemini-*"
    )


class ModelPerformanceTracker:
    """Model performance measurement and logging.

    This class tracks LLM invocation metrics including response time,
    token usage, and success/failure status.

    Attributes:
        model_name: Name of the LLM model
        start_time: Timestamp when measurement started (seconds since epoch)
        end_time: Timestamp when measurement ended (seconds since epoch)
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        success: Whether the LLM invocation succeeded
        error: Error message if invocation failed

    Examples:
        >>> tracker = ModelPerformanceTracker("claude-haiku-4-5")
        >>> tracker.start()
        >>> # ... LLM invocation ...
        >>> tracker.end(success=True, input_tokens=100, output_tokens=50)
        >>> tracker.log_metrics()
        INFO - Model Performance: model=claude-haiku-4-5, duration=123.45ms, ...
    """

    def __init__(self, model_name: str):
        """Initialize performance tracker.

        Args:
            model_name: Name of the LLM model being tracked
        """
        self.model_name = model_name
        self.start_time: float | None = None
        self.end_time: float | None = None
        self.input_tokens: int = 0
        self.output_tokens: int = 0
        self.success: bool = False
        self.error: str | None = None

    def start(self) -> None:
        """Start performance measurement.

        Records the current high-resolution timestamp for duration calculation.
        """
        self.start_time = time.perf_counter()

    def end(
        self,
        success: bool,
        input_tokens: int = 0,
        output_tokens: int = 0,
        error: str | None = None,
    ) -> None:
        """End performance measurement and record results.

        Args:
            success: Whether the LLM invocation succeeded
            input_tokens: Number of input tokens (default: 0)
            output_tokens: Number of output tokens (default: 0)
            error: Error message if invocation failed (default: None)
        """
        self.end_time = time.perf_counter()
        self.success = success
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.error = error

    def get_duration_ms(self) -> float:
        """Calculate response time in milliseconds.

        Returns:
            Response time in milliseconds, or 0.0 if measurement not completed

        Examples:
            >>> tracker = ModelPerformanceTracker("claude-haiku-4-5")
            >>> tracker.start()
            >>> time.sleep(0.1)
            >>> tracker.end(success=True, input_tokens=100, output_tokens=50)
            >>> duration = tracker.get_duration_ms()
            >>> 90.0 < duration < 110.0  # Approximately 100ms
            True
        """
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0

    def log_metrics(self) -> None:
        """Log performance metrics at INFO level.

        Logs include model name, duration, token counts, success status, and error if any.
        """
        logger.info(
            f"Model Performance: model={self.model_name}, "
            f"duration={self.get_duration_ms():.2f}ms, "
            f"input_tokens={self.input_tokens}, "
            f"output_tokens={self.output_tokens}, "
            f"success={self.success}, "
            f"error={self.error}"
        )


class ModelCostTracker:
    """Model cost calculation and tracking.

    This class calculates LLM API costs based on token usage and maintains
    a running total for the session. Cost rates are based on official pricing
    as of October 2025.

    Attributes:
        total_cost: Cumulative cost for all API calls (USD)
        session_costs: List of individual call costs with details

    Cost Table (USD per 1M tokens):
        - claude-haiku-4-5: $0.80 input, $4.00 output
        - claude-sonnet-4-5: $3.00 input, $15.00 output
        - gpt-4o: $2.50 input, $10.00 output
        - gpt-4o-mini: $0.15 input, $0.60 output
        - gemini-2.5-flash: $0.075 input, $0.30 output

    Examples:
        >>> tracker = ModelCostTracker()
        >>> cost = tracker.add_call("claude-haiku-4-5", input_tokens=1000, output_tokens=500)
        >>> print(f"Cost: ${cost:.4f}")
        Cost: $0.0028
        >>> tracker.log_summary()
        INFO - Cost Summary: total_cost=$0.0028 USD, calls=1
    """

    # Cost table (USD per 1M tokens) as of October 2025
    COST_TABLE: dict[str, dict[str, float]] = {
        "claude-haiku-4-5": {"input": 0.80, "output": 4.00},
        "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    }

    def __init__(self) -> None:
        """Initialize cost tracker with zero totals."""
        self.total_cost: float = 0.0
        self.session_costs: list[dict[str, Any]] = []

    def calculate_cost(
        self, model_name: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Calculate cost for a single API call.

        Args:
            model_name: Name of the LLM model
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Total cost in USD

        Examples:
            >>> tracker = ModelCostTracker()
            >>> cost = tracker.calculate_cost("claude-haiku-4-5", 1000, 500)
            >>> print(f"${cost:.4f}")
            $0.0028
        """
        cost_info = self.COST_TABLE.get(model_name.lower())
        if not cost_info:
            logger.warning(f"Cost table not found for model: {model_name}")
            return 0.0

        input_cost = (input_tokens / 1_000_000) * cost_info["input"]
        output_cost = (output_tokens / 1_000_000) * cost_info["output"]
        total = input_cost + output_cost

        return total

    def add_call(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
        """Add API call cost to running total.

        Args:
            model_name: Name of the LLM model
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost for this specific call in USD

        Examples:
            >>> tracker = ModelCostTracker()
            >>> cost1 = tracker.add_call("gpt-4o-mini", 500, 200)
            >>> cost2 = tracker.add_call("gpt-4o-mini", 300, 150)
            >>> print(f"Total: ${tracker.total_cost:.4f}")
            Total: $0.0003
        """
        cost = self.calculate_cost(model_name, input_tokens, output_tokens)
        self.total_cost += cost
        self.session_costs.append(
            {
                "model": model_name,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost,
            }
        )
        return cost

    def log_summary(self) -> None:
        """Log cost summary at INFO level.

        Logs total cost and number of API calls. Detailed per-call costs
        are logged at DEBUG level.
        """
        logger.info(
            f"Cost Summary: total_cost=${self.total_cost:.4f} USD, "
            f"calls={len(self.session_costs)}"
        )
        for call in self.session_costs:
            logger.debug(
                f"  - {call['model']}: ${call['cost_usd']:.4f} USD "
                f"(input={call['input_tokens']}, output={call['output_tokens']})"
            )


def create_llm_with_fallback(
    model_name: str,
    temperature: float = 0.0,
    max_tokens: int = 8192,
    fallback_models: list[str] | None = None,
    max_retries: int = 3,
) -> tuple[BaseChatModel, ModelPerformanceTracker, ModelCostTracker]:
    """Create LLM with automatic fallback mechanism.

    This function creates an LLM instance with automatic fallback to alternative
    models if the primary model fails. It also initializes performance and cost
    tracking for the session.

    Fallback Logic:
        1. Try primary model specified by model_name
        2. On failure, try fallback models in order
        3. Default fallback order: claude-haiku-4-5 → gpt-4o-mini → gemini-2.5-flash
        4. Stop after max_retries attempts

    Args:
        model_name: Primary model name to attempt first
        temperature: Temperature parameter for response generation (default: 0.0)
        max_tokens: Maximum tokens in response (default: 8192)
        fallback_models: List of fallback models (default: None = use default chain)
        max_retries: Maximum number of retry attempts (default: 3)

    Returns:
        Tuple of (LLM instance, performance tracker, cost tracker)

    Raises:
        ValueError: If all models fail after max_retries attempts

    Examples:
        >>> # Successful creation with primary model
        >>> llm, perf, cost = create_llm_with_fallback("claude-haiku-4-5")
        >>> isinstance(llm, ChatAnthropic)
        True

        >>> # Custom fallback chain
        >>> llm, perf, cost = create_llm_with_fallback(
        ...     "gpt-4o",
        ...     fallback_models=["gpt-4o-mini", "gemini-2.5-flash"]
        ... )

        >>> # Using trackers
        >>> llm, perf, cost = create_llm_with_fallback("claude-haiku-4-5")
        >>> perf.start()
        >>> response = await llm.ainvoke([{"role": "user", "content": "Hello"}])
        >>> perf.end(success=True, input_tokens=10, output_tokens=5)
        >>> cost.add_call("claude-haiku-4-5", 10, 5)
        >>> perf.log_metrics()
        >>> cost.log_summary()
    """
    if fallback_models is None:
        # Default fallback chain: cost-optimized order
        fallback_models = [
            "claude-haiku-4-5",
            "gpt-4o-mini",
            "gemini-2.5-flash",
        ]

    # Build models-to-try list (primary + fallbacks, deduplicated)
    models_to_try = [model_name] + [m for m in fallback_models if m != model_name]

    # Initialize trackers
    perf_tracker = ModelPerformanceTracker(model_name)
    cost_tracker = ModelCostTracker()

    # Try each model in sequence
    for attempt, model in enumerate(models_to_try):
        if attempt >= max_retries:
            break

        try:
            logger.info(
                f"Attempting to create LLM: model={model} "
                f"(attempt={attempt + 1}/{max_retries})"
            )
            llm = create_llm(model, temperature, max_tokens)

            logger.info(f"Successfully created LLM: model={model}")
            perf_tracker.model_name = model  # Update to actual used model
            return llm, perf_tracker, cost_tracker

        except Exception as e:
            logger.warning(f"Failed to create LLM: model={model}, error={str(e)[:100]}")
            if attempt == len(models_to_try) - 1:
                # All models failed
                error_msg = (
                    f"All models failed after {max_retries} retries. "
                    f"Models tried: {models_to_try}. "
                    f"Last error: {str(e)}"
                )
                logger.error(error_msg)
                raise ValueError(error_msg) from e

    # Max retries exceeded
    error_msg = f"Max retries ({max_retries}) exceeded without success"
    logger.error(error_msg)
    raise ValueError(error_msg)
