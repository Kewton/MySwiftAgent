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

    # Pattern for job variables: {{job.body.field}} or {{job.input_data.field}}
    JOB_VARIABLE_PATTERN = re.compile(r"\{\{job\.(body|input_data)(\.[\w.]+)?\}\}")

    # Pattern for current task variables: {{task.input_data.field}}
    CURRENT_TASK_PATTERN = re.compile(r"\{\{task\.(input_data)(\.[\w.]+)?\}\}")

    # Combined pattern for has_template_variables detection
    ANY_VARIABLE_PATTERN = re.compile(
        r"\{\{(tasks\[\d+\]|job|task)\.(input_data|output_data|body)(\.[\w.]+)?\}\}"
    )

    @staticmethod
    def resolve_template(
        template: dict[str, Any] | str | list[Any] | None,
        tasks: list[Any],
        job: Any | None = None,
        current_task: Any | None = None,
    ) -> dict[str, Any] | str | list[Any] | None:
        """
        Resolve template variables in a template dict/string/list.

        Args:
            template: Template with variables ({{tasks[N].output_data.path}})
            tasks: List of task objects with input_data and output_data
            job: Optional job object with body and input_data attributes
            current_task: Optional current task object with input_data attribute

        Returns:
            Resolved template with actual values

        Raises:
            TemplateResolverError: If variable resolution fails

        Supported variables:
            - {{tasks[N].output_data}} - output from task N
            - {{tasks[N].output_data.field}} - specific field from task N output
            - {{tasks[N].input_data}} - input to task N
            - {{job.body}} - entire job body
            - {{job.body.field}} - specific field from job body
            - {{job.input_data}} - job input data
            - {{task.input_data}} - current task's input data
        """
        if template is None:
            return None

        if isinstance(template, dict):
            return TemplateResolver._resolve_dict(template, tasks, job, current_task)
        elif isinstance(template, str):
            return TemplateResolver._resolve_string(template, tasks, job, current_task)
        elif isinstance(template, list):
            return TemplateResolver._resolve_list(template, tasks, job, current_task)
        else:
            return template

    @staticmethod
    def _resolve_dict(
        template_dict: dict[str, Any],
        tasks: list[Any],
        job: Any | None = None,
        current_task: Any | None = None,
    ) -> dict[str, Any]:
        """Resolve template variables in a dictionary."""
        resolved = {}
        for key, value in template_dict.items():
            resolved[key] = TemplateResolver.resolve_template(
                value, tasks, job, current_task
            )
        return resolved

    @staticmethod
    def _resolve_list(
        template_list: list[Any],
        tasks: list[Any],
        job: Any | None = None,
        current_task: Any | None = None,
    ) -> list[Any]:
        """Resolve template variables in a list."""
        return [
            TemplateResolver.resolve_template(item, tasks, job, current_task)
            for item in template_list
        ]

    @staticmethod
    def _resolve_string(
        template_str: str,
        tasks: list[Any],
        job: Any | None = None,
        current_task: Any | None = None,
    ) -> str | Any:
        """Resolve template variables in a string."""
        if not isinstance(template_str, str):
            return template_str

        # Collect all matches from all patterns
        all_matches: list[tuple[re.Match[str], str]] = []

        # Task variable matches
        for match in TemplateResolver.VARIABLE_PATTERN.finditer(template_str):
            all_matches.append((match, "task_ref"))

        # Job variable matches
        for match in TemplateResolver.JOB_VARIABLE_PATTERN.finditer(template_str):
            all_matches.append((match, "job"))

        # Current task variable matches
        for match in TemplateResolver.CURRENT_TASK_PATTERN.finditer(template_str):
            all_matches.append((match, "current_task"))

        if not all_matches:
            return template_str

        # Sort by start position
        all_matches.sort(key=lambda x: x[0].start())

        # If the entire string is a single variable, return the actual value (not string)
        if len(all_matches) == 1 and all_matches[0][0].group(0) == template_str:
            match, match_type = all_matches[0]
            return TemplateResolver._get_value_by_type(
                match, match_type, tasks, job, current_task
            )

        # Replace all variables in the string (reverse order to maintain positions)
        result = template_str
        for match, match_type in reversed(all_matches):
            value = TemplateResolver._get_value_by_type(
                match, match_type, tasks, job, current_task
            )
            # Convert value to string for replacement
            value_str = str(value) if value is not None else ""
            result = result[: match.start()] + value_str + result[match.end() :]

        return result

    @staticmethod
    def _get_value_by_type(
        match: re.Match[str],
        match_type: str,
        tasks: list[Any],
        job: Any | None,
        current_task: Any | None,
    ) -> Any:
        """Get variable value based on match type."""
        if match_type == "task_ref":
            return TemplateResolver._get_variable_value(match, tasks)
        elif match_type == "job":
            return TemplateResolver._get_job_variable_value(match, job)
        elif match_type == "current_task":
            return TemplateResolver._get_current_task_variable_value(
                match, current_task
            )
        return None

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
    def _navigate_path(data: Any, path: str, context: str) -> Any:
        """Navigate through a dot-separated path in a dict.

        Args:
            data: Starting data (should be dict)
            path: Dot-separated path like ".field.subfield"
            context: Context string for error messages

        Returns:
            Value at path, or None if not found
        """
        if not path:
            return data

        current = data
        field_names = path.strip(".").split(".")

        for field in field_names:
            if isinstance(current, dict):
                current = current.get(field)
                if current is None:
                    logger.warning(f"Field '{field}' not found in {context}")
                    return None
            else:
                error_msg = f"Cannot access field '{field}' in non-dict value"
                logger.error(error_msg)
                raise TemplateResolverError(error_msg)

        return current

    @staticmethod
    def _get_job_variable_value(match: re.Match[str], job: Any | None) -> Any:
        """Extract value from job based on variable pattern.

        Supports:
        - {{job.body}} - entire body dict
        - {{job.body.user_input}} - specific field
        - {{job.input_data}} - entire input_data dict
        - {{job.input_data.field}} - specific field
        """
        if job is None:
            logger.warning("Job is None, cannot resolve job variable")
            return None

        data_type = match.group(1)  # body or input_data
        path = match.group(2)  # .field.subfield or None

        # Get data dict (body or input_data)
        data = getattr(job, data_type, None)
        if data is None:
            logger.warning(f"Job has no {data_type}")
            return None

        # If no path, return entire data
        if not path:
            return data

        return TemplateResolver._navigate_path(data, path, f"job.{data_type}")

    @staticmethod
    def _get_current_task_variable_value(
        match: re.Match[str], current_task: Any | None
    ) -> Any:
        """Extract value from current task based on variable pattern.

        Supports:
        - {{task.input_data}} - entire input_data dict
        - {{task.input_data.field}} - specific field
        """
        if current_task is None:
            logger.warning("Current task is None, cannot resolve task variable")
            return None

        data_type = match.group(1)  # input_data
        path = match.group(2)  # .field.subfield or None

        data = getattr(current_task, data_type, None)
        if data is None:
            logger.warning(f"Current task has no {data_type}")
            return None

        if not path:
            return data

        return TemplateResolver._navigate_path(data, path, f"task.{data_type}")

    @staticmethod
    def has_template_variables(
        template: dict[str, Any] | str | list[Any] | None,
    ) -> bool:
        """
        Check if template contains any template variables.

        Detects all supported variable patterns:
        - {{tasks[N].output_data}} / {{tasks[N].input_data}}
        - {{job.body}} / {{job.input_data}}
        - {{task.input_data}}

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
            # Use ANY_VARIABLE_PATTERN to detect all variable types
            return bool(TemplateResolver.ANY_VARIABLE_PATTERN.search(template))
        elif isinstance(template, list):
            return any(
                TemplateResolver.has_template_variables(item) for item in template
            )
        else:
            return False
