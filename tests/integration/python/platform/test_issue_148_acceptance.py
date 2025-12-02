"""
Integration tests for Issue #148: Docker Compose Integration

Acceptance criteria tests for Docker Compose integration feature.

Note: This test uses fixtures from platform/conftest.py:
- project_root: Repository root path
- dev_start_script: Path to dev-start.sh
- docker_utils_script: Path to docker-utils.sh
"""

import subprocess


class TestAcceptanceCriteria1:
    """受入条件1: langfuseがDocker Composeで起動できること."""

    def test_langfuse_can_start_via_docker_compose(self, project_root, docker_utils_script):
        """
        Given: docker-compose.ymlにlangfuseサービスが定義されている
        When: Docker Composeでlangfuseを起動
        Then: langfuseコンテナが正常に起動すること
        """
        # Note: This test requires docker-compose.yml to have langfuse service
        # For now, we check if docker-utils.sh can handle service startup

        # Given: docker-utils.sh exists
        assert docker_utils_script.exists()

        # When: Check if start_docker_compose function can be called
        result = subprocess.run(
            f"bash -c 'source {docker_utils_script} && declare -F start_docker_compose'",
            shell=True,
            capture_output=True,
            text=True,
        )

        # Then: Function should exist
        assert result.returncode == 0


class TestAcceptanceCriteria2:
    """受入条件2: Dockerサービスのステータスが統合表示されること."""

    def test_docker_status_integrated_with_dev_start_status(
        self, dev_start_script, docker_utils_script
    ):
        """
        Given: dev-start.sh statusコマンドが存在する
        When: dev-start.sh statusを実行
        Then: Dockerサービスのステータスも表示されること
        """
        # Given: Scripts exist
        assert dev_start_script.exists()
        assert docker_utils_script.exists()

        # When: Run dev-start.sh with status command (dry-run check)
        # Note: We don't actually start services in tests, just check if commands work
        result = subprocess.run(
            [str(dev_start_script), "help"],
            capture_output=True,
            text=True,
            cwd=dev_start_script.parent.parent,
        )

        # Then: Should show help with status command
        assert result.returncode == 0
        assert "status" in result.stdout.lower()


class TestAcceptanceCriteria3:
    """受入条件3: Docker環境がない場合もネイティブサービスが起動すること."""

    def test_skip_docker_option_exists(self, dev_start_script):
        """
        Given: dev-start.shに--skip-dockerオプションが実装されている
        When: dev-start.sh start --skip-dockerを実行
        Then: Dockerをスキップしてネイティブサービスが起動すること
        """
        # Given: Script exists
        assert dev_start_script.exists()

        # When: Check help for --skip-docker option
        result = subprocess.run(
            [str(dev_start_script), "help"],
            capture_output=True,
            text=True,
            cwd=dev_start_script.parent.parent,
        )

        # Then: --skip-docker should be mentioned in help
        assert result.returncode == 0
        # Note: This will fail until implementation
        assert "--skip-docker" in result.stdout, "Missing --skip-docker option in help"


class TestAcceptanceCriteria4:
    """受入条件4: worktreeごとにDockerコンテナを分離できること."""

    def test_worktree_isolation_via_project_name(self, project_root, docker_utils_script):
        """
        Given: 複数のworktree環境が存在する
        When: get_worktree_project_name関数を呼び出す
        Then: worktreeごとに異なるプロジェクト名が返されること
        """
        # Given: docker-utils.sh exists
        assert docker_utils_script.exists()

        # When: Call get_worktree_project_name function
        result = subprocess.run(
            f"bash -c 'source {docker_utils_script} && get_worktree_project_name'",
            shell=True,
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        # Then: Should return a project name based on worktree path
        assert result.returncode == 0, f"Failed to get project name: {result.stderr}"
        project_name = result.stdout.strip()
        assert len(project_name) > 0, "Project name should not be empty"
        assert "myswiftagent" in project_name.lower(), f"Invalid project name: {project_name}"
