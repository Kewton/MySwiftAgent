"""Interface Compatibility Checker component for validating task interfaces."""

from typing import Any

import streamlit as st


class InterfaceCompatibilityChecker:
    """Interface compatibility validation component for task sequences."""

    @staticmethod
    def check_compatibility(
        selected_tasks: list[dict[str, Any]],
        interfaces: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Check interface compatibility between consecutive tasks.

        Args:
            selected_tasks: List of selected tasks with interface IDs: [{
                "master_id": "tm_01ABC...",
                "sequence": 0,
                "name": "Task Name",
                "input_interface_id": "if_01XYZ..." | None,
                "output_interface_id": "if_01XYZ..." | None,
            }]
            interfaces: Optional dict of interface details keyed by interface_id
                Format: {
                    "if_01XYZ...": {
                        "id": "if_01XYZ...",
                        "name": "Interface Name",
                        "input_schema": {...},
                        "output_schema": {...}
                    }
                }

        Returns:
            Compatibility check result: {
                "is_compatible": bool,
                "issues": [
                    {
                        "type": "error" | "warning",
                        "task_index": int,
                        "task_name": str,
                        "message": str,
                    }
                ],
                "summary": str
            }
        """
        issues = []

        # Check if tasks are provided
        if not selected_tasks:
            return {
                "is_compatible": True,
                "issues": [],
                "summary": "No tasks to validate",
            }

        # Single task - no interface compatibility check needed
        if len(selected_tasks) == 1:
            # Check if single task has required interfaces
            task = selected_tasks[0]
            if not task.get("input_interface_id"):
                issues.append(
                    {
                        "type": "warning",
                        "task_index": 0,
                        "task_name": task["name"],
                        "message": "Task has no input interface defined",
                    },
                )
            if not task.get("output_interface_id"):
                issues.append(
                    {
                        "type": "warning",
                        "task_index": 0,
                        "task_name": task["name"],
                        "message": "Task has no output interface defined",
                    },
                )

            return {
                "is_compatible": True,
                "issues": issues,
                "summary": "Single task - no compatibility check needed",
            }

        # Check consecutive task pairs
        for i in range(len(selected_tasks) - 1):
            current_task = selected_tasks[i]
            next_task = selected_tasks[i + 1]

            current_output = current_task.get("output_interface_id")
            next_input = next_task.get("input_interface_id")

            # Case 1: Both interfaces are None - warning
            if not current_output and not next_input:
                issues.append(
                    {
                        "type": "warning",
                        "task_index": i,
                        "task_name": f"{current_task['name']} → {next_task['name']}",
                        "message": "Neither task has interface definitions. Data compatibility cannot be verified.",
                    },
                )
                continue

            # Case 2: Current task has no output interface - warning
            if not current_output:
                issues.append(
                    {
                        "type": "warning",
                        "task_index": i,
                        "task_name": current_task["name"],
                        "message": f"Task has no output interface, but next task '{next_task['name']}' expects input interface `{next_input}`",
                    },
                )
                continue

            # Case 3: Next task has no input interface - warning
            if not next_input:
                issues.append(
                    {
                        "type": "warning",
                        "task_index": i + 1,
                        "task_name": next_task["name"],
                        "message": f"Task has no input interface, but previous task '{current_task['name']}' outputs interface `{current_output}`",
                    },
                )
                continue

            # Case 4: Both interfaces exist - check compatibility
            if current_output != next_input:
                # Get interface names if available
                current_output_name = current_output
                next_input_name = next_input

                if interfaces:
                    current_interface = interfaces.get(current_output, {})
                    next_interface = interfaces.get(next_input, {})
                    current_output_name = f"{current_interface.get('name', current_output)} ({current_output})"
                    next_input_name = (
                        f"{next_interface.get('name', next_input)} ({next_input})"
                    )

                issues.append(
                    {
                        "type": "error",
                        "task_index": i,
                        "task_name": f"{current_task['name']} → {next_task['name']}",
                        "message": f"Interface mismatch: Output `{current_output_name}` ≠ Input `{next_input_name}`",
                    },
                )

        # Determine overall compatibility
        has_errors = any(issue["type"] == "error" for issue in issues)
        is_compatible = not has_errors

        # Generate summary
        if not issues:
            summary = f"✅ All {len(selected_tasks)} tasks are compatible"
        else:
            error_count = sum(1 for issue in issues if issue["type"] == "error")
            warning_count = sum(1 for issue in issues if issue["type"] == "warning")

            summary_parts = []
            if error_count > 0:
                summary_parts.append(f"❌ {error_count} error(s)")
            if warning_count > 0:
                summary_parts.append(f"⚠️ {warning_count} warning(s)")

            summary = ", ".join(summary_parts)

        return {
            "is_compatible": is_compatible,
            "issues": issues,
            "summary": summary,
        }

    @staticmethod
    def render_compatibility_result(
        compatibility_result: dict[str, Any],
    ) -> None:
        """
        Render compatibility check result with visual indicators.

        Args:
            compatibility_result: Result from check_compatibility()
        """
        st.subheader("🔍 Interface Compatibility Check")

        # Overall status
        is_compatible = compatibility_result["is_compatible"]
        summary = compatibility_result["summary"]
        issues = compatibility_result["issues"]

        if is_compatible:
            st.success(f"✅ {summary}")
        else:
            st.error(f"❌ {summary}")

        # Display issues if any
        if issues:
            st.caption("Issues found:")

            for issue in issues:
                issue_type = issue["type"]
                task_name = issue["task_name"]
                message = issue["message"]

                if issue_type == "error":
                    st.error(f"**Error**: {task_name}")
                    st.markdown(f"↳ {message}")
                elif issue_type == "warning":
                    st.warning(f"**Warning**: {task_name}")
                    st.markdown(f"↳ {message}")

            # Recommendations
            st.divider()
            st.subheader("💡 Recommendations")

            error_count = sum(1 for issue in issues if issue["type"] == "error")
            warning_count = sum(1 for issue in issues if issue["type"] == "warning")

            if error_count > 0:
                st.markdown(
                    """
                    **Interface Mismatches Detected:**
                    - Add an intermediate transformation task to convert data formats
                    - Update TaskMaster interface definitions to match
                    - Verify that the task sequence is correct
                    """,
                )

            if warning_count > 0:
                st.markdown(
                    """
                    **Missing Interface Definitions:**
                    - Define input/output interfaces for TaskMasters
                    - This ensures data compatibility validation
                    - Interfaces help document expected data formats
                    """,
                )
        else:
            st.info("ℹ️ No issues found. All task interfaces are compatible.")

    @staticmethod
    def render_inline_compatibility_check(
        selected_tasks: list[dict[str, Any]],
        interfaces: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Render inline compatibility check (compact version).

        Args:
            selected_tasks: List of selected tasks
            interfaces: Optional dict of interface details

        Returns:
            Compatibility check result
        """
        compatibility_result = InterfaceCompatibilityChecker.check_compatibility(
            selected_tasks,
            interfaces,
        )

        if not selected_tasks or len(selected_tasks) < 2:
            return compatibility_result

        # Compact display
        is_compatible = compatibility_result["is_compatible"]
        summary = compatibility_result["summary"]

        if is_compatible:
            st.success(f"✅ Interface Compatibility: {summary}")
        else:
            st.error(f"❌ Interface Compatibility: {summary}")

            # Show first 3 issues
            issues = compatibility_result["issues"]
            errors = [issue for issue in issues if issue["type"] == "error"]

            if errors:
                with st.expander("⚠️ View Compatibility Issues", expanded=False):
                    for error in errors[:3]:
                        st.error(f"**{error['task_name']}**")
                        st.markdown(f"↳ {error['message']}")

                    if len(errors) > 3:
                        st.info(f"... and {len(errors) - 3} more issues")

        return compatibility_result
