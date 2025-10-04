"""Template manager UI component for CommonUI."""

from typing import Any

import streamlit as st

from core.template_storage import TemplateStorage


class TemplateManager:
    """Template manager component."""

    def __init__(self, service_name: str, storage: TemplateStorage | None = None) -> None:
        """Initialize template manager.

        Args:
            service_name: Service name (e.g., 'jobqueue', 'myscheduler')
            storage: Template storage instance (creates new if None)
        """
        self.service_name = service_name
        self.storage = storage or TemplateStorage()

    def render_template_selector(
        self, current_data: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """Render template selector and management UI.

        Args:
            current_data: Current form data to save as template

        Returns:
            Selected template data or None
        """
        templates = self.storage.list_template_names(self.service_name)

        col1, col2 = st.columns([3, 1])

        with col1:
            selected_template = st.selectbox(
                "📋 テンプレート選択",
                [""] + templates,
                help="保存済みテンプレートから選択",
            )

        with col2:
            if st.button("🗑️ 削除", disabled=not selected_template, use_container_width=True):
                if selected_template:
                    self.storage.delete_template(self.service_name, selected_template)
                    st.success(f"テンプレート '{selected_template}' を削除しました")
                    st.rerun()

        # Load selected template
        loaded_data = None
        if selected_template:
            loaded_data = self.storage.load_template(self.service_name, selected_template)
            if loaded_data:
                st.info(f"✅ テンプレート '{selected_template}' を読み込みました")

        # Save template section
        with st.expander("💾 現在の設定をテンプレートとして保存"):
            template_name = st.text_input(
                "テンプレート名",
                placeholder="例: API呼び出しテンプレート",
                help="わかりやすい名前を付けてください",
            )

            if st.button("保存", disabled=not template_name or not current_data):
                if template_name and current_data:
                    self.storage.save_template(
                        self.service_name, template_name, current_data
                    )
                    st.success(f"テンプレート '{template_name}' を保存しました")
                    st.rerun()

        return loaded_data

    def render_compact_selector(self) -> dict[str, Any] | None:
        """Render compact template selector (no save/delete).

        Returns:
            Selected template data or None
        """
        templates = self.storage.list_template_names(self.service_name)

        if not templates:
            return None

        selected_template = st.selectbox(
            "📋 テンプレートから読み込み",
            [""] + templates,
            help="保存済みテンプレートから選択",
        )

        if selected_template:
            loaded_data = self.storage.load_template(self.service_name, selected_template)
            if loaded_data:
                st.info(f"✅ テンプレート '{selected_template}' を読み込みました")
                return loaded_data

        return None
