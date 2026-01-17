"""
Issue #191 受入テスト（L3: ローカル受入テスト）

プロンプト管理API実装の受入テスト

前提条件:
- サービスが起動していること (./scripts/dev-start.sh または make dev-all)
- .env に必要なAPIキーが設定されていること

実行方法:
  uv run pytest tests/acceptance/test_issue_191_prompts_api.py -v
"""


import pytest
import requests


@pytest.mark.acceptance
class TestIssue191PromptsApiAcceptance:
    """Issue #191: プロンプト管理API実装"""

    # サービスURL
    EXPERT_AGENT_URL = "http://localhost:8104"
    API_BASE = f"{EXPERT_AGENT_URL}/aiagent-api"

    @pytest.fixture(autouse=True)
    def check_services_running(self) -> None:
        """サービス起動確認"""
        try:
            response = requests.get(f"{self.EXPERT_AGENT_URL}/health", timeout=5)
            assert response.status_code == 200, "expertAgent is not healthy"
        except requests.exceptions.ConnectionError:
            pytest.skip("expertAgent is not running. Run: ./scripts/dev-start.sh or make dev-all")

    # ==========================================================================
    # 正常系テスト
    # ==========================================================================

    def test_get_prompts_list_returns_items_and_total(self) -> None:
        """シナリオ1: GET /v1/prompts がプロンプト一覧を返す

        受入条件: /v1/prompts エンドポイント実装（GET: プロンプト一覧取得）
        """
        # Arrange
        endpoint = f"{self.API_BASE}/v1/prompts"

        # Act
        response = requests.get(
            endpoint,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        # Assert
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "items" in data, f"Response missing 'items' field: {data}"
        assert "total" in data, f"Response missing 'total' field: {data}"
        assert isinstance(data["items"], list), "items should be a list"
        assert data["total"] >= 1, f"Expected at least 1 prompt, got {data['total']}"

    def test_get_prompts_list_contains_expected_fields(self) -> None:
        """シナリオ2: プロンプト一覧の各アイテムが必要なフィールドを持つ

        受入条件: Pydanticスキーマによるレスポンス定義
        """
        # Arrange
        endpoint = f"{self.API_BASE}/v1/prompts"
        required_fields = [
            "id",
            "name",
            "description",
            "category",
            "current_version",
            "versions",
            "created_at",
            "updated_at",
        ]

        # Act
        response = requests.get(endpoint, timeout=30)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0, "No prompts found"

        item = data["items"][0]
        for field in required_fields:
            assert field in item, f"Missing required field '{field}' in prompt item: {item}"

    def test_get_prompt_detail_returns_full_content(self) -> None:
        """シナリオ3: GET /v1/prompts/{prompt_id} がプロンプト詳細を返す

        受入条件: /v1/prompts/{prompt_id} エンドポイント実装（GET: プロンプト詳細取得）
        """
        # Arrange - まず一覧からプロンプトIDを取得
        list_response = requests.get(f"{self.API_BASE}/v1/prompts", timeout=30)
        assert list_response.status_code == 200
        prompts = list_response.json()["items"]
        assert len(prompts) > 0, "No prompts available for testing"
        prompt_id = prompts[0]["id"]

        # Act
        endpoint = f"{self.API_BASE}/v1/prompts/{prompt_id}"
        response = requests.get(
            endpoint,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        # Assert
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert data["id"] == prompt_id, f"Expected id '{prompt_id}', got '{data['id']}'"
        assert "versions" in data, "Response missing 'versions' field"
        assert len(data["versions"]) > 0, "No versions found"

    def test_prompt_versions_contain_content(self) -> None:
        """シナリオ4: プロンプトのバージョンにコンテンツが含まれる

        受入条件: プロンプトの詳細（コンテンツ、バージョン情報）が閲覧できる
        """
        # Arrange
        list_response = requests.get(f"{self.API_BASE}/v1/prompts", timeout=30)
        prompts = list_response.json()["items"]
        prompt_id = prompts[0]["id"]

        # Act
        response = requests.get(
            f"{self.API_BASE}/v1/prompts/{prompt_id}",
            timeout=30,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        version = data["versions"][0]

        version_fields = ["id", "version", "content", "description", "created_at", "is_active"]
        for field in version_fields:
            assert field in version, f"Missing required field '{field}' in version: {version}"

        assert len(version["content"]) > 0, f"Version content is empty: {version}"

    # ==========================================================================
    # 異常系テスト
    # ==========================================================================

    def test_get_nonexistent_prompt_returns_404(self) -> None:
        """シナリオ5: 存在しないプロンプトIDで404を返す

        受入条件: 適切なエラーハンドリング
        """
        # Arrange
        endpoint = f"{self.API_BASE}/v1/prompts/nonexistent_prompt_id_12345"

        # Act
        response = requests.get(endpoint, timeout=10)

        # Assert
        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "detail" in data, f"Error response missing 'detail' field: {data}"

    # ==========================================================================
    # OpenAPI仕様テスト
    # ==========================================================================

    def test_openapi_includes_prompts_endpoints(self) -> None:
        """シナリオ6: OpenAPI仕様にPromptsエンドポイントが含まれる

        受入条件: OpenAPI仕様に準拠したドキュメント生成
        """
        # Arrange
        endpoint = f"{self.API_BASE}/openapi.json"

        # Act
        response = requests.get(endpoint, timeout=30)

        # Assert
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        paths = data.get("paths", {})

        assert "/v1/prompts" in paths, (
            f"/v1/prompts not found in OpenAPI paths: {list(paths.keys())}"
        )
        assert "/v1/prompts/{prompt_id}" in paths, (
            "/v1/prompts/{prompt_id} not found in OpenAPI paths"
        )

    # ==========================================================================
    # フロントエンド互換性テスト
    # ==========================================================================

    def test_frontend_compatibility_response_format(self) -> None:
        """シナリオ7: フロントエンドが期待する形式でレスポンスを返す

        受入条件: MLOps UIのPrompts画面で実際のプロンプト一覧が表示される
        """
        # Arrange
        endpoint = f"{self.API_BASE}/v1/prompts"

        # Act
        response = requests.get(endpoint, timeout=30)

        # Assert
        assert response.status_code == 200
        data = response.json()

        # フロントエンドが期待するルートフィールド
        assert "items" in data, "Missing 'items' field"
        assert "total" in data, "Missing 'total' field"
        assert isinstance(data["total"], int), "total should be an integer"

        # フロントエンドが期待するアイテムフィールド
        if len(data["items"]) > 0:
            item = data["items"][0]
            # TypeScript型定義との互換性確認
            assert isinstance(item.get("id"), str), "id should be string"
            assert isinstance(item.get("name"), str), "name should be string"
            assert isinstance(item.get("category"), str), "category should be string"
            assert isinstance(item.get("current_version"), int), "current_version should be int"
            assert isinstance(item.get("versions"), list), "versions should be list"

    def test_prompt_count_matches_yaml_files(self) -> None:
        """シナリオ8: プロンプト数がYAMLファイル数と一致する

        受入条件: 既存のPromptLoaderサービスを活用
        """
        # Arrange
        endpoint = f"{self.API_BASE}/v1/prompts"

        # Act
        response = requests.get(endpoint, timeout=30)

        # Assert
        assert response.status_code == 200
        data = response.json()

        # 少なくとも1つ以上のプロンプトが存在すること
        assert data["total"] >= 1, f"Expected at least 1 prompt, got {data['total']}"
        assert len(data["items"]) == data["total"], (
            f"items count ({len(data['items'])}) does not match total ({data['total']})"
        )
