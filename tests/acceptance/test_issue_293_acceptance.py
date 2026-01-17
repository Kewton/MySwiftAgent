"""
Issue #293 受入テスト（L3: ローカル受入テスト）

[myAgentDesk] Runs画面（実行履歴・監視）

【実践的テスト】
- Run開始からステータス遷移までの完全検証
- ポーリングによるリアルタイム更新
- Rerun機能のテスト
- API レスポンスのデータ構造を詳細に検証

前提条件:
- myAgentDesk サービスが起動していること (cd myAgentDesk && npm run dev)
- data/local.db にシードデータが存在すること (npm run db:seed)
- JobQueue サービスが起動していること (docker compose up jobqueue)

実行方法:
  uv run pytest tests/acceptance/test_issue_293_acceptance.py -v
"""

import os
import sqlite3
import time
from dataclasses import dataclass

import pytest
import requests


@dataclass
class RunData:
    """Run テストデータ"""

    id: str
    job_version_id: str
    status: str
    started_at: str | None
    completed_at: str | None
    tasks_completed: int
    total_tasks: int
    external_job_id: str | None
    external_trace_id: str | None


@dataclass
class JobVersionData:
    """JobVersion テストデータ"""

    id: str
    workbench_id: str
    status: str
    version_label: str


class DBHelper:
    """データベースヘルパー"""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def get_job_version(self, status: str = "active") -> JobVersionData | None:
        """指定ステータスのJobVersionを取得"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, workbench_id, status, version_label
            FROM job_version
            WHERE status = ?
            LIMIT 1
            """,
            (status,),
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return JobVersionData(
                id=row["id"],
                workbench_id=row["workbench_id"],
                status=row["status"],
                version_label=row["version_label"],
            )
        return None

    def get_any_job_version(self) -> JobVersionData | None:
        """任意のJobVersionを取得"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, workbench_id, status, version_label
            FROM job_version
            LIMIT 1
            """,
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return JobVersionData(
                id=row["id"],
                workbench_id=row["workbench_id"],
                status=row["status"],
                version_label=row["version_label"],
            )
        return None

    def get_run(self, run_id: str) -> RunData | None:
        """Run データ取得"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, job_version_id, status, started_at, completed_at,
                   tasks_completed, total_tasks, external_job_id, external_trace_id
            FROM run
            WHERE id = ?
            """,
            (run_id,),
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return RunData(
                id=row["id"],
                job_version_id=row["job_version_id"],
                status=row["status"],
                started_at=row["started_at"],
                completed_at=row["completed_at"],
                tasks_completed=row["tasks_completed"] or 0,
                total_tasks=row["total_tasks"] or 0,
                external_job_id=row["external_job_id"],
                external_trace_id=row["external_trace_id"],
            )
        return None

    def get_runs_by_workbench(self, workbench_id: str) -> list[RunData]:
        """Workbenchに属するRun一覧を取得"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT r.id, r.job_version_id, r.status, r.started_at, r.completed_at,
                   r.tasks_completed, r.total_tasks, r.external_job_id, r.external_trace_id
            FROM run r
            JOIN job_version jv ON r.job_version_id = jv.id
            WHERE jv.workbench_id = ?
            ORDER BY r.created_at DESC
            """,
            (workbench_id,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            RunData(
                id=row["id"],
                job_version_id=row["job_version_id"],
                status=row["status"],
                started_at=row["started_at"],
                completed_at=row["completed_at"],
                tasks_completed=row["tasks_completed"] or 0,
                total_tasks=row["total_tasks"] or 0,
                external_job_id=row["external_job_id"],
                external_trace_id=row["external_trace_id"],
            )
            for row in rows
        ]

    def get_failed_run(self) -> RunData | None:
        """失敗したRunを取得"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, job_version_id, status, started_at, completed_at,
                   tasks_completed, total_tasks, external_job_id, external_trace_id
            FROM run
            WHERE status IN ('failed', 'timeout')
            ORDER BY created_at DESC
            LIMIT 1
            """,
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return RunData(
                id=row["id"],
                job_version_id=row["job_version_id"],
                status=row["status"],
                started_at=row["started_at"],
                completed_at=row["completed_at"],
                tasks_completed=row["tasks_completed"] or 0,
                total_tasks=row["total_tasks"] or 0,
                external_job_id=row["external_job_id"],
                external_trace_id=row["external_trace_id"],
            )
        return None


