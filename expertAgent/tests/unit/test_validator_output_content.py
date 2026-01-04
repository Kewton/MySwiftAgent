"""Unit tests for _validate_output_content function.

Issue #338: Detect success=false in workflow output.
"""

from aiagent.langgraph.workflowGeneratorAgents.nodes.validator import (
    _validate_output_content,
)


class TestValidateOutputContentSuccessFalse:
    """Test success=false detection."""

    def test_detects_success_false(self) -> None:
        """Should detect success=false in results."""
        execution_result = {
            "results": {
                "success": False,
                "results": [],
                "error_message": "ツールの出力形式に問題があります",
            }
        }
        issues = _validate_output_content(execution_result)

        assert len(issues) >= 1
        success_issue = next(
            (i for i in issues if i.get("detail") == "success=false"), None
        )
        assert success_issue is not None
        assert "output_content" in success_issue["category"]
        assert "ツールの出力形式に問題があります" in success_issue["message"]

    def test_does_not_trigger_on_success_true(self) -> None:
        """Should not trigger when success=true."""
        execution_result = {
            "results": {
                "success": True,
                "results": [{"title": "Test"}],
                "error_message": "",
            }
        }
        issues = _validate_output_content(execution_result)

        success_issues = [i for i in issues if i.get("detail") == "success=false"]
        assert len(success_issues) == 0

    def test_does_not_trigger_on_success_none(self) -> None:
        """Should not trigger when success is None (not explicitly False)."""
        execution_result = {
            "results": {
                "results": [{"title": "Test"}],
                "error_message": "",
            }
        }
        issues = _validate_output_content(execution_result)

        success_issues = [i for i in issues if i.get("detail") == "success=false"]
        assert len(success_issues) == 0


class TestValidateOutputContentEmptyResults:
    """Test empty results with error detection."""

    def test_detects_empty_results_with_error(self) -> None:
        """Should detect empty results array with error_message."""
        execution_result = {
            "results": {
                "success": True,
                "results": [],
                "error_message": "データが見つかりませんでした",
            }
        }
        issues = _validate_output_content(execution_result)

        assert len(issues) >= 1
        empty_issue = next((i for i in issues if i.get("detail") == "results=[]"), None)
        assert empty_issue is not None
        assert "output_content" in empty_issue["category"]
        assert "データが見つかりませんでした" in empty_issue["message"]

    def test_does_not_trigger_on_empty_results_without_error(self) -> None:
        """Should not trigger when results is empty but no error_message."""
        execution_result = {
            "results": {
                "success": True,
                "results": [],
                "error_message": "",
            }
        }
        issues = _validate_output_content(execution_result)

        empty_issues = [i for i in issues if i.get("detail") == "results=[]"]
        assert len(empty_issues) == 0

    def test_does_not_trigger_on_non_empty_results(self) -> None:
        """Should not trigger when results has data."""
        execution_result = {
            "results": {
                "success": True,
                "results": [{"title": "Test", "url": "https://example.com"}],
                "error_message": "",
            }
        }
        issues = _validate_output_content(execution_result)

        empty_issues = [i for i in issues if i.get("detail") == "results=[]"]
        assert len(empty_issues) == 0


class TestValidateOutputContentEdgeCases:
    """Test edge cases."""

    def test_returns_empty_on_none_execution_result(self) -> None:
        """Should return empty list when execution_result is None."""
        issues = _validate_output_content(None)
        assert issues == []

    def test_returns_empty_on_missing_results_key(self) -> None:
        """Should return empty list when results key is missing."""
        execution_result = {"errors": {}}
        issues = _validate_output_content(execution_result)
        assert issues == []

    def test_returns_empty_on_empty_results_dict(self) -> None:
        """Should return empty list when results is empty dict."""
        execution_result = {"results": {}}
        issues = _validate_output_content(execution_result)
        assert issues == []

    def test_returns_empty_on_non_dict_results(self) -> None:
        """Should return empty list when results is not a dict."""
        execution_result = {"results": "string value"}
        issues = _validate_output_content(execution_result)
        assert issues == []

    def test_detects_both_issues_simultaneously(self) -> None:
        """Should detect both success=false and empty results with error."""
        execution_result = {
            "results": {
                "success": False,
                "results": [],
                "error_message": "複合エラー",
            }
        }
        issues = _validate_output_content(execution_result)

        assert len(issues) == 2
        categories = {i["detail"] for i in issues}
        assert "success=false" in categories
        assert "results=[]" in categories


class TestValidateOutputContentIntegration:
    """Integration tests for validator behavior."""

    def test_phase1_failure_scenario(self) -> None:
        """Reproduce Phase 1 failure: HTTP 200 with success=false."""
        # This is the exact error that occurred in Phase 1
        execution_result = {
            "results": {
                "success": False,
                "results": [],
                "error_message": "Google検索ツールの実行中にエラーが発生しました。"
                "ツールの出力形式に問題があるようです。",
            }
        }
        issues = _validate_output_content(execution_result)

        # Should detect the failure and route to self_repair
        assert len(issues) >= 1
        assert any(i.get("detail") == "success=false" for i in issues)
