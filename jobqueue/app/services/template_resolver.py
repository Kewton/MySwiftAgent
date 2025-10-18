"""Template variable resolver for task body templates."""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class TemplateResolverError(Exception):
    """Template resolution error."""

    pass


class TemplateResolver:
    """Service for resolving template variables in task bodies."""

    # Pattern for template variables: {{tasks[0].output_data.field.subfield}}
    VARIABLE_PATTERN = re.compile(
        r"\{\{tasks\[(\d+)\]\.(input_data|output_data)(\.[\w.]+)?\}\}"
    )

    @staticmethod
    def resolve_template(
        template: dict[str, Any] | str | list[Any] | None,
        tasks: list[Any],
    ) -> dict[str, Any] | str | list[Any] | None:
        """
        Resolve template variables in a template dict/string/list.

        Args:
            template: Template with variables ({{tasks[N].output_data.path}})
            tasks: List of task objects with input_data and output_data

        Returns:
            Resolved template with actual values

        Raises:
            TemplateResolverError: If variable resolution fails
        """
        if template is None:
            return None

        if isinstance(template, dict):
            return TemplateResolver._resolve_dict(template, tasks)
        elif isinstance(template, str):
            return TemplateResolver._resolve_string(template, tasks)
        elif isinstance(template, list):
            return TemplateResolver._resolve_list(template, tasks)
        else:
            return template

    @staticmethod
    def _resolve_dict(
        template_dict: dict[str, Any],
        tasks: list[Any],
    ) -> dict[str, Any]:
        """Resolve template variables in a dictionary."""
        resolved = {}
        for key, value in template_dict.items():
            resolved[key] = TemplateResolver.resolve_template(value, tasks)
        return resolved

    @staticmethod
    def _resolve_list(
        template_list: list[Any],
        tasks: list[Any],
    ) -> list[Any]:
        """Resolve template variables in a list."""
        return [
            TemplateResolver.resolve_template(item, tasks) for item in template_list
        ]

    @staticmethod
    def _resolve_string(
        template_str: str,
        tasks: list[Any],
    ) -> str | Any:
        """Resolve template variables in a string."""
        if not isinstance(template_str, str):
            return template_str

        # Find all variable matches
        matches = list(TemplateResolver.VARIABLE_PATTERN.finditer(template_str))

        if not matches:
            return template_str

        # If the entire string is a single variable, return the actual value (not string)
        if len(matches) == 1 and matches[0].group(0) == template_str:
            return TemplateResolver._get_variable_value(matches[0], tasks)

        # Replace all variables in the string
        result = template_str
        for match in reversed(matches):  # Reverse to maintain positions
            value = TemplateResolver._get_variable_value(match, tasks)
            # Convert value to string for replacement
            value_str = str(value) if value is not None else ""
            result = result[: match.start()] + value_str + result[match.end() :]

        return result

    @staticmethod
    def _get_variable_value(match: re.Match[str], tasks: list[Any]) -> Any:
        """Extract value from task based on variable pattern."""
        task_index = int(match.group(1))
        data_type = match.group(2)  # input_data or output_data
        path = match.group(3)  # .field.subfield or None

        # Validate task index
        if task_index >= len(tasks):
            error_msg = (
                f"Task index {task_index} out of range (available: 0-{len(tasks) - 1})"
            )
            logger.error(error_msg)
            raise TemplateResolverError(error_msg)

        task = tasks[task_index]

        # Get data dict (input_data or output_data)
        data = getattr(task, data_type, None)
        if data is None:
            error_msg = f"Task {task_index} has no {data_type}"
            logger.warning(error_msg)
            return None

        # If no path, return entire data
        if not path:
            return data

        # Navigate through path (.field.subfield)
        current = data
        field_names = path.strip(".").split(".")

        for field in field_names:
            if isinstance(current, dict):
                current = current.get(field)
                if current is None:
                    logger.warning(
                        f"Field '{field}' not found in task {task_index}.{data_type}"
                    )
                    return None
            else:
                error_msg = f"Cannot access field '{field}' in non-dict value"
                logger.error(error_msg)
                raise TemplateResolverError(error_msg)

        return current

    @staticmethod
    def has_template_variables(
        template: dict[str, Any] | str | list[Any] | None,
    ) -> bool:
        """
        Check if template contains any template variables.

        Args:
            template: Template to check

        Returns:
            True if template variables exist
        """
        if template is None:
            return False

        if isinstance(template, dict):
            return any(
                TemplateResolver.has_template_variables(value)
                for value in template.values()
            )
        elif isinstance(template, str):
            return bool(TemplateResolver.VARIABLE_PATTERN.search(template))
        elif isinstance(template, list):
            return any(
                TemplateResolver.has_template_variables(item) for item in template
            )
        else:
            return False
