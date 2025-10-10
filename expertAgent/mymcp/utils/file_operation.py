import pathlib

from core.logger import getlogger

logger = getlogger()


def delete_file(_file_path) -> bool:
    # 削除したいファイルのパスを指定して Path オブジェクトを作成
    file_path_obj = pathlib.Path(_file_path)

    try:
        # unlink() メソッドでファイルを削除
        # missing_ok=True にすると、ファイルが存在しなくてもエラーにならない
        file_path_obj.unlink(missing_ok=False)  # missing_ok=False (デフォルト)
        logger.info(f"File '{file_path_obj}' deleted successfully")
        return True
    except FileNotFoundError:
        # missing_ok=False の場合で、ファイルが存在しない場合に発生
        logger.warning(f"File '{file_path_obj}' not found")
        return False
    except PermissionError:
        logger.error(f"Permission denied to delete file '{file_path_obj}'")
        return False
    except IsADirectoryError:
        logger.error(
            f"'{file_path_obj}' is a directory, not a file"
        )
        # ディレクトリを削除する場合は Path.rmdir() (空の場合) や shutil.rmtree() を使います。
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting file: {e}", exc_info=True)
        return False
