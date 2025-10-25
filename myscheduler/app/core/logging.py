import logging
import logging.handlers
import os
import sys
from pathlib import Path

from .config import settings


def setup_logging() -> None:
    """ログ設定を初期化（マルチワーカー対応）"""
    # ログディレクトリの作成
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "myscheduler.log"
    error_log_file = log_dir / "myscheduler_rotation.log"

    # Create handlers
    stream_handler = logging.StreamHandler(sys.stdout)
    rotating_handler = logging.handlers.RotatingFileHandler(
        log_file,
        mode="a",
        maxBytes=1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    error_handler = logging.handlers.TimedRotatingFileHandler(
        error_log_file,
        when="S",
        interval=1,
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)

    handlers: list[logging.Handler] = [stream_handler, rotating_handler, error_handler]

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="[%(process)d-%(thread)d]-%(asctime)s-%(levelname)s-%(message)s",
        handlers=handlers,
        force=True,  # Force reconfiguration for multi-worker mode
    )

    # APSchedulerのログレベルを調整
    logging.getLogger("apscheduler").setLevel(logging.WARNING)

    # ログ設定完了メッセージ
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured: log_dir={log_dir}, log_level={settings.log_level}, PID={os.getpid()}"
    )


def get_logger(name: str) -> logging.Logger:
    """ロガーを取得"""
    return logging.getLogger(name)
