import inspect
import logging
import logging.config
import logging.handlers
import os
import sys
import time
from pathlib import Path

from core.config import settings


def setup_logging(log_file_name: str = "expertagent.log"):
    """ロギングをセットアップします。

    Args:
        log_file_name: メインログファイル名（デフォルト: expertagent.log）
                      MCPサブプロセス用には mcp_stdio.log 等を指定可能

    Note:
        マルチワーカーモード対応のため、logging.basicConfig(force=True)を使用。
        各ワーカープロセスで確実にログ設定が適用されます。
    """
    log_level = settings.LOG_LEVEL
    log_dir = settings.LOG_DIR

    # ディレクトリが存在しない場合は作成
    log_dir_path = Path(log_dir)
    log_dir_path.mkdir(parents=True, exist_ok=True)

    # ログファイルのパス
    main_log_path = log_dir_path / log_file_name
    # エラーログは常に rotation.log を使用（ファイル名の一貫性のため）
    error_log_base = log_file_name.replace(".log", "_rotation.log")
    error_log_path = log_dir_path / error_log_base

    # ログハンドラーの作成
    stream_handler = logging.StreamHandler(sys.stdout)
    rotating_handler = logging.handlers.RotatingFileHandler(
        main_log_path,
        mode="a",
        maxBytes=1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    error_handler = logging.handlers.TimedRotatingFileHandler(
        error_log_path,
        when="S",
        interval=1,
        backupCount=5,
        encoding="utf-8",
    )

    # ERRORハンドラーはERRORレベルのみ
    error_handler.setLevel(logging.ERROR)

    handlers: list[logging.Handler] = [stream_handler, rotating_handler, error_handler]

    # ログ設定を適用（マルチワーカー対応）
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="[%(process)d-%(thread)d]-%(asctime)s-%(levelname)s-%(message)s",
        handlers=handlers,
        force=True,  # 既存の設定を強制的に上書き（マルチワーカー対応の鍵）
    )

    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured: log_dir={log_dir}, log_level={log_level}, PID={os.getpid()}"
    )


def getlogger():
    return logging.getLogger(__name__)


def setfileConfig(_path):
    logging.config.fileConfig(fname=_path)


def declogger(func):
    curframe = inspect.currentframe()
    calframe = inspect.getouterframes(curframe, 3)
    fn = calframe[1][1].split("/")
    filename = fn[len(fn) - 1]
    modulename = fn[len(fn) - 2]
    lineno = calframe[1][2]
    code_context = calframe[1][4]
    funcname = code_context[len(code_context) - 1]
    defaultmessage = (
        "["
        + modulename
        + "."
        + filename
        + ":"
        + str(lineno)
        + "]["
        + funcname.strip()
        + "]:"
    )

    def wrapper(*args, **kwargs):
        sw = StopWatch()
        sw.sw_start()
        _logger = getlogger()
        _logger.debug(defaultmessage + "--- start ---")
        kekka = func(*args, **kwargs)
        syorijikan = f"  *** 処理時間：{sw.sw_stop()} ***"
        _logger.debug(defaultmessage + "---- end ----:" + syorijikan)
        return kekka

    wrapper.__name__ = func.__name__
    return wrapper


def edtmessage(message):
    calframe = inspect.getouterframes(inspect.currentframe(), 2)
    fn = calframe[2][1].split("/")
    filename = fn[len(fn) - 1]
    modulename = fn[len(fn) - 2]
    lineno = calframe[1][2]
    return (
        "["
        + modulename
        + "."
        + filename
        + ":"
        + str(lineno)
        + "]["
        + calframe[1][3]
        + "]:"
        + str(message)
    )


def writedebuglog(message):
    getlogger().debug(edtmessage(message))
    return


def writeinfolog(message):
    getlogger().info(edtmessage(message))
    return


def writeerrorlog(message):
    getlogger().error(edtmessage(message))
    return


class StopWatch:
    def sw_start(self):
        self.__starttime = time.time()
        return

    def sw_stop(self):
        return time.time() - self.__starttime
