import inspect
import logging
import logging.config
import os
import time

from core.config import settings

# ログセットアップが実行されたかを保持するフラグ
logging_setup_done = False


def setup_logging(log_file_name: str = "app.log"):
    """ロギングをセットアップします。

    Args:
        log_file_name: メインログファイル名（デフォルト: app.log）
                      MCPサブプロセス用には mcp_stdio.log 等を指定可能
    """
    global logging_setup_done

    # デバッグトレース
    debug_trace_file = "/tmp/mcp_stdio_debug.log"
    try:
        with open(debug_trace_file, "a") as f:
            f.write(
                f"[logger.py] setup_logging() called with log_file_name='{log_file_name}'\n"
            )
            f.write(
                f"[logger.py] logging_setup_done={logging_setup_done}, PID={os.getpid()}\n"
            )
    except Exception:
        pass

    if logging_setup_done:
        try:
            with open(debug_trace_file, "a") as f:
                f.write("[logger.py] Skipping setup (already done)\n")
        except Exception:
            pass
        return  # すでに実行済みなら何もしない
    else:
        print("setup_logging start")

    log_level = settings.LOG_LEVEL
    log_dir = settings.LOG_DIR

    # ディレクトリが存在しない場合は作成
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
            print(f"Directory {log_dir} created.")
        except OSError as e:
            # ディレクトリ作成失敗時は /tmp にフォールバック
            err_msg = f"Failed to create {log_dir}: {e}. Falling back to /tmp"
            print(err_msg)
            log_dir = "/tmp"
    else:
        print(f"Directory {log_dir} already exists.")

    # ログファイルのパス
    main_log_path = os.path.join(log_dir, log_file_name)
    # エラーログは常に rotation.log を使用（ファイル名の一貫性のため）
    error_log_base = log_file_name.replace(".log", "_rotation.log")
    error_log_path = os.path.join(log_dir, error_log_base)

    # ログ設定の定義
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "_formatter": {
                "format": "[%(process)d-%(thread)d]-%(asctime)s-%(levelname)s-%(message)s"
            },
        },
        "handlers": {
            "rotatinghandler": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_level,
                "formatter": "_formatter",
                "filename": main_log_path,
                "mode": "a",
                "maxBytes": 1024 * 1024,
                "backupCount": 5,
                "encoding": "utf-8",
            },
            "timedrotatinghandler": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "level": "ERROR",
                "formatter": "_formatter",
                "filename": error_log_path,
                "when": "S",  # 秒ごとのローテーション
                "interval": 1,  # ローテーション間隔
                "backupCount": 5,
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "": {  # root logger
                "level": log_level,
                "handlers": ["rotatinghandler", "timedrotatinghandler"],
            },
        },
    }

    # ログ設定を適用
    logging.config.dictConfig(log_config)
    logging.info(f"Logging is set up. Log file: {main_log_path}")

    # デバッグトレース
    try:
        with open(debug_trace_file, "a") as f:
            f.write("[logger.py] Log config applied successfully\n")
            f.write(f"[logger.py] Main log: {main_log_path}\n")
            f.write(f"[logger.py] Error log: {error_log_path}\n")
    except Exception:
        pass

    # 実行フラグをTrueに設定
    logging_setup_done = True


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
