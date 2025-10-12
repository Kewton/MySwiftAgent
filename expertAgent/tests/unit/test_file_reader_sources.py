"""Unit tests for file_reader_sources module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mymcp.tool.file_reader_sources import (
    download_from_google_drive,
    download_from_url,
    read_from_local,
)


class TestDownloadFromUrl:
    """Test download_from_url function."""

    @pytest.mark.asyncio
    async def test_download_from_url_success(self):
        """Test successful download from URL."""
        # Use a simple test URL
        test_url = (
            "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
        )

        file_path, mime_type = await download_from_url(test_url)

        try:
            assert file_path.exists()
            assert mime_type in ("application/pdf", "application/octet-stream")
            assert file_path.stat().st_size > 0
        finally:
            # Cleanup
            if file_path.exists():
                file_path.unlink()

    @pytest.mark.asyncio
    async def test_download_from_url_invalid_url(self):
        """Test download fails for invalid URL."""
        invalid_url = "https://nonexistent-domain-12345.com/file.pdf"

        with pytest.raises(ValueError, match="Download failed"):
            await download_from_url(invalid_url)

    @pytest.mark.asyncio
    async def test_download_from_url_404(self):
        """Test download fails for 404 response."""
        url_404 = "https://httpbin.org/status/404"

        with pytest.raises(ValueError, match="Failed to download from URL"):
            await download_from_url(url_404)


class TestDownloadFromGoogleDrive:
    """Test download_from_google_drive function."""

    @patch("mymcp.tool.file_reader_sources.get_googleapis_service")
    def test_download_from_google_drive_success(self, mock_get_service):
        """Test successful download from Google Drive."""
        # Mock Google Drive service
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # Mock file metadata
        mock_service.files().get().execute.return_value = {
            "name": "test.pdf",
            "mimeType": "application/pdf",
        }

        # Mock file download
        mock_request = MagicMock()
        mock_service.files().get_media.return_value = mock_request

        # Create a mock downloader that simulates download
        with patch(
            "mymcp.tool.file_reader_sources.MediaIoBaseDownload"
        ) as mock_downloader_class:
            mock_downloader = MagicMock()
            mock_downloader.next_chunk.side_effect = [
                (MagicMock(progress=lambda: 0.5, resumable_progress=512), False),
                (MagicMock(progress=lambda: 1.0, resumable_progress=1024), True),
            ]
            mock_downloader_class.return_value = mock_downloader

            url = "https://drive.google.com/file/d/1ABC123XYZ/view"
            file_path, mime_type = download_from_google_drive(url)

            assert file_path.exists()
            assert mime_type == "application/pdf"
            # Cleanup
            file_path.unlink()

    def test_download_from_google_drive_invalid_url(self):
        """Test download fails for invalid URL."""
        invalid_url = "https://example.com/not-a-drive-url"

        with pytest.raises(ValueError, match="Could not extract file ID"):
            download_from_google_drive(invalid_url)

    @patch("mymcp.tool.file_reader_sources.get_googleapis_service")
    def test_download_from_google_drive_no_service(self, mock_get_service):
        """Test download fails when service is unavailable."""
        mock_get_service.return_value = None

        url = "https://drive.google.com/file/d/1ABC123XYZ/view"

        with pytest.raises(ConnectionError, match="Failed to get Google Drive service"):
            download_from_google_drive(url)

    @patch("mymcp.tool.file_reader_sources.get_googleapis_service")
    def test_download_from_google_drive_file_not_found(self, mock_get_service):
        """Test download fails when file is not found."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # Mock 404 error
        mock_service.files().get().execute.side_effect = Exception("404 File not found")

        url = "https://drive.google.com/file/d/1NOTFOUND/view"

        with pytest.raises(FileNotFoundError, match="File not found on Google Drive"):
            download_from_google_drive(url)


class TestReadFromLocal:
    """Test read_from_local function."""

    def test_read_from_local_success(self):
        """Test successful read from local file."""
        test_file = Path(tempfile.gettempdir()) / "test_local.txt"
        test_file.write_text("Test content")

        try:
            file_path, mime_type = read_from_local(str(test_file))

            # Verify file exists and is resolved to absolute path
            assert file_path.exists()
            assert file_path.is_absolute()
            # Both paths should resolve to the same file
            assert file_path.samefile(test_file)
            assert mime_type == "text/plain"
        finally:
            test_file.unlink()

    def test_read_from_local_nonexistent_file(self):
        """Test read fails for nonexistent file."""
        with pytest.raises(FileNotFoundError, match="File not found"):
            read_from_local("/tmp/nonexistent_file_99999.txt")

    def test_read_from_local_outside_allowed_dirs(self):
        """Test read fails for file outside allowed directories."""
        with pytest.raises(ValueError, match="Path outside allowed directories"):
            read_from_local("/etc/passwd")

    def test_read_from_local_large_file(self):
        """Test read fails for file exceeding size limit."""
        from mymcp.tool.file_reader_utils import MAX_FILE_SIZE

        test_file = Path(tempfile.gettempdir()) / "test_large.bin"
        # Create a file larger than MAX_FILE_SIZE
        test_file.write_bytes(b"0" * (MAX_FILE_SIZE + 1024))

        try:
            with pytest.raises(ValueError, match="File size .* exceeds"):
                read_from_local(str(test_file))
        finally:
            if test_file.exists():
                test_file.unlink()
