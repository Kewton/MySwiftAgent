"""AgentConstraintValidator for validating agent-specific constraints.

Issue #342 Task 1.3: AgentConstraintValidator implementation.

This module validates agent-specific constraints:
- stringTemplateAgent: No JavaScript expressions (JSON.stringify, .map(), etc.)
- fetchAgent: Timeout in milliseconds, no environment variables in URLs

ReDoS protection is implemented through:
- Input length limits
- Non-backtracking patterns
- Pattern length limits in regex
"""

from __future__ import annotations

import re
from typing import Any

from aiagent.langgraph.jobGeneratorV2.validators import (
    ValidationError,
    ValidationErrorCode,
    WorkflowValidator,
)

# Maximum template length to prevent ReDoS
MAX_TEMPLATE_LENGTH = 10000

# Timeout constraints for fetchAgent (in milliseconds)
MIN_TIMEOUT_MS = 1000  # 1 second minimum
MAX_TIMEOUT_MS = 300000  # 5 minutes maximum
LIKELY_SECONDS_THRESHOLD = 500  # Values below this are likely seconds not ms

# Safe patterns for detecting JavaScript expressions in templates
# These patterns have bounded repetition to prevent ReDoS
JS_PATTERNS = [
    # JSON methods
    re.compile(r"\$\{[^}]{0,200}JSON\.stringify[^}]{0,200}\}"),
    re.compile(r"\$\{[^}]{0,200}JSON\.parse[^}]{0,200}\}"),
    # Array methods
    re.compile(r"\$\{[^}]{0,200}\.map\s*\([^}]{0,100}\)\}"),
    re.compile(r"\$\{[^}]{0,200}\.filter\s*\([^}]{0,100}\)\}"),
    re.compile(r"\$\{[^}]{0,200}\.reduce\s*\([^}]{0,100}\)\}"),
    re.compile(r"\$\{[^}]{0,200}\.forEach\s*\([^}]{0,100}\)\}"),
    re.compile(r"\$\{[^}]{0,200}\.find\s*\([^}]{0,100}\)\}"),
    # Object methods
    re.compile(r"\$\{[^}]{0,200}Object\.keys[^}]{0,100}\}"),
    re.compile(r"\$\{[^}]{0,200}Object\.values[^}]{0,100}\}"),
    re.compile(r"\$\{[^}]{0,200}Object\.entries[^}]{0,100}\}"),
    # String methods
    re.compile(r"\$\{[^}]{0,200}\.toLowerCase\s*\(\)[^}]{0,50}\}"),
    re.compile(r"\$\{[^}]{0,200}\.toUpperCase\s*\(\)[^}]{0,50}\}"),
    re.compile(r"\$\{[^}]{0,200}\.trim\s*\(\)[^}]{0,50}\}"),
    re.compile(r"\$\{[^}]{0,200}\.split\s*\([^}]{0,50}\)\}"),
    re.compile(r"\$\{[^}]{0,200}\.join\s*\([^}]{0,50}\)\}"),
    # Arrow functions
    re.compile(r"\$\{[^}]{0,200}=>[^}]{0,100}\}"),
]

# Environment variable patterns in URLs
ENV_VAR_PATTERNS = [
    re.compile(r"\$\{[A-Z_][A-Z0-9_]*\}"),  # ${ENV_VAR}
    re.compile(r"\{\{[A-Z_][A-Z0-9_]*\}\}"),  # {{ENV_VAR}}
    re.compile(r"%[A-Z_][A-Z0-9_]*%"),  # %ENV_VAR%
]


