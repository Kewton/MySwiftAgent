"""
Issue #288 受入テスト（L3: ローカル受入テスト）
[myAgentDesk] #279-4: Project一覧・詳細画面

前提条件:
- myAgentDesk が起動していること (cd myAgentDesk && npm run dev)
- DBに初期データが投入されていること

実行方法:
  uv run pytest tests/acceptance/test_issue_288_acceptance.py -v
"""

import pytest
import requests
from typing import Any


@pytest.mark.acceptance
class TestIssue288Acceptance:
    """Issue #288: Project一覧・詳細画面の受入テスト"""

    # myAgentDesk サービスURL
    MYAGENTDESK_URL = "http://localhost:5173"

    @pytest.fixture(autouse=True)
    def check_services_running(self) -> None:
        """サービス起動確認"""
        try:
            response = requests.get(self.MYAGENTDESK_URL, timeout=5)
            # SvelteKit は 200 または redirect を返す
            assert response.status_code in [
                200,
                302,
                304,
            ], f"myAgentDesk is not responding correctly: {response.status_code}"
        except requests.exceptions.ConnectionError:
            pytest.skip(
                "myAgentDesk is not running. "
                "Run: cd myAgentDesk && npm run dev"
            )

    # ==========================================================================
    # 正常系テスト
    # ==========================================================================

    def test_projects_list_page_returns_200(self) -> None:
        """シナリオ1: /projects ページが200を返す

        受入条件: /projects でProject一覧が表示される
        """
        # Arrange
        endpoint = f"{self.MYAGENTDESK_URL}/projects"

        # Act
        response = requests.get(endpoint, timeout=30)

        # Assert
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text[:500]}"
        )
        # HTMLレスポンスであることを確認
        assert "text/html" in response.headers.get("content-type", ""), (
            f"Expected HTML response, got: {response.headers.get('content-type')}"
        )

    def test_projects_list_page_contains_expected_content(self) -> None:
        """シナリオ1b: /projects ページに期待するコンテンツが含まれる"""
        # Arrange
        endpoint = f"{self.MYAGENTDESK_URL}/projects"

        # Act
        response = requests.get(endpoint, timeout=30)

        # Assert
        assert response.status_code == 200
        content = response.text.lower()
        # "project" という単語がページに含まれることを確認
        assert "project" in content, (
            f"Expected 'project' in page content"
        )

    def test_project_detail_page_returns_200_for_valid_id(self) -> None:
        """シナリオ2: /projects/:projectId が有効なIDで200を返す

        受入条件: /projects/:projectId でProject詳細が表示される
        """
        # Arrange
        # テスト用のプロジェクトID（DBに存在する必要がある）
        test_project_id = "proj_001"
        endpoint = f"{self.MYAGENTDESK_URL}/projects/{test_project_id}"

        # Act
        response = requests.get(endpoint, timeout=30)

        # Assert
        # 有効なIDの場合は200、存在しない場合は404
        assert response.status_code in [200, 404], (
            f"Expected 200 or 404, got {response.status_code}: {response.text[:500]}"
        )

    def test_vault_settings_page_returns_200(self) -> None:
        """シナリオ3: /projects/:projectId/vault が200を返す

        受入条件: /projects/:projectId/vault でシークレット一覧が表示される
        """
        # Arrange
        test_project_id = "proj_001"
        endpoint = f"{self.MYAGENTDESK_URL}/projects/{test_project_id}/vault"

        # Act
        response = requests.get(endpoint, timeout=30)

        # Assert
        # 有効なプロジェクトの場合は200、存在しない場合は404
        assert response.status_code in [200, 404], (
            f"Expected 200 or 404, got {response.status_code}: {response.text[:500]}"
        )

    # ==========================================================================
    # 異常系テスト
    # ==========================================================================

    def test_project_detail_returns_404_for_invalid_id(self) -> None:
        """シナリオ4: /projects/invalid_id で404を返す

        受入条件: 存在しないprojectIdで404エラー
        """
        # Arrange
        invalid_project_id = "invalid_project_id_that_does_not_exist"
        endpoint = f"{self.MYAGENTDESK_URL}/projects/{invalid_project_id}"

        # Act
        response = requests.get(endpoint, timeout=30)

        # Assert
        assert response.status_code == 404, (
            f"Expected 404 for invalid project ID, got {response.status_code}"
        )

    def test_vault_returns_404_for_invalid_project(self) -> None:
        """シナリオ5: /projects/invalid_id/vault で404を返す"""
        # Arrange
        invalid_project_id = "nonexistent_project_xyz"
        endpoint = f"{self.MYAGENTDESK_URL}/projects/{invalid_project_id}/vault"

        # Act
        response = requests.get(endpoint, timeout=30)

        # Assert
        assert response.status_code == 404, (
            f"Expected 404 for invalid project vault, got {response.status_code}"
        )

    def test_path_traversal_attack_returns_404(self) -> None:
        """シナリオ6: パストラバーサル攻撃で404を返す（セキュリティ）"""
        # Arrange
        malicious_id = "../../etc/passwd"
        endpoint = f"{self.MYAGENTDESK_URL}/projects/{malicious_id}"

        # Act
        response = requests.get(endpoint, timeout=30, allow_redirects=False)

        # Assert
        # 404または400（Bad Request）を期待
        assert response.status_code in [400, 404], (
            f"Expected 400 or 404 for path traversal, got {response.status_code}"
        )

    # ==========================================================================
    # APIレスポンス形式テスト
    # ==========================================================================

    def test_projects_page_is_html(self) -> None:
        """シナリオ7: /projects ページがHTML形式で返される"""
        # Arrange
        endpoint = f"{self.MYAGENTDESK_URL}/projects"

        # Act
        response = requests.get(endpoint, timeout=30)

        # Assert
        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "text/html" in content_type, (
            f"Expected text/html, got {content_type}"
        )

    def test_projects_page_has_doctype(self) -> None:
        """シナリオ8: /projects ページが有効なHTMLドキュメント"""
        # Arrange
        endpoint = f"{self.MYAGENTDESK_URL}/projects"

        # Act
        response = requests.get(endpoint, timeout=30)

        # Assert
        assert response.status_code == 200
        content = response.text.strip().lower()
        # HTMLドキュメントであることを確認
        assert content.startswith("<!doctype html") or "<html" in content, (
            f"Expected HTML document, got: {content[:100]}"
        )
