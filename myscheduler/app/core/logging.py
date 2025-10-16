import logging
import sys
from pathlib import Path

from .config import settings


def setup_logging() -> None:
    """ログ設定を初期化"""
    # ログディレクトリの作成
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format=settings.log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, mode="a", encoding="utf-8"),
        ],
        force=True,  # Force reconfiguration even if logging was already configured
    )

    # APSchedulerのログレベルを調整
    logging.getLogger("apscheduler").setLevel(logging.WARNING)

    # ログ設定完了メッセージ
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured: log_dir={log_dir}, log_level={settings.log_level}"
    )


def get_logger(name: str) -> logging.Logger:
    """ロガーを取得"""
    return logging.getLogger(name)
