import datetime
import uuid
from pathlib import Path
from typing import Optional

from core.config import settings
from core.logger import getlogger
from mymcp.googleapis.drive import (
    SpreadsheetDB,
    get_google_drive_file_links,
    get_or_create_folder,
    resumable_upload,
    upload_file,
)
from mymcp.tts.tts import tts
from mymcp.utils.file_operation import delete_file

logger = getlogger()


SPREADSHEET_ID = settings.SPREADSHEET_ID
SHEET_NAME = "podcast"


def tts_and_upload_drive(input_message, file_name):
    """ツールの本体ロジック（同期）"""
    logger.info("tts_and_upload_driveを実行します")
    logger.info(f"input_message: {input_message}")
    logger.info(f"file_name: {file_name}")
    temp_dir = Path("./temp")
    speech_file_path: Optional[Path] = None  # finally スコープで参照するため

    # 引数のデフォルト値がNoneの場合の処理 (Pydanticがデフォルト値を適用するはずだが念のため)
    if file_name is None:
        file_name = "AIエージェントからの手紙"

    name = "tts_and_upload_to_google_drive"
    target_folder_name = "./MyAiAgent/podcast"

    try:
        # 0. 一時ディレクトリの確認/作成
        try:
            temp_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return f"エラー: 一時ディレクトリ '{temp_dir}' の作成に失敗しました: {e}"

        # 一時ファイルパスの生成
        unique_filename = f"{uuid.uuid4()}.mp3"
        speech_file_path = temp_dir / unique_filename

        # 1. テキスト -> 音声ファイル (TTS)
        logger.info(f"Generating speech file at '{speech_file_path}'")
        try:
            # tts関数がファイルパス(文字列)とテキストを引数に取ることを想定
            tts(str(speech_file_path), input_message)
            # 生成されたファイルが存在し、空でないかを確認
            if not speech_file_path.is_file() or speech_file_path.stat().st_size == 0:
                # TTS失敗時のエラーメッセージ
                logger.error(
                    f"TTS failed: File '{speech_file_path}' does not exist or is empty."
                )
                return f"エラー: TTS処理に失敗しました。音声ファイルが生成されませんでした。Text: '{input_message[:50]}...'"
        except Exception as e:
            # TTS実行中の予期せぬエラー
            logger.error(f"Error during TTS: {e}", exc_info=True)
            return f"エラー: 音声ファイル生成中に予期せぬエラーが発生しました: {e}"
        logger.info("Speech file generated successfully")

        # 2. Google Drive アップロード先フォルダIDの取得
        logger.info(f"Searching for Google Drive folder '{target_folder_name}'")
        folder_id: Optional[str] = None
        try:
            # 注意: get_file_id_and_mime_typeは同名フォルダ/ファイルが複数ある場合、
            # 意図しないものを返す可能性があります。より堅牢にするには、
            # mimeType='application/vnd.google-apps.folder' を条件に加えるなどの改善を検討。
            # _name, folder_id, mimeType = get_file_id_and_mime_type(target_folder_name)
            folder_id = get_or_create_folder(target_folder_name)

            # if not folder_id:
            #     return f"エラー: Google Drive でフォルダ '{target_folder_name}' が見つかりません。"
            # if mimeType != 'application/vnd.google-apps.folder':
            #     return f"エラー: Google Drive で見つかった '{target_folder_name}' はフォルダではありません (Type: {mimeType})。"
        except Exception as e:
            # フォルダ検索中のエラー
            logger.error(f"Error during Google Drive folder search: {e}", exc_info=True)
            return f"エラー: Google Drive フォルダ '{target_folder_name}' の検索中にエラーが発生しました: {e}"
        logger.info(f"Found folder ID: {folder_id}")

        # 3. Google Drive へのファイルアップロード
        drive_filename = f"{file_name}.mp3"
        logger.info(f"Uploading '{speech_file_path.name}' as '{drive_filename}' to folder '{folder_id}'")
        uploaded_file_id: Optional[str] = None
        try:
            # resumable_upload がアップロード成功時にファイルIDを返すことを想定
            uploaded_file_id = resumable_upload(
                save_file_name_in_drive=drive_filename,
                upload_file_path=str(speech_file_path),
                mime_type="audio/mpeg",  # MP3の正しいMIMEタイプ
                folder_id=folder_id,
            )
            if not uploaded_file_id:
                return f"エラー: Google Drive へのファイル '{drive_filename}' のアップロードに失敗しました（ファイルIDが返されませんでした）。"
        except Exception as e:
            # アップロード中のエラー
            logger.error(f"Error during Google Drive upload: {e}", exc_info=True)
            return f"エラー: Google Drive へのアップロード中にエラーが発生しました: {e}"
        logger.info(f"File uploaded successfully. File ID: {uploaded_file_id}")

        # 4. アップロードされたファイルのリンク取得
        logger.info(f"Getting links for file ID '{uploaded_file_id}'")
        try:
            link_info = get_google_drive_file_links(uploaded_file_id)
            if not link_info or not link_info.get("webViewLink"):
                # リンク取得失敗、または webViewLink が見つからない場合
                return f"エラー: アップロードされたファイル (ID: {uploaded_file_id}) のリンクを取得できませんでした。"

            web_view_link = link_info["webViewLink"]
            logger.info(f"Successfully retrieved webViewLink: {web_view_link}")
            # 成功時の返り値 (AI に分かりやすいメッセージ形式)

            # ---------------
            # ポッドキャスト生成情報を記録
            # マークダウンファイル生成
            temp_dir = Path("./temp")
            try:
                temp_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                logger.error(f"Error creating temporary directory '{temp_dir}': {e}")
                return (
                    f"エラー: 一時ディレクトリ '{temp_dir}' の作成に失敗しました: {e}"
                )
            unique_filename = f"{uuid.uuid4()}.md"
            md_file_path = temp_dir / unique_filename

            try:
                with open(md_file_path, "w", encoding="utf-8") as f:
                    f.write(input_message)
            except IOError as e:
                logger.error(f"Error writing to file '{md_file_path}': {e}", exc_info=True)

            # googl drive にアップロード
            folder_id = get_or_create_folder("./MyAiAgent/podcast_input")
            logger.info("Uploading markdown file to Google Drive")
            _id = upload_file(
                f"{drive_filename}.md", md_file_path, "text/plain", folder_id
            )
            delete_file(str(md_file_path))

            db = SpreadsheetDB(SPREADSHEET_ID)
            new_products = [
                [
                    uploaded_file_id,
                    drive_filename,
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    web_view_link,
                    get_google_drive_file_links(_id)["webViewLink"],
                ]
            ]
            db.append_rows(SHEET_NAME, new_products)
            # ---------------

            logger.info(
                f"音声ファイル「{drive_filename}」を Google Drive のフォルダ「{target_folder_name}」にアップロードしました。表示用リンク: {web_view_link}"
            )
            return f"音声ファイル「{drive_filename}」を Google Drive のフォルダ「{target_folder_name}」にアップロードしました。表示用リンク: {web_view_link}"

        except Exception as e:
            # リンク取得中のエラー
            logger.error(f"Error during link retrieval: {e}", exc_info=True)
            return f"エラー: アップロードされたファイルのリンク取得中にエラーが発生しました (File ID: {uploaded_file_id}): {e}"

    finally:
        # 5. 一時ファイルの削除 (tryブロックの成功・失敗に関わらず実行)
        if speech_file_path and speech_file_path.exists():
            logger.info(f"Deleting temporary file '{speech_file_path}'")
            try:
                # delete_file 関数がファイルパス文字列を期待する場合
                delete_file(str(speech_file_path))
                logger.info("Temporary file deleted")
            except Exception as e:
                # 一時ファイルの削除失敗は警告に留める (主要処理ではないため)
                logger.warning(
                    f"Failed to delete temporary file '{speech_file_path}': {e}"
                )
