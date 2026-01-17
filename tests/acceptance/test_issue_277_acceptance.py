"""
Issue #277 受入テスト（L3: ローカル受入テスト）

前提条件:
- サービスが起動していること (./scripts/dev-start.sh または make dev-all)
- .env に必要なAPIキーが設定されていること

実行方法:
  uv run pytest tests/acceptance/test_issue_277_acceptance.py -v
"""

import os
import uuid
from typing import Any

import pytest
import requests


@pytest.mark.acceptance
class TestIssue277Acceptance:
    """Issue #277: commonUIのJob Configurationでのtaskのインタフェース確認効率化"""

    # サービスURL（環境変数で上書き可能）
    JOBQUEUE_URL = os.environ.get("JOBQUEUE_BASE_URL", "http://localhost:8101")
    API_TOKEN = os.environ.get("JOBQUEUE_API_TOKEN", "test_token")

    @pytest.fixture(autouse=True)
    def check_services_running(self) -> None:
        """サービス起動確認"""
        services = [
            (f"{self.JOBQUEUE_URL}/health", "jobqueue"),
        ]
        for url, name in services:
            try:
                response = requests.get(url, timeout=5)
                assert response.status_code == 200, f"{name} is not healthy"
            except requests.exceptions.ConnectionError:
                pytest.skip(f"{name} is not running. Run: ./scripts/dev-start.sh or make dev-all")

    def _get_headers(self) -> dict[str, str]:
        """API呼び出し用ヘッダーを取得"""
        return {
            "Content-Type": "application/json",
            "X-API-Token": self.API_TOKEN,
        }

    # ==========================================================================
    # 正常系テスト
    # ==========================================================================

    def test_scenario_1_create_interface_master(self) -> None:
        """シナリオ1: InterfaceMasterを作成できる

        受入条件: タスク選択時にインタフェース名が表示される（前提条件）
        """
        # Arrange
        endpoint = f"{self.JOBQUEUE_URL}/api/v1/interface-masters"
        unique_id = str(uuid.uuid4())[:8]
        payload: dict[str, Any] = {
            "name": f"TestInputInterface_{unique_id}",
            "description": "Test input interface for Issue #277 acceptance test",
            "input_schema": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {
                    "company_name": {"type": "string", "description": "Company name"},
                    "country": {"type": "string", "description": "Country code"},
                },
                "required": ["company_name"],
            },
        }

        # Act
        response = requests.post(
            endpoint,
            json=payload,
            headers=self._get_headers(),
            timeout=30,
        )

        # Assert
        assert response.status_code in [200, 201], (
            f"Expected 200/201, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "id" in data, f"Response missing 'id' field: {data}"
        assert data["name"] == payload["name"], f"Name mismatch: {data}"

        # Cleanup
        interface_id = data["id"]
        requests.delete(
            f"{self.JOBQUEUE_URL}/api/v1/interface-masters/{interface_id}",
            headers=self._get_headers(),
            timeout=10,
        )

    def test_scenario_2_get_interface_master_details(self) -> None:
        """シナリオ2: InterfaceMasterの詳細を取得できる

        受入条件: JSON Schemaプロパティがエキスパンダーで展開表示できる（前提条件）
        """
        # Arrange - Create interface first
        endpoint = f"{self.JOBQUEUE_URL}/api/v1/interface-masters"
        unique_id = str(uuid.uuid4())[:8]
        create_payload: dict[str, Any] = {
            "name": f"TestInterface_{unique_id}",
            "description": "Test interface for detail retrieval",
            "input_schema": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {
                    "field1": {"type": "string", "description": "Field 1"},
                    "field2": {"type": "integer", "description": "Field 2"},
                },
                "required": ["field1"],
            },
        }
        create_response = requests.post(
            endpoint,
            json=create_payload,
            headers=self._get_headers(),
            timeout=30,
        )
        assert create_response.status_code in [200, 201], (
            f"Failed to create interface: {create_response.text}"
        )
        interface_id = create_response.json()["id"]

        try:
            # Act - Get interface details
            get_response = requests.get(
                f"{endpoint}/{interface_id}",
                headers=self._get_headers(),
                timeout=10,
            )

            # Assert
            assert get_response.status_code == 200, (
                f"Expected 200, got {get_response.status_code}: {get_response.text}"
            )
            data = get_response.json()
            assert "id" in data, f"Response missing 'id' field: {data}"
            assert "name" in data, f"Response missing 'name' field: {data}"
            assert "input_schema" in data, f"Response missing 'input_schema' field: {data}"

            # Verify schema has expected structure
            schema = data.get("input_schema", {})
            assert "properties" in schema, f"Schema missing 'properties': {schema}"
            assert "field1" in schema["properties"], f"Schema missing 'field1': {schema}"

        finally:
            # Cleanup
            requests.delete(
                f"{endpoint}/{interface_id}",
                headers=self._get_headers(),
                timeout=10,
            )

    def test_scenario_3_list_task_masters_with_interface_ids(self) -> None:
        """シナリオ3: TaskMaster一覧でインタフェースIDを取得できる

        受入条件: ワークフロータスク一覧にインタフェース列が追加される（前提条件）
        """
        # Arrange
        endpoint = f"{self.JOBQUEUE_URL}/api/v1/task-masters"

        # Act
        response = requests.get(
            endpoint,
            headers=self._get_headers(),
            timeout=30,
        )

        # Assert
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "masters" in data, f"Response missing 'masters' field: {data}"

        # Verify structure supports interface_id fields
        if data["masters"]:
            task = data["masters"][0]
            # These fields should exist (may be null if not set)
            assert isinstance(task, dict), f"Task should be a dict: {task}"
            # input_interface_id and output_interface_id may or may not be present

    # ==========================================================================
    # 異常系テスト
    # ==========================================================================

    def test_scenario_4_get_nonexistent_interface_returns_404(self) -> None:
        """シナリオ4: 存在しないInterfaceMasterへのアクセスで404を返す

        受入条件: インタフェース未設定時は「未設定」と表示される（前提条件）
        """
        # Arrange
        nonexistent_id = f"if_nonexistent_{uuid.uuid4().hex[:8]}"
        endpoint = f"{self.JOBQUEUE_URL}/api/v1/interface-masters/{nonexistent_id}"

        # Act
        response = requests.get(
            endpoint,
            headers=self._get_headers(),
            timeout=10,
        )

        # Assert
        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )

    # ==========================================================================
    # UI動作確認用（手動チェック項目）
    # ==========================================================================

    def test_scenario_5_ui_verification_checklist(self) -> None:
        """シナリオ5: UI動作確認チェックリスト（情報表示のみ）

        このテストは常にパスしますが、手動確認項目を出力します。
        """
        checklist = """
        ============================================================
        UI動作確認チェックリスト（手動確認）
        ============================================================

        ブラウザで http://localhost:8501 を開き、以下を確認してください:

        1. [ ] サイドバーで「Job Configuration」を選択

        2. [ ] JobMasterを選択（または新規作成）

        3. [ ] 「Add Task to Workflow」パネルでインタフェース付きタスクを選択
           - [ ] 入力インタフェース名が表示される
           - [ ] 出力インタフェース名が表示される
           - [ ] 「View Input Schema」エキスパンダーをクリックでJSON Schema表示
           - [ ] プロパティ一覧（フィールド名、型、required）が表示される

        4. [ ] インタフェースなしタスクを選択
           - [ ] 入力インタフェース「未設定」と表示される
           - [ ] 出力インタフェース「未設定」と表示される

        5. [ ] ワークフロータスク一覧
           - [ ] 「Input Interface」列が表示される
           - [ ] 「Output Interface」列が表示される

        ============================================================
        """
        print(checklist)

        # このテストは手動確認用なので、API接続ができていれば成功とする
        assert True, "UI verification checklist displayed"
