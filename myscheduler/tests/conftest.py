import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.db.session import scheduler_manager
from app.main import create_app


@pytest.fixture
def client():
    """テスト用のFastAPIクライアント"""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def temp_db():
    """テスト用の一時データベース"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_db_path = f.name

    # テスト用のデータベースパスに変更
    original_url = scheduler_manager.jobstore.url
    scheduler_manager.jobstore.url = f"sqlite:///{temp_db_path}"

    yield temp_db_path

    # 元に戻す
    scheduler_manager.jobstore.url = original_url

    # 一時ファイルを削除
    if os.path.exists(temp_db_path):
        os.unlink(temp_db_path)


@pytest.fixture(autouse=True)
def cleanup_jobs():
    """各テスト後にジョブをクリーンアップ"""
    yield
    # 全てのジョブを削除
    scheduler = scheduler_manager.get_scheduler()
    for job in scheduler.get_jobs():
        scheduler.remove_job(job.id)
