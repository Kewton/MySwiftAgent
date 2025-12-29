"""Template variable pattern definitions (shared by Resolver and Validator)."""

import re


class TemplatePatterns:
    """Template variable regex patterns.

    DRY principle: These patterns are shared between TemplateResolver
    and TemplateValidator to ensure consistency.
    """

    # Task reference: {{tasks[N].output_data.field}} or {{tasks[N].input_data.field}}
    TASK_VARIABLE = re.compile(
        r"\{\{tasks\[(\d+)\]\.(input_data|output_data)(\.[\w.]+)?\}\}"
    )

    # Job reference: {{job.body.field}} or {{job.input_data.field}}
    JOB_VARIABLE = re.compile(r"\{\{job\.(body|input_data)(\.[\w.]+)?\}\}")

    # Current task reference: {{task.input_data.field}}
    CURRENT_TASK_VARIABLE = re.compile(r"\{\{task\.(input_data)(\.[\w.]+)?\}\}")

    # Combined pattern for detecting any template variable
    ANY_VARIABLE = re.compile(
        r"\{\{(tasks\[\d+\]|job|task)\.(input_data|output_data|body)(\.[\w.]+)?\}\}"
    )

    @classmethod
    def extract_all_variables(cls, text: str) -> list[str]:
        """Extract all template variables from a string.

        Args:
            text: String potentially containing template variables

        Returns:
            List of matched template variable strings
        """
        variables: list[str] = []

        # Task variables
        for match in cls.TASK_VARIABLE.finditer(text):
            variables.append(match.group(0))

        # Job variables
        for match in cls.JOB_VARIABLE.finditer(text):
            variables.append(match.group(0))

        # Current task variables
        for match in cls.CURRENT_TASK_VARIABLE.finditer(text):
            variables.append(match.group(0))

        return variables

    @classmethod
    def has_variables(cls, text: str) -> bool:
        """Check if text contains any template variables.

        Args:
            text: String to check

        Returns:
            True if template variables are present
        """
        return bool(cls.ANY_VARIABLE.search(text))

    @classmethod
    def get_path_depth(cls, variable: str) -> int:
        """Get the nesting depth of a variable's path.

        Args:
            variable: Template variable string

        Returns:
            Path depth (number of dots in path)
        """
        # Extract path portion (e.g., ".field.subfield" from the variable)
        for pattern in [cls.TASK_VARIABLE, cls.JOB_VARIABLE, cls.CURRENT_TASK_VARIABLE]:
            match = pattern.match(variable)
            if match:
                path = match.group(match.lastindex) if match.lastindex else ""
                if path:
                    return path.count(".")
                return 0
        return 0
