"""Error definitions for Registration workflow.

This module defines custom exceptions for the registration workflow.

Bug Fix: 20260126_email_not_sent
- LLM changed field names (email -> recipient_email)
- Added UserInputFieldMismatchError to fail fast on field mismatches
"""

from __future__ import annotations


class UserInputFieldMismatchError(Exception):
    """Exception raised when a required field is not found in user_input_schema.

    This error is raised when the LLM generates inconsistent field names,
    e.g., using 'recipient_email' when the user input expects 'email'.

    Attributes:
        field_name: The field name that was not found
        available_fields: List of valid field names in user_input_schema
    """

    def __init__(
        self,
        field_name: str,
        available_fields: list[str],
        message: str | None = None,
    ):
        self.field_name = field_name
        self.available_fields = available_fields

        if message is None:
            message = (
                f"Field '{field_name}' not found in user_input_schema. "
                f"Available fields: {sorted(available_fields)}. "
                f"The LLM may have generated inconsistent field names. "
                f"Ensure field names match the original user requirement."
            )

        super().__init__(message)

    def __str__(self) -> str:
        return super().__str__()
