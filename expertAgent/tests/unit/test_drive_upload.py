"""GoogleDrive アップロード機能のユニットテスト"""

from unittest.mock import MagicMock, patch

import pytest

from mymcp.googleapis.drive import (
    check_file_exists_in_folder,
    create_subfolder_under_parent,
    extract_folder_id_from_url,
    generate_unique_filename,
    get_mime_type,
)


class TestExtractFolderIdFromUrl:
    """extract_folder_id_from_url のテスト"""

    def test_valid_url(self):
        """正常なURL形式からフォルダIDを抽出"""
        url = "https://drive.google.com/drive/folders/1Xrv6nJPuMB92s2DGcvZo_lH2H4cd_OsQ"
        folder_id = extract_folder_id_from_url(url)
        assert folder_id == "1Xrv6nJPuMB92s2DGcvZo_lH2H4cd_OsQ"

    def test_valid_url_with_query_params(self):
        """クエリパラメータ付きURLからフォルダIDを抽出"""
        url = "https://drive.google.com/drive/folders/1Xrv6nJPuMB92s2DGcvZo_lH2H4cd_OsQ?usp=drive_link"
        folder_id = extract_folder_id_from_url(url)
        assert folder_id == "1Xrv6nJPuMB92s2DGcvZo_lH2H4cd_OsQ"

    def test_invalid_url_format(self):
        """不正なURL形式でValueErrorを発生"""
        url = "https://invalid-url.com/folders/abc123"
        with pytest.raises(ValueError, match="Invalid Google Drive folder URL"):
            extract_folder_id_from_url(url)

    def test_invalid_url_missing_folder_id(self):
        """フォルダIDが欠けているURLでValueErrorを発生"""
        url = "https://drive.google.com/drive/folders/"
        with pytest.raises(ValueError, match="Invalid Google Drive folder URL"):
            extract_folder_id_from_url(url)


class TestGetMimeType:
    """get_mime_type のテスト"""

    def test_pdf_file(self):
        """PDFファイルのMIMEタイプ判定"""
        assert get_mime_type("document.pdf") == "application/pdf"

    def test_text_file(self):
        """テキストファイルのMIMEタイプ判定"""
        assert get_mime_type("readme.txt") == "text/plain"

    def test_mp3_file(self):
        """MP3ファイルのMIMEタイプ判定"""
        assert get_mime_type("audio.mp3") == "audio/mpeg"

    def test_jpg_file(self):
        """JPEGファイルのMIMEタイプ判定"""
        assert get_mime_type("image.jpg") == "image/jpeg"

    def test_png_file(self):
        """PNGファイルのMIMEタイプ判定"""
        assert get_mime_type("image.png") == "image/png"

    def test_unknown_extension(self):
        """未知の拡張子で application/octet-stream を返す"""
        assert get_mime_type("file.unknown") == "application/octet-stream"

    def test_no_extension(self):
        """拡張子なしで application/octet-stream を返す"""
        assert get_mime_type("file") == "application/octet-stream"


class TestCheckFileExistsInFolder:
    """check_file_exists_in_folder のテスト"""

    @patch("mymcp.googleapis.drive.get_googleapis_service")
    def test_file_exists(self, mock_get_service):
        """ファイルが存在する場合 True を返す"""
        # モックサービス設定
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.files().list().execute.return_value = {
            "files": [{"id": "file123", "name": "test.txt"}]
        }

        result = check_file_exists_in_folder("folder123", "test.txt")
        assert result is True

    @patch("mymcp.googleapis.drive.get_googleapis_service")
    def test_file_not_exists(self, mock_get_service):
        """ファイルが存在しない場合 False を返す"""
        # モックサービス設定
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.files().list().execute.return_value = {"files": []}

        result = check_file_exists_in_folder("folder123", "test.txt")
        assert result is False

    @patch("mymcp.googleapis.drive.get_googleapis_service")
    def test_api_error(self, mock_get_service):
        """API エラー時に False を返す"""
        # モックサービス設定
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.files().list().execute.side_effect = Exception("API Error")

        result = check_file_exists_in_folder("folder123", "test.txt")
        assert result is False