class AgentConstraintValidator(WorkflowValidator):
    """Validator for agent-specific constraints.

    Validates:
    - stringTemplateAgent templates (no JavaScript)
    - fetchAgent timeouts (milliseconds) and URLs (no env vars)
    """

    def validate_string_template_agent(
        self,
        config: dict[str, Any],
    ) -> list[str]:
        """Validate stringTemplateAgent configuration.

        Args:
            config: Node configuration dictionary

        Returns:
            List of error messages
        """
        errors: list[str] = []

        params = config.get("params", {})
        template = params.get("template", "")

        if not template:
            return errors

        # Check template length
        if len(template) > MAX_TEMPLATE_LENGTH:
            errors.append(
                f"Template too long ({len(template)} chars). "
                f"Maximum allowed: {MAX_TEMPLATE_LENGTH}"
            )
            return errors  # Skip pattern matching for very long templates

        # Check for JavaScript expressions
        for pattern in JS_PATTERNS:
            if pattern.search(template):
                errors.append(
                    "JavaScript expression detected in stringTemplateAgent template. "
                    "stringTemplateAgent only supports simple ${variable} substitution. "
                    "Use /utility/json_stringify API to convert objects to strings."
                )
                break  # Only report once

        return errors

    def validate_fetch_agent(
        self,
        config: dict[str, Any],
    ) -> list[str]:
        """Validate fetchAgent configuration.

        Args:
            config: Node configuration dictionary

        Returns:
            List of error messages
        """
        errors: list[str] = []

        # Validate timeout
        timeout = config.get("timeout")
        if timeout is not None:
            if isinstance(timeout, (int, float)):
                if timeout < LIKELY_SECONDS_THRESHOLD:
                    errors.append(
                        f"Timeout value {timeout} is likely in seconds, not milliseconds. "
                        f"GraphAI uses milliseconds. Use {int(timeout * 1000)} instead "
                        f"(minimum: {MIN_TIMEOUT_MS}ms)."
                    )
                elif timeout < MIN_TIMEOUT_MS:
                    errors.append(
                        f"Timeout {timeout}ms is too small. "
                        f"Minimum recommended: {MIN_TIMEOUT_MS}ms."
                    )
                elif timeout > MAX_TIMEOUT_MS:
                    errors.append(
                        f"Timeout {timeout}ms is too large. "
                        f"Maximum recommended: {MAX_TIMEOUT_MS}ms (5 minutes)."
                    )

        # Validate URL for environment variables
        inputs = config.get("inputs", {})
        url = inputs.get("url", "")

        if isinstance(url, str) and url:
            for pattern in ENV_VAR_PATTERNS:
                if pattern.search(url):
                    errors.append(
                        f"URL contains environment variable: '{url}'. "
                        "GraphAI does not resolve environment variables at runtime. "
                        "Use a literal URL like 'http://localhost:8004/api'."
                    )
                    break

        return errors

    def validate_node(
        self,
        node_name: str,
        node_def: dict[str, Any],
    ) -> list[str]:
        """Validate a single node.

        Args:
            node_name: Name of the node
            node_def: Node definition dictionary

        Returns:
            List of error messages
        """
        errors: list[str] = []

        agent = node_def.get("agent", "")

        if agent == "stringTemplateAgent":
            template_errors = self.validate_string_template_agent(node_def)
            errors.extend([f"[{node_name}] {e}" for e in template_errors])

        elif agent == "fetchAgent":
            fetch_errors = self.validate_fetch_agent(node_def)
            errors.extend([f"[{node_name}] {e}" for e in fetch_errors])

        return errors

    def validate_workflow(
        self,
        workflow: dict[str, Any],
    ) -> list[str]:
        """Validate all agents in a workflow.

        Args:
            workflow: Workflow dictionary

        Returns:
            List of error messages
        """
        errors: list[str] = []
        nodes = workflow.get("nodes", {})

        for node_name, node_def in nodes.items():
            if node_name == "source":
                continue

            if not isinstance(node_def, dict):
                continue

            node_errors = self.validate_node(node_name, node_def)
            errors.extend(node_errors)

        return errors

    def validate(
        self,
        workflow: dict[str, Any],
    ) -> list[ValidationError]:
        """Validate workflow and return ValidationError objects.

        Args:
            workflow: Workflow dictionary

        Returns:
            List of ValidationError objects
        """
        validation_errors: list[ValidationError] = []
        nodes = workflow.get("nodes", {})

        for node_name, node_def in nodes.items():
            if node_name == "source":
                continue

            if not isinstance(node_def, dict):
                continue

            agent = node_def.get("agent", "")

            # Validate stringTemplateAgent
            if agent == "stringTemplateAgent":
                errors = self._validate_string_template_errors(node_name, node_def)
                validation_errors.extend(errors)

            # Validate fetchAgent
            elif agent == "fetchAgent":
                errors = self._validate_fetch_agent_errors(node_name, node_def)
                validation_errors.extend(errors)

        return validation_errors

    def _validate_string_template_errors(
        self,
        node_name: str,
        node_def: dict[str, Any],
    ) -> list[ValidationError]:
        """Validate stringTemplateAgent and return ValidationError objects.

        Args:
            node_name: Name of the node
            node_def: Node definition dictionary

        Returns:
            List of ValidationError objects
        """
        errors: list[ValidationError] = []

        params = node_def.get("params", {})
        template = params.get("template", "")

        if not template:
            return errors

        # Check template length
        if len(template) > MAX_TEMPLATE_LENGTH:
            errors.append(
                ValidationError(
                    code=ValidationErrorCode.VALIDATION_FAILED,
                    message=f"Template too long ({len(template)} chars)",
                    location=f"nodes.{node_name}.params.template",
                    suggestion=f"Keep template under {MAX_TEMPLATE_LENGTH} characters",
                    severity="major",
                )
            )
            return errors

        # Check for JavaScript expressions
        for pattern in JS_PATTERNS:
            if pattern.search(template):
                errors.append(
                    ValidationError(
                        code=ValidationErrorCode.JS_IN_TEMPLATE,
                        message=(
                            "JavaScript expression detected in stringTemplateAgent template. "
                            "stringTemplateAgent only supports simple ${variable} substitution."
                        ),
                        location=f"nodes.{node_name}.params.template",
                        suggestion=(
                            "Use /utility/json_stringify API to convert objects to strings, "
                            "then reference the result in the template."
                        ),
                        severity="critical",
                    )
                )
                break

        return errors

    def _validate_fetch_agent_errors(
        self,
        node_name: str,
        node_def: dict[str, Any],
    ) -> list[ValidationError]:
        """Validate fetchAgent and return ValidationError objects.

        Args:
            node_name: Name of the node
            node_def: Node definition dictionary

        Returns:
            List of ValidationError objects
        """
        errors: list[ValidationError] = []

        # Validate timeout
        timeout = node_def.get("timeout")
        if timeout is not None:
            if isinstance(timeout, (int, float)):
                if timeout < LIKELY_SECONDS_THRESHOLD:
                    errors.append(
                        ValidationError(
                            code=ValidationErrorCode.INVALID_TIMEOUT,
                            message=(
                                f"Timeout value {timeout} is likely in seconds, not milliseconds"
                            ),
                            location=f"nodes.{node_name}.timeout",
                            suggestion=(
                                f"Use {int(timeout * 1000)} (milliseconds). "
                                f"Minimum: {MIN_TIMEOUT_MS}ms"
                            ),
                            severity="critical",
                        )
                    )
                elif timeout < MIN_TIMEOUT_MS:
                    errors.append(
                        ValidationError(
                            code=ValidationErrorCode.INVALID_TIMEOUT,
                            message=f"Timeout {timeout}ms is too small",
                            location=f"nodes.{node_name}.timeout",
                            suggestion=f"Use at least {MIN_TIMEOUT_MS}ms",
                            severity="major",
                        )
                    )
                elif timeout > MAX_TIMEOUT_MS:
                    errors.append(
                        ValidationError(
                            code=ValidationErrorCode.INVALID_TIMEOUT,
                            message=f"Timeout {timeout}ms is too large",
                            location=f"nodes.{node_name}.timeout",
                            suggestion=f"Use at most {MAX_TIMEOUT_MS}ms (5 minutes)",
                            severity="major",
                        )
                    )

        # Validate URL
        inputs = node_def.get("inputs", {})
        url = inputs.get("url", "")

        if isinstance(url, str) and url:
            for pattern in ENV_VAR_PATTERNS:
                if pattern.search(url):
                    errors.append(
                        ValidationError(
                            code=ValidationErrorCode.ENV_VAR_IN_URL,
                            message=f"URL contains environment variable: '{url}'",
                            location=f"nodes.{node_name}.inputs.url",
                            suggestion=(
                                "Use literal URL like 'http://localhost:8004/api'. "
                                "GraphAI does not resolve environment variables."
                            ),
                            severity="critical",
                        )
                    )
                    break

        return errors


# Export
__all__ = ["AgentConstraintValidator"]
