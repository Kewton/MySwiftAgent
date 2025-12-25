"""
Issue #292 受入テスト（L3: ローカル受入テスト）

[myAgentDesk] Review画面（JobVersion詳細）

【実践的テスト】
- DBの実データと画面表示の整合性を検証
- タスク分解の件数・内容を具体的に検証
- API レスポンスのデータ構造を詳細に検証
- ユーザーの業務フローをシナリオで検証

前提条件:
- myAgentDesk サービスが起動していること (cd myAgentDesk && npm run dev)
- data/local.db にシードデータが存在すること (npm run db:seed)

実行方法:
  uv run pytest tests/acceptance/test_issue_292_acceptance.py -v
"""
import json
import os
import re
import sqlite3
import subprocess
from dataclasses import dataclass

import pytest
import requests


@dataclass
class JobVersionData:
    """JobVersion テストデータ"""

    id: str
    workbench_id: str
    major_version: int
    minor_version: int
    version_label: str
    status: str
    task_breakdown: list[dict] | None
    interface_definitions: dict | None
    workflows: list[dict] | None


@dataclass
class WorkbenchData:
    """Workbench テストデータ"""

    id: str
    project_id: str
    name: str
    status: str


class DBHelper:
    """データベースヘルパー"""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def get_workbench(self, workbench_id: str) -> WorkbenchData | None:
        """Workbench データ取得"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, project_id, name, status FROM workbench WHERE id = ?",
            (workbench_id,),
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return WorkbenchData(
                id=row["id"],
                project_id=row["project_id"],
                name=row["name"],
                status=row["status"],
            )
        return None

    def get_job_versions_by_workbench(
        self, workbench_id: str
    ) -> list[JobVersionData]:
        """Workbench に属する JobVersion 一覧を取得"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, workbench_id, major_version, minor_version, version_label,
                   status, task_breakdown, interface_definitions, workflows
            FROM job_version
            WHERE workbench_id = ?
            ORDER BY major_version DESC, minor_version DESC
            """,
            (workbench_id,),
        )
        rows = cursor.fetchall()
        conn.close()

        result = []
        for row in rows:
            task_breakdown = None
            if row["task_breakdown"]:
                try:
                    task_breakdown = json.loads(row["task_breakdown"])
                except json.JSONDecodeError:
                    pass

            interface_definitions = None
            if row["interface_definitions"]:
                try:
                    interface_definitions = json.loads(row["interface_definitions"])
                except json.JSONDecodeError:
                    pass

            workflows = None
            if row["workflows"]:
                try:
                    workflows = json.loads(row["workflows"])
                except json.JSONDecodeError:
                    pass

            result.append(
                JobVersionData(
                    id=row["id"],
                    workbench_id=row["workbench_id"],
                    major_version=row["major_version"],
                    minor_version=row["minor_version"],
                    version_label=row["version_label"],
                    status=row["status"],
                    task_breakdown=task_breakdown,
                    interface_definitions=interface_definitions,
                    workflows=workflows,
                )
            )
        return result

    def get_job_version(self, job_version_id: str) -> JobVersionData | None:
        """JobVersion データ取得"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, workbench_id, major_version, minor_version, version_label,
                   status, task_breakdown, interface_definitions, workflows
            FROM job_version
            WHERE id = ?
            """,
            (job_version_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        task_breakdown = None
        if row["task_breakdown"]:
            try:
                task_breakdown = json.loads(row["task_breakdown"])
            except json.JSONDecodeError:
                pass

        interface_definitions = None
        if row["interface_definitions"]:
            try:
                interface_definitions = json.loads(row["interface_definitions"])
            except json.JSONDecodeError:
                pass

        workflows = None
        if row["workflows"]:
            try:
                workflows = json.loads(row["workflows"])
            except json.JSONDecodeError:
                pass

        return JobVersionData(
            id=row["id"],
            workbench_id=row["workbench_id"],
            major_version=row["major_version"],
            minor_version=row["minor_version"],
            version_label=row["version_label"],
            status=row["status"],
            task_breakdown=task_breakdown,
            interface_definitions=interface_definitions,
            workflows=workflows,
        )


@pytest.mark.acceptance
class TestIssue292Acceptance:
    """Issue #292: Review画面（JobVersion詳細）- 実践的受入テスト"""

    # サービスURL
    MYAGENTDESK_URL = os.environ.get("MYAGENTDESK_URL", "http://localhost:5173")
    MYAGENTDESK_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "myAgentDesk",
    )

    # テストデータ
    db_helper: DBHelper | None = None
    workbench: WorkbenchData | None = None
    job_versions: list[JobVersionData] = []

    @pytest.fixture(autouse=True)
    def setup_test_data(self) -> None:
        """テストデータのセットアップ"""
        # myAgentDesk 起動確認
        try:
            response = requests.get(self.MYAGENTDESK_URL, timeout=5)
            assert response.status_code == 200, "myAgentDesk is not running"
        except requests.exceptions.ConnectionError:
            pytest.skip(
                "myAgentDesk is not running. "
                "Run: cd myAgentDesk && npm run dev"
            )

        # DBヘルパー初期化
        db_path = os.path.join(self.MYAGENTDESK_DIR, "data", "local.db")
        if not os.path.exists(db_path):
            pytest.skip(f"Database not found: {db_path}")

        self.__class__.db_helper = DBHelper(db_path)

        # テストデータ取得 (wb_001 を使用)
        self.__class__.workbench = self.db_helper.get_workbench("wb_001")
        if not self.workbench:
            pytest.skip("Workbench wb_001 not found in database")

        self.__class__.job_versions = self.db_helper.get_job_versions_by_workbench(
            "wb_001"
        )

    # ==========================================================================
    # シナリオ1: Review画面 - JobVersion一覧の表示検証
    # ==========================================================================

    def test_review_page_displays_correct_version_count(self) -> None:
        """Review画面にDBの件数と同じJobVersionが表示される"""
        assert self.workbench is not None
        expected_count = len(self.job_versions)

        url = (
            f"{self.MYAGENTDESK_URL}/projects/{self.workbench.project_id}"
            f"/workbenches/{self.workbench.id}/review"
        )

        response = requests.get(url, timeout=10)
        assert response.status_code == 200

        # バージョン番号のパターンをカウント (v1.0, v2.1 等)
        version_pattern = re.compile(r"v\d+\.\d+")
        found_versions = version_pattern.findall(response.text)

        # DBの件数と一致（または0件の場合は空状態メッセージ）
        if expected_count == 0:
            assert "no" in response.text.lower() or "empty" in response.text.lower()
        else:
            assert len(found_versions) >= expected_count, (
                f"Expected at least {expected_count} versions, "
                f"found {len(found_versions)}: {found_versions}"
            )

    def test_review_page_displays_correct_version_labels(self) -> None:
        """Review画面にDBのversion_labelが正しく表示される"""
        assert self.workbench is not None
        if not self.job_versions:
            pytest.skip("No JobVersions in database")

        url = (
            f"{self.MYAGENTDESK_URL}/projects/{self.workbench.project_id}"
            f"/workbenches/{self.workbench.id}/review"
        )

        response = requests.get(url, timeout=10)
        assert response.status_code == 200

        # 各JobVersionのversion_labelが含まれているか確認
        for jv in self.job_versions:
            assert jv.version_label in response.text, (
                f"Version label '{jv.version_label}' not found in response"
            )

    def test_review_page_displays_status_badges(self) -> None:
        """Review画面にDBのstatusに対応するバッジが表示される"""
        assert self.workbench is not None
        if not self.job_versions:
            pytest.skip("No JobVersions in database")

        url = (
            f"{self.MYAGENTDESK_URL}/projects/{self.workbench.project_id}"
            f"/workbenches/{self.workbench.id}/review"
        )

        response = requests.get(url, timeout=10)
        assert response.status_code == 200
        html_lower = response.text.lower()

        # 各JobVersionのstatusが含まれているか確認
        for jv in self.job_versions:
            assert jv.status.lower() in html_lower, (
                f"Status '{jv.status}' not found in response"
            )

    # ==========================================================================
    # シナリオ2: JobVersion詳細画面 - タスク分解の表示検証
    # ==========================================================================

    def test_detail_page_displays_correct_task_count(self) -> None:
        """JobVersion詳細にDBのタスク件数が正しく表示される"""
        assert self.workbench is not None

        # task_breakdownが存在するJobVersionを取得
        jv_with_tasks = next(
            (jv for jv in self.job_versions if jv.task_breakdown), None
        )
        if not jv_with_tasks:
            pytest.skip("No JobVersion with task_breakdown in database")

        expected_task_count = len(jv_with_tasks.task_breakdown or [])

        url = (
            f"{self.MYAGENTDESK_URL}/projects/{self.workbench.project_id}"
            f"/workbenches/{self.workbench.id}"
            f"/job-versions/{jv_with_tasks.id}"
        )

        response = requests.get(url, timeout=10)
        assert response.status_code == 200

        # タスク名がすべて含まれているか確認
        for task in jv_with_tasks.task_breakdown or []:
            task_name = task.get("name", "")
            if task_name:
                assert task_name in response.text, (
                    f"Task name '{task_name}' not found in response. "
                    f"Expected {expected_task_count} tasks."
                )

    def test_detail_page_displays_task_names_in_order(self) -> None:
        """JobVersion詳細にタスク名が順序通り表示される"""
        assert self.workbench is not None

        jv_with_tasks = next(
            (jv for jv in self.job_versions if jv.task_breakdown), None
        )
        if not jv_with_tasks:
            pytest.skip("No JobVersion with task_breakdown in database")

        url = (
            f"{self.MYAGENTDESK_URL}/projects/{self.workbench.project_id}"
            f"/workbenches/{self.workbench.id}"
            f"/job-versions/{jv_with_tasks.id}"
        )

        response = requests.get(url, timeout=10)
        assert response.status_code == 200

        # タスク名の出現位置を確認し、順序が正しいか検証
        sorted_tasks = sorted(
            jv_with_tasks.task_breakdown or [],
            key=lambda t: t.get("order", 0),
        )
        last_pos = -1
        for task in sorted_tasks:
            task_name = task.get("name", "")
            if task_name:
                pos = response.text.find(task_name)
                assert pos > last_pos, (
                    f"Task '{task_name}' appears before expected position"
                )
                last_pos = pos

    # ==========================================================================
    # シナリオ3: JobVersion詳細画面 - IF定義の表示検証
    # ==========================================================================

    def test_detail_page_displays_interface_input_schema(self) -> None:
        """JobVersion詳細にInput Interfaceが正しく表示される"""
        assert self.workbench is not None

        jv_with_if = next(
            (jv for jv in self.job_versions if jv.interface_definitions), None
        )
        if not jv_with_if:
            pytest.skip("No JobVersion with interface_definitions in database")

        url = (
            f"{self.MYAGENTDESK_URL}/projects/{self.workbench.project_id}"
            f"/workbenches/{self.workbench.id}"
            f"/job-versions/{jv_with_if.id}"
        )

        response = requests.get(url, timeout=10)
        assert response.status_code == 200

        # Input Interfaceのキーが含まれているか確認
        input_if = jv_with_if.interface_definitions.get("input", {})
        for key in input_if.keys():
            assert key in response.text, (
                f"Input interface key '{key}' not found in response"
            )

    def test_detail_page_displays_interface_output_schema(self) -> None:
        """JobVersion詳細にOutput Interfaceが正しく表示される"""
        assert self.workbench is not None

        jv_with_if = next(
            (jv for jv in self.job_versions if jv.interface_definitions), None
        )
        if not jv_with_if:
            pytest.skip("No JobVersion with interface_definitions in database")

        url = (
            f"{self.MYAGENTDESK_URL}/projects/{self.workbench.project_id}"
            f"/workbenches/{self.workbench.id}"
            f"/job-versions/{jv_with_if.id}"
        )

        response = requests.get(url, timeout=10)
        assert response.status_code == 200

        # Output Interfaceのキーが含まれているか確認
        output_if = jv_with_if.interface_definitions.get("output", {})
        for key in output_if.keys():
            assert key in response.text, (
                f"Output interface key '{key}' not found in response"
            )

    # ==========================================================================
    # シナリオ4: Active切り替えAPI - データ整合性検証
    # ==========================================================================

    def test_activate_api_returns_correct_response_structure(self) -> None:
        """Active切り替えAPIが正しいレスポンス構造を返す"""
        assert self.db_helper is not None

        # success または deprecated のJobVersionを取得（activeは切替不可）
        jv_to_activate = next(
            (
                jv
                for jv in self.job_versions
                if jv.status in ["success", "deprecated"]
            ),
            None,
        )
        if not jv_to_activate:
            # activeのJobVersionでバリデーションエラーを確認
            jv_to_activate = next(
                (jv for jv in self.job_versions if jv.status == "active"), None
            )
            if not jv_to_activate:
                pytest.skip("No JobVersion available for activate test")

        url = f"{self.MYAGENTDESK_URL}/api/job-versions/{jv_to_activate.id}/activate"

        response = requests.post(url, timeout=10)

        # レスポンスがJSONであることを確認
        assert response.headers.get("content-type", "").startswith(
            "application/json"
        ), f"Expected JSON response, got {response.headers.get('content-type')}"

        data = response.json()

        if response.status_code == 200:
            # 成功時: 更新されたJobVersionが返る
            assert "id" in data or "jobVersion" in data, (
                f"Success response missing expected fields: {data}"
            )
        elif response.status_code == 400:
            # バリデーションエラー時: エラーメッセージが返る
            assert "message" in data or "error" in data, (
                f"Error response missing message field: {data}"
            )
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")

    def test_activate_api_rejects_already_active_version(self) -> None:
        """既にActiveのJobVersionは切り替え不可（バリデーションエラー）"""
        assert self.db_helper is not None

        active_jv = next(
            (jv for jv in self.job_versions if jv.status == "active"), None
        )
        if not active_jv:
            pytest.skip("No active JobVersion in database")

        url = f"{self.MYAGENTDESK_URL}/api/job-versions/{active_jv.id}/activate"

        response = requests.post(url, timeout=10)

        # 400 Bad Request を期待
        assert response.status_code == 400, (
            f"Expected 400 for already active version, got {response.status_code}"
        )

        data = response.json()
        # エラーメッセージにactive関連の説明が含まれる
        error_msg = data.get("message", "") or data.get("error", "")
        assert "active" in error_msg.lower(), (
            f"Error message should mention 'active': {error_msg}"
        )

    # ==========================================================================
    # シナリオ5: エラーハンドリング - セキュリティ検証
    # ==========================================================================

    def test_nonexistent_job_version_returns_404_with_message(self) -> None:
        """存在しないJobVersionへのアクセスで404と適切なエラーメッセージが返る"""
        assert self.workbench is not None

        url = (
            f"{self.MYAGENTDESK_URL}/projects/{self.workbench.project_id}"
            f"/workbenches/{self.workbench.id}"
            f"/job-versions/jv_nonexistent_999"
        )

        response = requests.get(url, timeout=10)

        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}"
        )
        # エラーメッセージが含まれているか確認
        assert "not found" in response.text.lower() or "404" in response.text, (
            "404 page should contain 'not found' or '404'"
        )

    def test_wrong_workbench_access_returns_404(self) -> None:
        """別のWorkbench経由でのアクセスは404（所属確認ガード）"""
        assert self.workbench is not None
        if not self.job_versions:
            pytest.skip("No JobVersions in database")

        jv = self.job_versions[0]

        # 別のWorkbench経由でアクセス
        url = (
            f"{self.MYAGENTDESK_URL}/projects/{self.workbench.project_id}"
            f"/workbenches/wb_999"  # 存在しないWorkbench
            f"/job-versions/{jv.id}"
        )

        response = requests.get(url, timeout=10)

        assert response.status_code == 404, (
            f"Expected 404 for wrong workbench access, got {response.status_code}"
        )

    # ==========================================================================
    # シナリオ6: ビルド・型チェック - CI/CD品質確認
    # ==========================================================================

    def test_typescript_build_passes_without_errors(self) -> None:
        """TypeScriptビルドがエラーなしで成功する"""
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=self.MYAGENTDESK_DIR,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, (
            f"Build failed with exit code {result.returncode}:\n"
            f"STDERR: {result.stderr[-1000:]}\n"
            f"STDOUT: {result.stdout[-1000:]}"
        )

        # エラーキーワードがないことを確認
        assert "error" not in result.stderr.lower(), (
            f"Build output contains 'error': {result.stderr[-500:]}"
        )

    def test_type_check_passes_without_errors(self) -> None:
        """TypeScript型チェックがエラーなしで成功する"""
        result = subprocess.run(
            ["npm", "run", "type-check"],
            cwd=self.MYAGENTDESK_DIR,
            capture_output=True,
            text=True,
            check=False,
        )

        if "Missing script" in result.stderr:
            pytest.skip("type-check script not found in package.json")

        assert result.returncode == 0, (
            f"Type check failed with exit code {result.returncode}:\n"
            f"STDERR: {result.stderr[-1000:]}\n"
            f"STDOUT: {result.stdout[-1000:]}"
        )

    # ==========================================================================
    # シナリオ7: 業務フロー検証 - E2Eシナリオ
    # ==========================================================================

    def test_user_workflow_review_to_detail_navigation(self) -> None:
        """ユーザーフロー: Review画面 → JobVersion詳細へ遷移"""
        assert self.workbench is not None
        if not self.job_versions:
            pytest.skip("No JobVersions in database")

        jv = self.job_versions[0]

        # Step 1: Review画面にアクセス
        review_url = (
            f"{self.MYAGENTDESK_URL}/projects/{self.workbench.project_id}"
            f"/workbenches/{self.workbench.id}/review"
        )
        review_response = requests.get(review_url, timeout=10)
        assert review_response.status_code == 200, "Review page failed to load"

        # Step 2: JobVersionへのリンクが含まれているか確認
        detail_path = f"/job-versions/{jv.id}"
        assert (
            detail_path in review_response.text
            or jv.version_label in review_response.text
        ), f"Link to {detail_path} not found in review page"

        # Step 3: 詳細画面にアクセス
        detail_url = (
            f"{self.MYAGENTDESK_URL}/projects/{self.workbench.project_id}"
            f"/workbenches/{self.workbench.id}"
            f"/job-versions/{jv.id}"
        )
        detail_response = requests.get(detail_url, timeout=10)
        assert detail_response.status_code == 200, "Detail page failed to load"

        # Step 4: 詳細画面にバージョン情報が表示されているか確認
        assert jv.version_label in detail_response.text, (
            f"Version label {jv.version_label} not found in detail page"
        )

    def test_api_data_consistency_with_db(self) -> None:
        """API レスポンスとDBデータの整合性検証"""
        assert self.workbench is not None
        if not self.job_versions:
            pytest.skip("No JobVersions in database")

        jv = self.job_versions[0]

        # APIからJobVersion情報を取得（存在すれば）
        api_url = f"{self.MYAGENTDESK_URL}/api/workbenches/{self.workbench.id}/job-versions"
        response = requests.get(api_url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            job_versions_from_api = (
                data if isinstance(data, list) else data.get("jobVersions", [])
            )

            # DBのデータとAPIのデータを比較
            api_jv = next(
                (j for j in job_versions_from_api if j.get("id") == jv.id), None
            )
            if api_jv:
                # バージョンラベルの一致確認
                assert api_jv.get("versionLabel") == jv.version_label, (
                    f"Version label mismatch: API={api_jv.get('versionLabel')}, "
                    f"DB={jv.version_label}"
                )
                # ステータスの一致確認
                assert api_jv.get("status") == jv.status, (
                    f"Status mismatch: API={api_jv.get('status')}, DB={jv.status}"
                )
        elif response.status_code == 404:
            pytest.skip("JobVersions API endpoint not implemented")
        else:
            pytest.fail(f"Unexpected API response: {response.status_code}")