class TestGenerateUniqueFilename:
    """generate_unique_filename のテスト"""

    @patch("mymcp.googleapis.drive.check_file_exists_in_folder")
    def test_no_duplicate(self, mock_check_exists):
        """重複がない場合、元のファイル名を返す"""
        mock_check_exists.return_value = False
        result = generate_unique_filename("test.txt", "folder123")
        assert result == "test.txt"

    @patch("mymcp.googleapis.drive.check_file_exists_in_folder")
    def test_with_duplicate(self, mock_check_exists):
        """重複がある場合、連番と日時を付与したファイル名を返す"""
        # 1回目: 元のファイル名が存在
        # 2回目: リネーム後のファイル名が存在しない
        mock_check_exists.side_effect = [True, False]

        result = generate_unique_filename("test.txt", "folder123")

        # ファイル名形式の検証: test_001_YYYYMMDD_HHMMSS.txt
        assert result.startswith("test_001_")
        assert result.endswith(".txt")
        assert len(result) == len("test_001_20251015_143022.txt")

    @patch("mymcp.googleapis.drive.check_file_exists_in_folder")
    def test_multiple_duplicates(self, mock_check_exists):
        """複数の重複がある場合、連番をインクリメント"""
        # 1回目: 元のファイル名が存在
        # 2回目: test_001_xxx.txt が存在
        # 3回目: test_002_xxx.txt が存在しない
        mock_check_exists.side_effect = [True, True, False]

        result = generate_unique_filename("test.txt", "folder123")

        assert result.startswith("test_002_")
        assert result.endswith(".txt")

    @patch("mymcp.googleapis.drive.check_file_exists_in_folder")
    def test_max_retries_exceeded(self, mock_check_exists):
        """最大試行回数を超えた場合 RuntimeError を発生"""
        # 常に重複が存在する
        mock_check_exists.return_value = True

        with pytest.raises(
            RuntimeError, match="Failed to generate unique filename after"
        ):
            generate_unique_filename("test.txt", "folder123")

    @patch("mymcp.googleapis.drive.check_file_exists_in_folder")
    def test_no_extension(self, mock_check_exists):
        """拡張子なしのファイル名でも正しく処理"""
        mock_check_exists.side_effect = [True, False]

        result = generate_unique_filename("README", "folder123")

        assert result.startswith("README_001_")
        assert "." not in result.split("_")[-1]  # 最後の部分に拡張子がない


class TestIntegrationScenarios:
    """統合シナリオテスト"""

    @patch("mymcp.googleapis.drive.get_googleapis_service")
    def test_upload_workflow(self, mock_get_service):
        """アップロードワークフロー全体のテスト"""
        # 1. URL からフォルダID抽出
        folder_url = "https://drive.google.com/drive/folders/test_folder_id"
        folder_id = extract_folder_id_from_url(folder_url)
        assert folder_id == "test_folder_id"

        # 2. MIMEタイプ判定
        mime_type = get_mime_type("report.pdf")
        assert mime_type == "application/pdf"

        # 3. ファイル存在チェック（存在しない）
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.files().list().execute.return_value = {"files": []}

        exists = check_file_exists_in_folder(folder_id, "report.pdf")
        assert exists is False

        # 4. ユニークファイル名生成（重複なし）
        unique_name = generate_unique_filename("report.pdf", folder_id)
        assert unique_name == "report.pdf"


class TestCreateSubfolderUnderParent:
    """create_subfolder_under_parent のテスト"""

    @patch("mymcp.googleapis.drive.get_googleapis_service")
    def test_create_single_subfolder(self, mock_get_service):
        """単一サブフォルダ作成"""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # 既存フォルダなし → 新規作成
        mock_service.files().list().execute.return_value = {"files": []}
        mock_service.files().create().execute.return_value = {"id": "new_folder_123"}

        result = create_subfolder_under_parent("parent_123", "reports")
        assert result == "new_folder_123"

    @patch("mymcp.googleapis.drive.get_googleapis_service")
    def test_create_nested_subfolders(self, mock_get_service):
        """複数階層サブフォルダ作成"""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # reports作成 → 2025作成
        mock_service.files().list().execute.side_effect = [
            {"files": []},  # reports不存在
            {"files": []},  # 2025不存在
        ]
        mock_service.files().create().execute.side_effect = [
            {"id": "reports_id"},
            {"id": "2025_id"},
        ]

        result = create_subfolder_under_parent("parent_123", "reports/2025")
        assert result == "2025_id"

    @patch("mymcp.googleapis.drive.get_googleapis_service")
    def test_existing_subfolder(self, mock_get_service):
        """既存フォルダが存在する場合"""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # 既存フォルダ発見
        mock_service.files().list().execute.return_value = {
            "files": [{"id": "existing_folder_123", "name": "reports"}]
        }

        result = create_subfolder_under_parent("parent_123", "reports")
        assert result == "existing_folder_123"

    def test_empty_path(self):
        """空文字列パスでValueError"""
        with pytest.raises(ValueError, match="subdirectory_path cannot be empty"):
            create_subfolder_under_parent("parent_123", "")

    @patch("mymcp.googleapis.drive.get_googleapis_service")
    def test_api_error(self, mock_get_service):
        """Drive API エラー時"""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.files().list().execute.side_effect = Exception("API Error")

        with pytest.raises(RuntimeError, match="Failed to create subfolder"):
            create_subfolder_under_parent("parent_123", "reports")


