import logging
import sys
from typing import Any

from .config import settings


def setup_logging() -> None:
    """ログ設定を初期化"""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format=settings.log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    # APSchedulerのログレベルを調整
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """ロガーを取得"""
    return logging.getLogger(name)