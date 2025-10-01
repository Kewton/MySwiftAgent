import pathlib


def delete_file(_file_path) -> bool:
    # 削除したいファイルのパスを指定して Path オブジェクトを作成
    file_path_obj = pathlib.Path(_file_path)
 
    try:
        # unlink() メソッドでファイルを削除
        # missing_ok=True にすると、ファイルが存在しなくてもエラーにならない
        file_path_obj.unlink(missing_ok=False) # missing_ok=False (デフォルト)
        print(f"ファイル '{file_path_obj}' を削除しました。")
        return True
    except FileNotFoundError:
        # missing_ok=False の場合で、ファイルが存在しない場合に発生
        print(f"エラー: ファイル '{file_path_obj}' が見つかりません。")
        return False
    except PermissionError:
        print(f"エラー: ファイル '{file_path_obj}' を削除する権限がありません。")
        return False
    except IsADirectoryError:
        print(f"エラー: '{file_path_obj}' はディレクトリです。ファイルのパスを指定してください。")
        # ディレクトリを削除する場合は Path.rmdir() (空の場合) や shutil.rmtree() を使います。
        return False
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")
        return False