class TestCreateFileFromContent:
    """_create_file_from_content のテスト"""

    def test_create_text_file(self, tmp_path):
        """テキストコンテンツからファイル作成"""
        from mymcp.stdio_action import _create_file_from_content

        file_path = str(tmp_path / "test.txt")
        content = "Hello, World!"
        file_format = "txt"

        result = _create_file_from_content(file_path, content, file_format)

        assert result == file_path
        assert tmp_path.joinpath("test.txt").exists()
        with open(result, encoding="utf-8") as f:
            assert f.read() == "Hello, World!"

    def test_create_binary_file(self, tmp_path):
        """バイナリコンテンツからファイル作成"""
        from mymcp.stdio_action import _create_file_from_content

        file_path = str(tmp_path / "test.bin")
        content = b"\x89PNG\r\n\x1a\n\x00\x00"
        file_format = "bin"

        result = _create_file_from_content(file_path, content, file_format)

        assert result == file_path
        with open(result, "rb") as f:
            assert f.read() == content

    def test_create_base64_file(self, tmp_path):
        """Base64エンコード文字列からファイル作成"""
        from mymcp.stdio_action import _create_file_from_content

        file_path = str(tmp_path / "test.txt")
        content = "SGVsbG8sIFdvcmxkIQ=="  # "Hello, World!" in Base64
        file_format = "txt"

        result = _create_file_from_content(file_path, content, file_format)

        assert result == file_path
        with open(result, "rb") as f:
            # Base64デコードされた内容が書き込まれている
            assert f.read() == b"Hello, World!"

    def test_rename_on_duplicate(self, tmp_path):
        """既存ファイルがある場合、リネームする"""
        from mymcp.stdio_action import _create_file_from_content

        # 既存ファイル作成
        existing_file = tmp_path / "test.txt"
        existing_file.write_text("Existing content")

        file_path = str(tmp_path / "test.txt")
        content = "New content"
        file_format = "txt"

        result = _create_file_from_content(file_path, content, file_format)

        # リネームされたファイルが作成されている
        assert result != file_path
        assert result.startswith(str(tmp_path / "test_001_"))
        assert result.endswith(".txt")

        # 既存ファイルは変更されていない
        assert existing_file.read_text() == "Existing content"

        # 新ファイルの内容が正しい
        with open(result, encoding="utf-8") as f:
            assert f.read() == "New content"

    def test_create_parent_directory(self, tmp_path):
        """親ディレクトリが存在しない場合、自動作成"""
        from mymcp.stdio_action import _create_file_from_content

        file_path = str(tmp_path / "new_dir" / "test.txt")
        content = "Test content"
        file_format = "txt"

        result = _create_file_from_content(file_path, content, file_format)

        assert result == file_path
        assert tmp_path.joinpath("new_dir", "test.txt").exists()

    def test_unsupported_content_type(self, tmp_path):
        """未対応のコンテンツタイプでエラー"""
        from mymcp.stdio_action import _create_file_from_content

        file_path = str(tmp_path / "test.txt")
        content = ["invalid", "content"]  # リスト型（未対応）
        file_format = "txt"

        with pytest.raises(RuntimeError, match="Failed to create file"):
            _create_file_from_content(file_path, content, file_format)