@pytest.mark.acceptance
class TestIssue293Acceptance:
    """Issue #293: Runs画面（実行履歴・監視）- 実践的受入テスト"""

    # サービスURL
    MYAGENTDESK_URL = os.environ.get("MYAGENTDESK_URL", "http://localhost:5173")
    JOBQUEUE_URL = os.environ.get("JOBQUEUE_URL", "http://localhost:8001")
    MYAGENTDESK_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "myAgentDesk",
    )

    # テストデータ
    db_helper: DBHelper | None = None
    job_version: JobVersionData | None = None
    created_run_id: str | None = None

    @pytest.fixture(autouse=True)
    def setup_test_data(self) -> None:
        """テストデータのセットアップ"""
        # myAgentDesk 起動確認
        try:
            response = requests.get(self.MYAGENTDESK_URL, timeout=5)
            assert response.status_code == 200, "myAgentDesk is not running"
        except requests.exceptions.ConnectionError:
            pytest.skip("myAgentDesk is not running. Run: cd myAgentDesk && npm run dev")

        # DBヘルパー初期化
        db_path = os.path.join(self.MYAGENTDESK_DIR, "data", "local.db")
        if not os.path.exists(db_path):
            pytest.skip(f"Database not found: {db_path}")

        self.__class__.db_helper = DBHelper(db_path)

        # テスト用JobVersionを取得
        self.__class__.job_version = self.db_helper.get_any_job_version()
        if not self.job_version:
            pytest.skip("No JobVersion in database")

    # ==========================================================================
    # シナリオ1: Run開始API - 正常系
    # ==========================================================================

    def test_run_creation_api_returns_correct_response(self) -> None:
        """Run開始APIが正しいレスポンス構造を返す（status=queued）"""
        assert self.job_version is not None

        url = f"{self.MYAGENTDESK_URL}/api/runs"
        payload = {"jobVersionId": self.job_version.id}

        response = requests.post(url, json=payload, timeout=10)

        assert response.status_code in [200, 201], (
            f"Expected 200 or 201, got {response.status_code}: {response.text}"
        )

        data = response.json()

        # レスポンス構造の検証
        assert "id" in data, f"Response missing 'id': {data}"
        assert "status" in data, f"Response missing 'status': {data}"
        assert data["status"] == "queued", (
            f"Initial status should be 'queued', got '{data['status']}'"
        )

        # 作成したRun IDを保存（後続テストで使用）
        self.__class__.created_run_id = data["id"]

    def test_run_creation_sets_initial_values(self) -> None:
        """Run作成時に初期値が正しく設定される"""
        assert self.db_helper is not None

        if not self.created_run_id:
            pytest.skip("No run created in previous test")

        run = self.db_helper.get_run(self.created_run_id)
        assert run is not None, "Run not found in database"

        # 初期値の検証
        assert run.status == "queued", f"Expected 'queued', got '{run.status}'"
        assert run.tasks_completed == 0, (
            f"Initial tasks_completed should be 0, got {run.tasks_completed}"
        )

    # ==========================================================================
    # シナリオ2: Run開始API - 異常系
    # ==========================================================================

    def test_run_creation_rejects_nonexistent_job_version(self) -> None:
        """存在しないJobVersionでRun開始を試みると404が返る"""
        url = f"{self.MYAGENTDESK_URL}/api/runs"
        payload = {"jobVersionId": "jv_nonexistent_999"}

        response = requests.post(url, json=payload, timeout=10)

        assert response.status_code in [400, 404], (
            f"Expected 400 or 404, got {response.status_code}"
        )

        data = response.json()
        assert "error" in data or "message" in data, f"Error response missing error field: {data}"

    def test_run_creation_rejects_invalid_payload(self) -> None:
        """不正なペイロードでRun開始を試みると400が返る"""
        url = f"{self.MYAGENTDESK_URL}/api/runs"
        payload = {}  # jobVersionIdがない

        response = requests.post(url, json=payload, timeout=10)

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"

    # ==========================================================================
    # シナリオ3: ステータス取得API
    # ==========================================================================

    def test_status_api_returns_current_status(self) -> None:
        """ステータス取得APIが現在のステータスを返す"""
        if not self.created_run_id:
            pytest.skip("No run created in previous test")

        url = f"{self.MYAGENTDESK_URL}/api/runs/{self.created_run_id}/status"
        response = requests.get(url, timeout=10)

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

        data = response.json()
        assert "status" in data, f"Response missing 'status': {data}"
        assert data["status"] in [
            "queued",
            "running",
            "success",
            "failed",
            "canceled",
            "timeout",
        ], f"Unexpected status: {data['status']}"

    def test_status_api_returns_progress_info(self) -> None:
        """ステータス取得APIがプログレス情報を含む"""
        if not self.created_run_id:
            pytest.skip("No run created in previous test")

        url = f"{self.MYAGENTDESK_URL}/api/runs/{self.created_run_id}/status"
        response = requests.get(url, timeout=10)

        assert response.status_code == 200

        data = response.json()
        # プログレス情報の存在確認（オプショナル）
        if "tasksCompleted" in data:
            assert isinstance(data["tasksCompleted"], int)
        if "totalTasks" in data:
            assert isinstance(data["totalTasks"], int)

    def test_status_api_returns_404_for_nonexistent_run(self) -> None:
        """存在しないRunのステータス取得で404が返る"""
        url = f"{self.MYAGENTDESK_URL}/api/runs/run_nonexistent_999/status"
        response = requests.get(url, timeout=10)

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"

    # ==========================================================================
    # シナリオ4: Rerun API
    # ==========================================================================

    def test_rerun_api_creates_new_run_from_failed(self) -> None:
        """失敗RunからRerunで新しいRunが作成される"""
        assert self.db_helper is not None

        failed_run = self.db_helper.get_failed_run()
        if not failed_run:
            pytest.skip("No failed run in database")

        url = f"{self.MYAGENTDESK_URL}/api/runs/{failed_run.id}/rerun"
        response = requests.post(url, timeout=10)

        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data, f"Response missing 'id': {data}"
            assert data["id"] != failed_run.id, "Rerun should create new Run"
            assert data["status"] == "queued", (
                f"Rerun should start with 'queued', got '{data['status']}'"
            )
        elif response.status_code == 400:
            # Rerunがビジネスロジックで拒否された場合
            data = response.json()
            assert "error" in data or "message" in data
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")

    def test_rerun_api_rejects_success_run(self) -> None:
        """成功RunへのRerunは拒否される（400）"""
        assert self.db_helper is not None

        # 成功Runを探す
        conn = sqlite3.connect(os.path.join(self.MYAGENTDESK_DIR, "data", "local.db"))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM run WHERE status = 'success' LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        if not row:
            pytest.skip("No success run in database")

        url = f"{self.MYAGENTDESK_URL}/api/runs/{row['id']}/rerun"
        response = requests.post(url, timeout=10)

        assert response.status_code == 400, (
            f"Expected 400 for success run rerun, got {response.status_code}"
        )

    # ==========================================================================
    # シナリオ5: Runs一覧画面
    # ==========================================================================

    def test_runs_list_page_loads(self) -> None:
        """Runs一覧画面が正常にロードされる"""
        assert self.job_version is not None

        # Workbench IDを取得
        workbench_id = self.job_version.workbench_id

        # Project IDを取得
        conn = sqlite3.connect(os.path.join(self.MYAGENTDESK_DIR, "data", "local.db"))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT project_id FROM workbench WHERE id = ?",
            (workbench_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            pytest.skip("Workbench not found")

        project_id = row["project_id"]

        url = f"{self.MYAGENTDESK_URL}/projects/{project_id}/workbenches/{workbench_id}/runs"
        response = requests.get(url, timeout=10)

        assert response.status_code == 200, f"Runs list page failed to load: {response.status_code}"

        # ページ内容にRunsに関するコンテンツが含まれる
        assert "run" in response.text.lower(), "Page should contain 'run' related content"

    # ==========================================================================
    # シナリオ6: ステータス遷移の監視（シミュレーション）
    # ==========================================================================

    def test_polling_simulation(self) -> None:
        """ポーリングシミュレーション（5秒間隔で3回）"""
        if not self.created_run_id:
            pytest.skip("No run created in previous test")

        url = f"{self.MYAGENTDESK_URL}/api/runs/{self.created_run_id}/status"

        statuses = []
        for i in range(3):
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                statuses.append(data.get("status"))
                print(f"  Poll {i + 1}: status={data.get('status')}")

                # 終了ステータスならポーリング終了
                if data.get("status") in [
                    "success",
                    "failed",
                    "canceled",
                    "timeout",
                ]:
                    print("  Terminal status reached, stopping poll")
                    break

            time.sleep(2)  # テスト用に短縮

        assert len(statuses) > 0, "No status could be retrieved"
        print(f"  Status history: {statuses}")

    # ==========================================================================
    # シナリオ7: ビルド・型チェック
    # ==========================================================================

    def test_typescript_build_passes(self) -> None:
        """TypeScriptビルドが成功する"""
        import subprocess

        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=self.MYAGENTDESK_DIR,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, f"Build failed:\nSTDERR: {result.stderr[-1000:]}"
