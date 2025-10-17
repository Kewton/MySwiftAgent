"""Task Selector component for selecting and ordering TaskMasters."""

from typing import Any, cast

import streamlit as st


class TaskSelector:
    """Task selection and ordering UI component for Job creation."""

    @staticmethod
    def render_task_selector(
        available_tasks: list[dict[str, Any]],
        key_prefix: str = "task_selector",
    ) -> list[dict[str, Any]]:
        """
        Render Task selection and ordering UI.

        Args:
            available_tasks: List of available TaskMasters from API
                Expected format: [{
                    "id": "tm_01ABC...",
                    "name": "Task Name",
                    "description": "...",
                    "input_interface_id": "if_01XYZ..." | None,
                    "output_interface_id": "if_01XYZ..." | None,
                    ...
                }]
            key_prefix: Prefix for session state keys (default: "task_selector")

        Returns:
            List of selected tasks with sequence numbers: [{
                "master_id": "tm_01ABC...",
                "sequence": 0,
                "name": "Task Name",
                "input_interface_id": "if_01XYZ..." | None,
                "output_interface_id": "if_01XYZ..." | None,
            }]
        """
        # Initialize session state
        selected_tasks_key = f"{key_prefix}_selected_tasks"
        if selected_tasks_key not in st.session_state:
            st.session_state[selected_tasks_key] = []

        st.subheader("📋 Task Selection")
        st.caption(
            "Select TaskMasters to execute in sequence. "
            "Interface compatibility will be checked automatically.",
        )

        # Task selection dropdown
        if available_tasks:
            # Create task options for selectbox
            task_options = ["(Select a task to add)"] + [
                f"{task['name']} ({task['id']})" for task in available_tasks
            ]

            col1, col2 = st.columns([4, 1])

            with col1:
                selected_option = st.selectbox(
                    "Available TaskMasters",
                    task_options,
                    key=f"{key_prefix}_selectbox",
                    help="Select a TaskMaster to add to the execution sequence",
                )

            with col2:
                add_button = st.button(
                    "➕ Add Task",
                    use_container_width=True,
                    key=f"{key_prefix}_add_button",
                )

            # Add selected task
            if add_button and selected_option != "(Select a task to add)":
                # Extract task ID from option (format: "Name (tm_01ABC...)")
                task_id = selected_option.split("(")[-1].rstrip(")")

                # Find task details
                task = next((t for t in available_tasks if t["id"] == task_id), None)

                if task:
                    # Check if task is already selected
                    if task_id not in [
                        t["master_id"] for t in st.session_state[selected_tasks_key]
                    ]:
                        # Add task to selected list
                        st.session_state[selected_tasks_key].append(
                            {
                                "master_id": task["id"],
                                "sequence": len(st.session_state[selected_tasks_key]),
                                "name": task["name"],
                                "description": task.get("description"),
                                "input_interface_id": task.get("input_interface_id"),
                                "output_interface_id": task.get("output_interface_id"),
                            },
                        )
                        st.success(f"✅ Added: {task['name']}")
                        st.rerun()
                    else:
                        st.warning(f"⚠️ Task '{task['name']}' is already selected")

        else:
            st.info("ℹ️ No TaskMasters available. Please create TaskMasters first.")

        # Display selected tasks
        selected_tasks = st.session_state[selected_tasks_key]

        if selected_tasks:
            st.divider()
            st.subheader(f"🔢 Selected Tasks ({len(selected_tasks)})")
            st.caption("Tasks will be executed in the order shown below")

            # Render each selected task
            for idx, task in enumerate(selected_tasks):
                with st.container():
                    col1, col2, col3, col4 = st.columns([1, 5, 2, 2])

                    with col1:
                        st.markdown(f"**#{idx + 1}**")

                    with col2:
                        st.markdown(f"**{task['name']}**")
                        if task.get("description"):
                            st.caption(task["description"])

                        # Display Interface info
                        interface_info = []
                        if task.get("input_interface_id"):
                            interface_info.append(
                                f"📥 Input: `{task['input_interface_id']}`",
                            )
                        else:
                            interface_info.append("📥 Input: None")

                        if task.get("output_interface_id"):
                            interface_info.append(
                                f"📤 Output: `{task['output_interface_id']}`",
                            )
                        else:
                            interface_info.append("📤 Output: None")

                        st.caption(" | ".join(interface_info))

                    with col3:
                        # Move up/down buttons
                        col_up, col_down = st.columns(2)

                        with col_up:
                            if idx > 0:
                                if st.button(
                                    "⬆️",
                                    key=f"{key_prefix}_move_up_{idx}",
                                    help="Move up",
                                    use_container_width=True,
                                ):
                                    # Swap with previous task
                                    (
                                        st.session_state[selected_tasks_key][idx],
                                        st.session_state[selected_tasks_key][idx - 1],
                                    ) = (
                                        st.session_state[selected_tasks_key][idx - 1],
                                        st.session_state[selected_tasks_key][idx],
                                    )
                                    # Update sequence numbers
                                    for i, t in enumerate(
                                        st.session_state[selected_tasks_key],
                                    ):
                                        t["sequence"] = i
                                    st.rerun()

                        with col_down:
                            if idx < len(selected_tasks) - 1:
                                if st.button(
                                    "⬇️",
                                    key=f"{key_prefix}_move_down_{idx}",
                                    help="Move down",
                                    use_container_width=True,
                                ):
                                    # Swap with next task
                                    (
                                        st.session_state[selected_tasks_key][idx],
                                        st.session_state[selected_tasks_key][idx + 1],
                                    ) = (
                                        st.session_state[selected_tasks_key][idx + 1],
                                        st.session_state[selected_tasks_key][idx],
                                    )
                                    # Update sequence numbers
                                    for i, t in enumerate(
                                        st.session_state[selected_tasks_key],
                                    ):
                                        t["sequence"] = i
                                    st.rerun()

                    with col4:
                        # Delete button
                        if st.button(
                            "🗑️ Remove",
                            key=f"{key_prefix}_delete_{idx}",
                            help=f"Remove {task['name']}",
                            use_container_width=True,
                        ):
                            st.session_state[selected_tasks_key].pop(idx)
                            # Update sequence numbers
                            for i, t in enumerate(st.session_state[selected_tasks_key]):
                                t["sequence"] = i
                            st.rerun()

                    st.divider()

            # Clear all button
            if st.button(
                "🗑️ Clear All Tasks",
                key=f"{key_prefix}_clear_all",
                help="Remove all selected tasks",
            ):
                st.session_state[selected_tasks_key] = []
                st.rerun()

        else:
            st.info("ℹ️ No tasks selected yet. Add tasks from the dropdown above.")

        return cast("list[dict[str, Any]]", st.session_state[selected_tasks_key])

    @staticmethod
    def get_selected_tasks(key_prefix: str = "task_selector") -> list[dict[str, Any]]:
        """
        Get currently selected tasks from session state.

        Args:
            key_prefix: Prefix for session state keys

        Returns:
            List of selected tasks
        """
        selected_tasks_key = f"{key_prefix}_selected_tasks"
        return cast(
            "list[dict[str, Any]]",
            st.session_state.get(selected_tasks_key, []),
        )

    @staticmethod
    def clear_selected_tasks(key_prefix: str = "task_selector") -> None:
        """
        Clear all selected tasks from session state.

        Args:
            key_prefix: Prefix for session state keys
        """
        selected_tasks_key = f"{key_prefix}_selected_tasks"
        if selected_tasks_key in st.session_state:
            st.session_state[selected_tasks_key] = []
