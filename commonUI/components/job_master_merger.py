"""Job Master parameter merger with preview.

This component provides client-side merge logic that mirrors the jobqueue backend
implementation for previewing how master and override parameters will be merged.
"""

from typing import Any

import streamlit as st


class JobMasterMerger:
    """Job Master parameter merger with preview."""

    @staticmethod
    def merge_dict_shallow(
        base: dict[str, Any] | None,
        override: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """
        Merge two dictionaries with shallow merge strategy.

        Override values take precedence over base values.
        Used for headers and query parameters.

        Args:
            base: Base dictionary (from job master)
            override: Override dictionary (from job creation request)

        Returns:
            Merged dictionary, or None if both inputs are None
        """
        if base is None and override is None:
            return None

        result = (base or {}).copy()
        if override:
            result.update(override)

        return result if result else None

    @staticmethod
    def merge_dict_deep(
        base: dict[str, Any] | None,
        override: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """
        Merge two dictionaries with deep merge strategy.

        Recursively merges nested dictionaries.
        Override values take precedence over base values.
        Used for request body.

        Args:
            base: Base dictionary (from job master)
            override: Override dictionary (from job creation request)

        Returns:
            Deeply merged dictionary, or None if both inputs are None
        """
        if base is None and override is None:
            return None

        if base is None:
            return override

        if override is None:
            return base

        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                # Recursive merge for nested dicts
                result[key] = JobMasterMerger.merge_dict_deep(result[key], value)
            else:
                # Override value (including arrays, which are not merged)
                result[key] = value

        return result

    @staticmethod
    def merge_tags(
        base_tags: list[str] | None,
        override_tags: list[str] | None,
    ) -> list[str] | None:
        """
        Merge two tag lists with union strategy.

        Duplicates are removed and result is sorted.

        Args:
            base_tags: Base tag list (from job master)
            override_tags: Override tag list (from job creation request)

        Returns:
            Merged and deduplicated tag list, or None if both inputs are None
        """
        if base_tags is None and override_tags is None:
            return None

        result = set(base_tags or [])
        if override_tags:
            result.update(override_tags)

        return sorted(result) if result else None

    @staticmethod
    def render_merge_preview(
        master_data: dict[str, Any],
        override_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Render merge preview of master and override parameters.

        Args:
            master_data: Master template data
            override_data: Override parameters

        Returns:
            Merged result
        """
        merged: dict[str, Any] = {}

        # Merge headers (shallow)
        merged_headers = JobMasterMerger.merge_dict_shallow(
            master_data.get("headers"),
            override_data.get("headers"),
        )
        if merged_headers:
            merged["headers"] = merged_headers

        # Merge params (shallow)
        merged_params = JobMasterMerger.merge_dict_shallow(
            master_data.get("params"),
            override_data.get("params"),
        )
        if merged_params:
            merged["params"] = merged_params

        # Merge body (deep)
        merged_body = JobMasterMerger.merge_dict_deep(
            master_data.get("body"),
            override_data.get("body"),
        )
        if merged_body:
            merged["body"] = merged_body

        # Merge tags (union)
        merged_tags = JobMasterMerger.merge_tags(
            master_data.get("tags"),
            override_data.get("tags"),
        )
        if merged_tags:
            merged["tags"] = merged_tags

        # Copy non-mergeable fields from master
        for field in ["method", "url", "timeout_sec"]:
            if field in master_data:
                merged[field] = master_data[field]

        # Apply overrides for timeout_sec if provided
        if override_data.get("timeout_sec"):
            merged["timeout_sec"] = override_data["timeout_sec"]

        # Display preview
        with st.expander("👁️ Merged Result Preview", expanded=False):
            if merged:
                st.json(merged)
            else:
                st.info("No merged data available")

        return merged
