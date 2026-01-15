"""Unit tests for task order sorting in V2 adapter.

Issue: タスクの順序がtask_id順になっていない問題の修正検証
"""

import pytest

from aiagent.langgraph.jobGeneratorV2.adapter import JobGeneratorV2Adapter
from aiagent.langgraph.jobGeneratorV2.types import TaskDefinition


class TestTaskOrderSorting:
    """Test task ordering in _convert_tasks_to_breakdown."""

    @pytest.fixture
    def adapter(self) -> JobGeneratorV2Adapter:
        """Create adapter instance without dependencies."""
        # JobGeneratorV2Adapter requires these but we're only testing the method
        adapter = object.__new__(JobGeneratorV2Adapter)
        return adapter

    def test_tasks_sorted_by_task_id_numeric_order(
        self, adapter: JobGeneratorV2Adapter
    ) -> None:
        """Tasks should be sorted by task_id in numeric order."""
        # Arrange: Tasks in wrong order (001, 003, 002)
        tasks = [
            TaskDefinition(
                id="task_001",
                name="Google検索の実行",
                description="検索を実行",
                task_type="web_search",
                recommended_api="/v1/utility/google_search",
            ),
            TaskDefinition(
                id="task_003",
                name="サマリのメール送信",
                description="メールを送信",
                task_type="email_send",
                recommended_api="/v1/utility/gmail/send",
            ),
            TaskDefinition(
                id="task_002",
                name="検索結果の要約",
                description="結果を要約",
                task_type="llm_processing",
                recommended_api="/v1/mylllm",
            ),
        ]

        # Act
        result = adapter._convert_tasks_to_breakdown(tasks)

        # Assert: Should be in numeric order (001, 002, 003)
        assert result[0]["task_id"] == "task_001"
        assert result[1]["task_id"] == "task_002"
        assert result[2]["task_id"] == "task_003"

    def test_alt_tasks_come_after_base_tasks(
        self, adapter: JobGeneratorV2Adapter
    ) -> None:
        """Alternative tasks (_alt) should come after base tasks with same number."""
        # Arrange: task_002_alt should come after task_002
        tasks = [
            TaskDefinition(
                id="task_002_alt",
                name="検索結果の要約（代替）",
                description="代替の要約方法",
                task_type="llm_processing",
                recommended_api="/v1/mylllm",
            ),
            TaskDefinition(
                id="task_001",
                name="Google検索の実行",
                description="検索を実行",
                task_type="web_search",
                recommended_api="/v1/utility/google_search",
            ),
            TaskDefinition(
                id="task_002",
                name="検索結果の要約",
                description="結果を要約",
                task_type="llm_processing",
                recommended_api="/v1/mylllm",
            ),
        ]

        # Act
        result = adapter._convert_tasks_to_breakdown(tasks)

        # Assert: Order should be 001, 002, 002_alt
        assert result[0]["task_id"] == "task_001"
        assert result[1]["task_id"] == "task_002"
        assert result[2]["task_id"] == "task_002_alt"

    def test_mixed_tasks_with_alt_sorted_correctly(
        self, adapter: JobGeneratorV2Adapter
    ) -> None:
        """Complex case with multiple alt tasks sorted correctly."""
        # Arrange: Mixed order with multiple alt tasks
        tasks = [
            TaskDefinition(
                id="task_003",
                name="メール送信",
                description="送信",
                task_type="email_send",
                recommended_api="/v1/utility/gmail/send",
            ),
            TaskDefinition(
                id="task_001_alt",
                name="代替検索",
                description="代替",
                task_type="web_search",
                recommended_api="/v1/utility/google_search",
            ),
            TaskDefinition(
                id="task_002_alt",
                name="代替要約",
                description="代替",
                task_type="llm_processing",
                recommended_api="/v1/mylllm",
            ),
            TaskDefinition(
                id="task_001",
                name="検索",
                description="検索",
                task_type="web_search",
                recommended_api="/v1/utility/google_search",
            ),
            TaskDefinition(
                id="task_002",
                name="要約",
                description="要約",
                task_type="llm_processing",
                recommended_api="/v1/mylllm",
            ),
        ]

        # Act
        result = adapter._convert_tasks_to_breakdown(tasks)

        # Assert: Order should be 001, 001_alt, 002, 002_alt, 003
        assert [r["task_id"] for r in result] == [
            "task_001",
            "task_001_alt",
            "task_002",
            "task_002_alt",
            "task_003",
        ]

    def test_real_world_case_from_ui_bug(self, adapter: JobGeneratorV2Adapter) -> None:
        """Test the exact case from the UI bug report.

        Original order in DB: task_001, task_003, task_002_alt
        Expected order: task_001, task_002_alt, task_003
        """
        # Arrange: Exact data from the bug report
        tasks = [
            TaskDefinition(
                id="task_001",
                name="Google検索の実行",
                description="キーワード「大谷翔平」を使用してGoogle検索を実行",
                task_type="web_search",
                recommended_api="/v1/utility/google_search",
            ),
            TaskDefinition(
                id="task_003",
                name="サマリのメール送信",
                description="作成された要約テキストを送信",
                task_type="email_send",
                recommended_api="/v1/utility/gmail/send",
            ),
            TaskDefinition(
                id="task_002_alt",
                name="検索結果の要約",
                description="Direct LLMエンドポイントを使用して要約を作成",
                task_type="llm_processing",
                recommended_api="/v1/mylllm",
            ),
        ]

        # Act
        result = adapter._convert_tasks_to_breakdown(tasks)

        # Assert: Should be in logical order (001, 002_alt, 003)
        assert result[0]["task_id"] == "task_001"
        assert result[0]["name"] == "Google検索の実行"

        assert result[1]["task_id"] == "task_002_alt"
        assert result[1]["name"] == "検索結果の要約"

        assert result[2]["task_id"] == "task_003"
        assert result[2]["name"] == "サマリのメール送信"

    def test_empty_tasks_list(self, adapter: JobGeneratorV2Adapter) -> None:
        """Empty task list should return empty list."""
        result = adapter._convert_tasks_to_breakdown([])
        assert result == []

    def test_single_task(self, adapter: JobGeneratorV2Adapter) -> None:
        """Single task should work correctly."""
        tasks = [
            TaskDefinition(
                id="task_001",
                name="単一タスク",
                description="テスト",
                task_type="general",
                recommended_api="/v1/test",
            ),
        ]

        result = adapter._convert_tasks_to_breakdown(tasks)

        assert len(result) == 1
        assert result[0]["task_id"] == "task_001"

    def test_non_standard_task_id_falls_back(
        self, adapter: JobGeneratorV2Adapter
    ) -> None:
        """Non-standard task_ids should fall back to end of list."""
        tasks = [
            TaskDefinition(
                id="custom_task",
                name="カスタムタスク",
                description="非標準ID",
                task_type="general",
                recommended_api="/v1/test",
            ),
            TaskDefinition(
                id="task_001",
                name="標準タスク",
                description="標準ID",
                task_type="general",
                recommended_api="/v1/test",
            ),
        ]

        result = adapter._convert_tasks_to_breakdown(tasks)

        # Standard task_id should come first, non-standard at end
        assert result[0]["task_id"] == "task_001"
        assert result[1]["task_id"] == "custom_task"
