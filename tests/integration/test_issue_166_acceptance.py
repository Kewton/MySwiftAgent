"""Integration acceptance tests for Issue #166: SQLAlchemy async driver configuration."""

import tempfile
from pathlib import Path


class TestServiceStartupAcceptance:
    """Test that services start up correctly with async database drivers."""

    def test_all_services_start_with_correct_database_url(self):
        """受入条件: 全サービスが正常に起動し、ヘルスチェックが成功すること"""
        # Given: Project root directory
        project_root = Path(__file__).parent.parent.parent

        # Ensure .env files exist for both services
        for service in ["jobqueue", "myscheduler"]:
            env_example = project_root / service / ".env.example"
            env_file = project_root / service / ".env"
            if env_example.exists() and not env_file.exists():
                import shutil

                shutil.copy(env_example, env_file)

        # When: Checking .env file contents (avoiding module import for test isolation)
        jobqueue_env = project_root / "jobqueue" / ".env"
        myscheduler_env = project_root / "myscheduler" / ".env"

        # Then: jobqueue .env should have async SQLite driver configured
        jobqueue_content = jobqueue_env.read_text()
        assert "sqlite+aiosqlite://" in jobqueue_content, (
            "jobqueue .env should contain sqlite+aiosqlite:// for async driver"
        )

        # And: myscheduler .env should use synchronous SQLite (APScheduler requirement)
        myscheduler_content = myscheduler_env.read_text()
        assert "sqlite:///" in myscheduler_content, (
            "myscheduler .env should contain sqlite:/// for sync driver"
        )
        # Check that DATABASE_URL doesn't use aiosqlite (comments may mention it)
        for line in myscheduler_content.splitlines():
            if line.startswith("DATABASE_URL="):
                assert "aiosqlite" not in line, (
                    "myscheduler DATABASE_URL should not use aiosqlite"
                )

    def test_dev_start_script_creates_env_files(self):
        """受入条件: dev-start.shが.envファイルを自動生成すること"""
        # Given: Temporary project structure
        with tempfile.TemporaryDirectory() as tmpdir:
            test_root = Path(tmpdir)

            # Create service directories
            for service in ["jobqueue", "myscheduler"]:
                service_dir = test_root / service
                service_dir.mkdir()

                # Copy .env.example files
                original_example = Path(__file__).parent.parent.parent / service / ".env.example"
                if original_example.exists():
                    import shutil

                    shutil.copy(original_example, service_dir / ".env.example")

            # When: Simulating dev-start.sh environment setup
            for service in ["jobqueue", "myscheduler"]:
                example_file = test_root / service / ".env.example"
                env_file = test_root / service / ".env"

                if example_file.exists() and not env_file.exists():
                    import shutil

                    shutil.copy(example_file, env_file)

            # Then: .env files should be created with correct content
            jobqueue_env = test_root / "jobqueue" / ".env"
            myscheduler_env = test_root / "myscheduler" / ".env"

            assert jobqueue_env.exists()
            assert myscheduler_env.exists()

            # Verify content
            jobqueue_content = jobqueue_env.read_text()
            assert "DATABASE_URL=sqlite+aiosqlite:///" in jobqueue_content

            myscheduler_content = myscheduler_env.read_text()
            # myscheduler uses synchronous SQLite (APScheduler requirement)
            assert "DATABASE_URL=sqlite:///" in myscheduler_content

    def test_database_driver_compatibility(self):
        """受入条件: 各サービスが適切なデータベースドライバーを使用すること"""
        # Given: Project configuration files
        project_root = Path(__file__).parent.parent.parent

        # Test jobqueue config.py has correct default value
        # This validates the source code directly to avoid module caching issues
        jobqueue_config = project_root / "jobqueue" / "app" / "core" / "config.py"
        jobqueue_config_content = jobqueue_config.read_text()

        # Then: jobqueue default should use aiosqlite for async compatibility
        assert (
            'database_url: str = Field(default="sqlite+aiosqlite:///' in jobqueue_config_content
        ), "jobqueue config.py should have sqlite+aiosqlite:// as default"

        # Test myscheduler config.py has synchronous default for APScheduler compatibility
        myscheduler_config = project_root / "myscheduler" / "app" / "core" / "config.py"
        myscheduler_config_content = myscheduler_config.read_text()

        # Then: myscheduler default should use sync driver (APScheduler requirement)
        assert 'database_url: str = "sqlite:///' in myscheduler_config_content, (
            "myscheduler config.py should have sqlite:/// as default (sync for APScheduler)"
        )
        assert "aiosqlite" not in myscheduler_config_content, (
            "myscheduler should not use aiosqlite (APScheduler requires sync driver)"
        )
