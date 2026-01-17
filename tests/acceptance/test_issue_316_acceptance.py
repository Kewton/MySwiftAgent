"""
Issue #316 受入テスト（L3: ローカル受入テスト）

３層構造の組み換え - jobqueue/myscheduler を Platform 層から Agent 層へ移動

前提条件:
- Docker Compose ファイルが正しいパスに存在すること

実行方法:
  uv run pytest tests/acceptance/test_issue_316_acceptance.py -v
"""

import subprocess
from pathlib import Path

import pytest


@pytest.mark.acceptance
class TestIssue316Acceptance:
    """Issue #316: ３層構造の組み換え"""

    PROJECT_ROOT = Path(__file__).parent.parent.parent

    # ==========================================================================
    # Docker Compose 構文検証
    # ==========================================================================

    def test_docker_compose_platform_yml_syntax(self) -> None:
        """Docker Compose Platform 構文検証

        AC5関連: docker compose up -d で全サービスが healthy 状態になる
        """
        result = subprocess.run(
            ["docker", "compose", "-f", "docker-compose.platform.yml", "config", "--quiet"],
            cwd=self.PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"docker-compose.platform.yml syntax error: {result.stderr}"

    def test_docker_compose_agent_yml_syntax(self) -> None:
        """Docker Compose Agent 構文検証

        AC5関連: docker compose up -d で全サービスが healthy 状態になる
        """
        result = subprocess.run(
            ["docker", "compose", "-f", "docker-compose.agent.yml", "config", "--quiet"],
            cwd=self.PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"docker-compose.agent.yml syntax error: {result.stderr}"

    # ==========================================================================
    # 層構造検証
    # ==========================================================================

    def test_platform_layer_does_not_contain_jobqueue(self) -> None:
        """Platform層にjobqueueがないことを確認

        AC1: docker-compose.platform.yml から jobqueue/myscheduler が削除されている
        """
        platform_yml = self.PROJECT_ROOT / "docker-compose.platform.yml"
        content = platform_yml.read_text()

        # jobqueue サービス定義がないことを確認（コメント内の言及は許容）
        lines = content.split("\n")
        for i, line in enumerate(lines):
            # サービス定義行を検出（インデントが2スペースで始まり:で終わる）
            if line.strip().startswith("jobqueue:"):
                pytest.fail(f"jobqueue service found in platform.yml at line {i + 1}")

    def test_platform_layer_does_not_contain_myscheduler(self) -> None:
        """Platform層にmyschedulerがないことを確認

        AC1: docker-compose.platform.yml から jobqueue/myscheduler が削除されている
        """
        platform_yml = self.PROJECT_ROOT / "docker-compose.platform.yml"
        content = platform_yml.read_text()

        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.strip().startswith("myscheduler:"):
                pytest.fail(f"myscheduler service found in platform.yml at line {i + 1}")

    def test_agent_layer_contains_jobqueue(self) -> None:
        """Agent層にjobqueueがあることを確認

        AC1: docker-compose.agent.yml に jobqueue/myscheduler が移動している
        """
        agent_yml = self.PROJECT_ROOT / "docker-compose.agent.yml"
        content = agent_yml.read_text()

        assert "jobqueue:" in content, "jobqueue service not found in agent.yml"

    def test_agent_layer_contains_myscheduler(self) -> None:
        """Agent層にmyschedulerがあることを確認

        AC1: docker-compose.agent.yml に jobqueue/myscheduler が移動している
        """
        agent_yml = self.PROJECT_ROOT / "docker-compose.agent.yml"
        content = agent_yml.read_text()

        assert "myscheduler:" in content, "myscheduler service not found in agent.yml"

    def test_myscheduler_depends_on_jobqueue(self) -> None:
        """myschedulerがjobqueueに依存することを確認

        AC2: myscheduler は jobqueue の service_healthy 条件を満たしてから起動する
        """
        agent_yml = self.PROJECT_ROOT / "docker-compose.agent.yml"
        content = agent_yml.read_text()

        # myscheduler セクションを探す
        in_myscheduler = False
        depends_on_found = False
        jobqueue_healthy_found = False

        for line in content.split("\n"):
            if line.strip().startswith("myscheduler:"):
                in_myscheduler = True
                continue

            if in_myscheduler:
                # 次のトップレベルサービス定義に到達したら終了
                if (
                    line.startswith("  ") is False
                    and line.strip()
                    and not line.strip().startswith("#")
                ):
                    if line.strip() != "":
                        break

                if "depends_on:" in line:
                    depends_on_found = True
                if "jobqueue:" in line and depends_on_found:
                    jobqueue_healthy_found = True
                if "service_healthy" in line and jobqueue_healthy_found:
                    # 依存関係が正しく設定されている
                    return

        assert depends_on_found, "myscheduler does not have depends_on section"
        assert jobqueue_healthy_found, (
            "myscheduler does not depend on jobqueue with service_healthy condition"
        )

    # ==========================================================================
    # Makefile 検証
    # ==========================================================================

    def test_makefile_syntax(self) -> None:
        """Makefile 構文検証

        AC7: Makefile の dev-platform/dev-agent ターゲットが正しく動作する
        """
        result = subprocess.run(
            ["make", "help"],
            cwd=self.PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Makefile syntax error: {result.stderr}"

    def test_makefile_check_platform_does_not_check_jobqueue(self) -> None:
        """_check-platform に JOBQUEUE_PORT チェックがないことを確認

        AC7: Platform層のヘルスチェックからjobqueueが削除されている
        """
        makefile = self.PROJECT_ROOT / "Makefile"
        content = makefile.read_text()

        # _check-platform セクションを探す
        in_check_platform = False
        for line in content.split("\n"):
            if line.startswith("_check-platform:"):
                in_check_platform = True
                continue
            if in_check_platform:
                # 次のターゲット定義に到達したら終了
                if line and not line.startswith("\t") and not line.startswith("#"):
                    break
                # このセクション内でJOBQUEUE_PORTの使用がないことを確認
                if "JOBQUEUE_PORT" in line:
                    pytest.fail("JOBQUEUE_PORT check found in _check-platform target")

    # ==========================================================================
    # dev-hybrid.sh 検証
    # ==========================================================================

    def test_dev_hybrid_sh_syntax(self) -> None:
        """dev-hybrid.sh 構文検証

        AC6: dev-hybrid.sh の構文が正しい
        """
        result = subprocess.run(
            ["bash", "-n", "scripts/dev-hybrid.sh"],
            cwd=self.PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"dev-hybrid.sh syntax error: {result.stderr}"

    def test_dev_hybrid_docker_services_does_not_contain_jobqueue(self) -> None:
        """DOCKER_SERVICES に jobqueue がないことを確認

        AC6: jobqueue はローカル起動に移動している
        """
        script = self.PROJECT_ROOT / "scripts" / "dev-hybrid.sh"
        content = script.read_text()

        for line in content.split("\n"):
            if "DOCKER_SERVICES=" in line and not line.strip().startswith("#"):
                assert "jobqueue" not in line, "jobqueue should not be in DOCKER_SERVICES"
                break

    def test_dev_hybrid_has_start_jobqueue_function(self) -> None:
        """start_jobqueue 関数があることを確認

        AC6: dev-hybrid.sh で jobqueue がローカルプロセスとして起動する
        """
        script = self.PROJECT_ROOT / "scripts" / "dev-hybrid.sh"
        content = script.read_text()

        assert "start_jobqueue()" in content, "start_jobqueue() function not found in dev-hybrid.sh"

    def test_dev_hybrid_has_start_myscheduler_function(self) -> None:
        """start_myscheduler 関数があることを確認

        AC6: dev-hybrid.sh で myscheduler がローカルプロセスとして起動する
        """
        script = self.PROJECT_ROOT / "scripts" / "dev-hybrid.sh"
        content = script.read_text()

        assert "start_myscheduler()" in content, (
            "start_myscheduler() function not found in dev-hybrid.sh"
        )

    # ==========================================================================
    # ドキュメント検証
    # ==========================================================================

    def test_service_dependencies_md_updated(self) -> None:
        """service-dependencies.md が更新されていることを確認

        AC8: docs/arch/service-dependencies.md が新しい層構造を反映している
        """
        doc = self.PROJECT_ROOT / "docs" / "arch" / "service-dependencies.md"
        content = doc.read_text()

        # Agent層の説明にjobqueue/myschedulerが含まれていることを確認
        # レイヤテーブルで Agent 層に jobqueue, myscheduler があることを確認
        assert "jobqueue" in content, "jobqueue not mentioned in service-dependencies.md"
        assert "myscheduler" in content, "myscheduler not mentioned in service-dependencies.md"
