from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.v1 import health, jobs
from .core.config import settings
from .core.logging import setup_logging
from .db.session import scheduler_manager
from .services.http_service import http_service


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """アプリケーションのライフサイクル管理"""
    # 起動時
    setup_logging()
    scheduler_manager.start()
    yield
    # 終了時
    scheduler_manager.shutdown()
    await http_service.close()


def create_app() -> FastAPI:
    """FastAPIアプリケーションを作成"""

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # ルーターの登録
    app.include_router(health.router)
    app.include_router(jobs.router, prefix="/api/v1")

    return app


# アプリケーションインスタンス
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        reload=settings.debug,
    )
