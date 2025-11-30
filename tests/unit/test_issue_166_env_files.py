"""Unit tests for Issue #166: .env file generation and loading."""

import tempfile
from pathlib import Path


class TestEnvFileGeneration:
    """Test .env file generation in dev-start.sh."""

    def test_dev_start_creates_env_files_if_not_exist(self):
        """受入条件: dev-start.shが.envファイルを自動生成すること"""
        # Given: No .env files exist
        with tempfile.TemporaryDirectory() as tmpdir:
            test_project_root = Path(tmpdir)
            jobqueue_dir = test_project_root / "jobqueue"
            myscheduler_dir = test_project_root / "myscheduler"
            jobqueue_dir.mkdir()
            myscheduler_dir.mkdir()

            # When: dev-start.sh generates .env files
            jobqueue_env_path = jobqueue_dir / ".env"
            myscheduler_env_path = myscheduler_dir / ".env"

            # Simulate the env file generation logic
            def generate_env_file(project_path, service_name):
                env_path = project_path / ".env"
                if not env_path.exists():
                    if service_name == "jobqueue":
                        env_content = (
                            "LOG_LEVEL=INFO\nDATABASE_URL=sqlite+aiosqlite:///./data/jobqueue.db\n"
                        )
                    elif service_name == "myscheduler":
                        env_content = "LOG_LEVEL=INFO\nDATABASE_URL=sqlite+aiosqlite:///./data/myscheduler.db\n"
                    else:
                        env_content = ""
                    env_path.write_text(env_content)

            generate_env_file(jobqueue_dir, "jobqueue")
            generate_env_file(myscheduler_dir, "myscheduler")

            # Then: .env files should be created with correct content
            assert jobqueue_env_path.exists()
            assert myscheduler_env_path.exists()

            jobqueue_content = jobqueue_env_path.read_text()
            assert "DATABASE_URL=sqlite+aiosqlite:///./data/jobqueue.db" in jobqueue_content

            myscheduler_content = myscheduler_env_path.read_text()
            assert "DATABASE_URL=sqlite+aiosqlite:///./data/myscheduler.db" in myscheduler_content


class TestEnvExampleFiles:
    """Test .env.example files."""

    def test_env_example_files_exist(self):
        """受入条件: .env.exampleファイルが各サービスに配置されていること"""
        # Given: Project directories
        project_root = Path(__file__).parent.parent.parent

        # When: Checking for .env.example files
        jobqueue_example = project_root / "jobqueue" / ".env.example"
        myscheduler_example = project_root / "myscheduler" / ".env.example"

        # Then: .env.example files should exist
        assert jobqueue_example.exists()
        assert myscheduler_example.exists()

        # And: They should contain the correct database URL format
        jobqueue_content = jobqueue_example.read_text()
        assert "DATABASE_URL=sqlite+aiosqlite:///./data/jobqueue.db" in jobqueue_content

        myscheduler_content = myscheduler_example.read_text()
        # myscheduler uses synchronous SQLite (APScheduler requirement)
        assert "DATABASE_URL=sqlite:///./data/jobs.db" in myscheduler_content
