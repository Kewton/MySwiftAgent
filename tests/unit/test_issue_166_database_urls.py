"""Unit tests for Issue #166: SQLAlchemy async driver configuration."""

import sys
from pathlib import Path


class TestJobQueueDatabaseURL:
    """Test jobqueue database URL configuration."""

    def test_jobqueue_default_database_url_uses_aiosqlite(self):
        """受入条件: jobqueueがsqlite+aiosqlite:///形式のDATABASE_URLで動作すること"""
        # Given: jobqueue config module import
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "jobqueue"))
        from app.core.config import Settings

        # When: Settings instance is created
        settings = Settings()

        # Then: Default database URL should use aiosqlite driver
        assert settings.database_url == "sqlite+aiosqlite:///./data/jobqueue.db"
        assert "sqlite+aiosqlite://" in settings.database_url


class TestMySchedulerDatabaseURL:
    """Test myscheduler database URL configuration."""

    def test_myscheduler_default_database_url_uses_sync_sqlite(self):
        """受入条件: myschedulerが同期SQLiteを使用すること（APScheduler互換性）"""
        # Given: Import myscheduler config directly with full path
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "myscheduler_config",
            Path(__file__).parent.parent.parent / "myscheduler" / "app" / "core" / "config.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # When: Settings instance is created
        settings = module.Settings()

        # Then: Default database URL should use synchronous SQLite (APScheduler requirement)
        assert settings.database_url == "sqlite:///./data/jobs.db"
        assert settings.database_url.startswith("sqlite:///")
        # APScheduler's SQLAlchemyJobStore requires sync driver, not aiosqlite
        assert "aiosqlite" not in settings.database_url
