"""Task Selector component for selecting and ordering TaskMasters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Iterable

import streamlit as st  # type: ignore[import-not-found]

TaskDict = dict[str, Any]
TaskList = list[TaskDict]

EMPTY_OPTION = "(Select a task to add)"


def _selected_tasks_key(key_prefix: str) -> str:
    return f"{key_prefix}_selected_tasks"


def _ensure_selected_tasks(key_prefix: str) -> TaskList:
    key = _selected_tasks_key(key_prefix)
    if key not in st.session_state:
        st.session_state[key] = []
    return cast("TaskList", st.session_state[key])


def _task_options(tasks: Iterable[TaskDict]) -> list[str]:
    return [EMPTY_OPTION] + [f"{task['name']} ({task['id']})" for task in tasks]


def _extract_task_id(option: str) -> str:
    return option.split("(")[-1].rstrip(")")


def _task_already_selected(tasks: TaskList, task_id: str) -> bool:
    return any(task["master_id"] == task_id for task in tasks)


def _find_task(
    available_tasks: Iterable[TaskDict],
    task_id: str,
) -> TaskDict | None:
    return next(
        (task for task in available_tasks if task["id"] == task_id),
        None,
    )


def _update_sequences(tasks: TaskList) -> None:
    for index, task in enumerate(tasks):
        task["sequence"] = index


def _add_task(
    available_tasks: Iterable[TaskDict],
    selected_tasks: TaskList,
    selected_option: str,
) -> None:
    task_id = _extract_task_id(selected_option)
    task = _find_task(available_tasks, task_id)
    if task is None:
        return
    if _task_already_selected(selected_tasks, task_id):
        st.warning(f"⚠️ Task '{task['name']}' is already selected")
        return

    selected_tasks.append(
        {
            "master_id": task["id"],
            "sequence": len(selected_tasks),
            "name": task["name"],
            "description": task.get("description"),
            "input_interface_id": task.get("input_interface_id"),
            "output_interface_id": task.get("output_interface_id"),
        },
    )
    st.success(f"✅ Added: {task['name']}")
    st.rerun()


def _swap_tasks(tasks: TaskList, first: int, second: int) -> None:
    tasks[first], tasks[second] = tasks[second], tasks[first]
    _update_sequences(tasks)
    st.rerun()


def _remove_task(tasks: TaskList, index: int) -> None:
    tasks.pop(index)
    _update_sequences(tasks)
    st.rerun()


def _render_task_entry(
    task: TaskDict,
    index: int,
    total: int,
    key_prefix: str,
    tasks: TaskList,
) -> None:
    with st.container():
        col_position, col_body, col_move, col_delete = st.columns([1, 5, 2, 2])

        with col_position:
            st.markdown(f"**#{index + 1}**")

        with col_body:
            st.markdown(f"**{task['name']}**")
            description = task.get("description")
            if description:
                st.caption(description)

            interface_info = []
            input_id = task.get("input_interface_id")
            output_id = task.get("output_interface_id")

            interface_info.append(
                f"📥 Input: `{input_id}`" if input_id else "📥 Input: None",
            )
            interface_info.append(
                f"📤 Output: `{output_id}`" if output_id else "📤 Output: None",
            )
            st.caption(" | ".join(interface_info))

        with col_move:
            col_up, col_down = st.columns(2)

            with col_up:
                if index > 0 and st.button(
                    "⬆️",
                    key=f"{key_prefix}_move_up_{index}",
                    help="Move up",
                    use_container_width=True,
                ):
                    _swap_tasks(tasks, index, index - 1)

            with col_down:
                if index < total - 1 and st.button(
                    "⬇️",
                    key=f"{key_prefix}_move_down_{index}",
                    help="Move down",
                    use_container_width=True,
                ):
                    _swap_tasks(tasks, index, index + 1)

        with col_delete:
            if st.button(
                "🗑️ Remove",
                key=f"{key_prefix}_delete_{index}",
                help=f"Remove {task['name']}",
                use_container_width=True,
            ):
                _remove_task(tasks, index)

        st.divider()


def _render_selected_tasks(tasks: TaskList, key_prefix: str) -> None:
    if not tasks:
        st.info(
            "ℹ️ No tasks selected yet. Add tasks from the dropdown above.",
        )
        return

    st.divider()
    st.subheader(f"🔢 Selected Tasks ({len(tasks)})")
    st.caption("Tasks will be executed in the order shown below")

    for index, task in enumerate(tasks):
        _render_task_entry(task, index, len(tasks), key_prefix, tasks)

    if st.button(
        "🗑️ Clear All Tasks",
        key=f"{key_prefix}_clear_all",
        help="Remove all selected tasks",
    ):
        tasks.clear()
        st.rerun()


class TaskSelector:
    """Task selection and ordering UI component for Job creation."""

    @staticmethod
    def render_task_selector(
        available_tasks: list[TaskDict],
        key_prefix: str = "task_selector",
    ) -> TaskList:
        """Render task selection and ordering UI."""

        selected_tasks = _ensure_selected_tasks(key_prefix)

        st.subheader("📋 Task Selection")
        st.caption(
            "Select TaskMasters to execute in sequence. "
            "Interface compatibility will be checked automatically.",
        )

        if available_tasks:
            options = _task_options(available_tasks)
            col_select, col_add = st.columns([4, 1])

            with col_select:
                selected_option = st.selectbox(
                    "Available TaskMasters",
                    options,
                    key=f"{key_prefix}_selectbox",
                    help=("Select a TaskMaster to add to the execution sequence"),
                )

            with col_add:
                add_clicked = st.button(
                    "➕ Add Task",
                    use_container_width=True,
                    key=f"{key_prefix}_add_button",
                )

            if add_clicked and selected_option != EMPTY_OPTION:
                _add_task(available_tasks, selected_tasks, selected_option)
        else:
            st.info(
                "ℹ️ No TaskMasters available. Please create TaskMasters first.",
            )

        _render_selected_tasks(selected_tasks, key_prefix)

        return selected_tasks

    @staticmethod
    def get_selected_tasks(key_prefix: str = "task_selector") -> TaskList:
        """Return selected tasks from session state."""

        key = _selected_tasks_key(key_prefix)
        return cast("TaskList", st.session_state.get(key, []))

    @staticmethod
    def clear_selected_tasks(key_prefix: str = "task_selector") -> None:
        """Clear selected tasks from session state."""

        key = _selected_tasks_key(key_prefix)
        if key in st.session_state:
            st.session_state[key] = []
