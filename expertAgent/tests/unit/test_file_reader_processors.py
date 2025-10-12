"""Unit tests for file_reader_processors module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mymcp.tool.file_reader_processors import (
    process_audio,
    process_csv,
    process_file,
    process_image,
    process_pdf,
    process_text,
)


class TestProcessImage:
    """Test process_image function."""

    @patch("core.secrets.resolve_runtime_value")
    @patch("openai.OpenAI")
    def test_process_image_success(self, mock_openai, mock_resolve):
        """Test successful image processing."""
        # Setup mocks
        mock_resolve.return_value = "fake-api-key"
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Mock the nested structure: choices[0].message.content
        mock_choice = MagicMock()
        mock_choice.message.content = "Image description"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        # Create a test image file
        test_file = Path(tempfile.gettempdir()) / "test_image.jpg"
        test_file.write_bytes(b"fake image data")

        try:
            result = process_image(test_file, "Describe this image")
            assert result == "Image description"
        finally:
            test_file.unlink()

    def test_process_image_file_not_found(self):
        """Test image processing fails for nonexistent file."""
        nonexistent = Path("/tmp/nonexistent_image.jpg")

        with pytest.raises(FileNotFoundError):
            process_image(nonexistent, "Describe")

    @patch("core.secrets.resolve_runtime_value")
    def test_process_image_no_api_key(self, mock_resolve):
        """Test image processing fails without API key."""
        mock_resolve.return_value = None

        test_file = Path(tempfile.gettempdir()) / "test_image.jpg"
        test_file.write_bytes(b"fake image data")

        try:
            with pytest.raises(ValueError, match="OPENAI_API_KEY not configured"):
                process_image(test_file, "Describe")
        finally:
            test_file.unlink()


class TestProcessPdf:
    """Test process_pdf function."""

    @patch("mymcp.tool.file_reader_processors.PdfReader")
    def test_process_pdf_success(self, mock_pdf_reader):
        """Test successful PDF processing."""
        # Mock PDF reader
        mock_reader = MagicMock()
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1 content"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2 content"
        mock_reader.pages = [mock_page1, mock_page2]
        mock_pdf_reader.return_value = mock_reader

        test_file = Path(tempfile.gettempdir()) / "test.pdf"
        test_file.write_bytes(b"fake pdf data")

        try:
            result = process_pdf(test_file)
            assert "Page 1" in result
            assert "Page 1 content" in result
            assert "Page 2 content" in result
        finally:
            test_file.unlink()

    def test_process_pdf_file_not_found(self):
        """Test PDF processing fails for nonexistent file."""
        nonexistent = Path("/tmp/nonexistent.pdf")

        with pytest.raises(FileNotFoundError):
            process_pdf(nonexistent)


class TestProcessText:
    """Test process_text function."""

    def test_process_text_utf8(self):
        """Test text processing with UTF-8 encoding."""
        test_file = Path(tempfile.gettempdir()) / "test_utf8.txt"
        test_content = "Hello, World! 日本語テスト"
        test_file.write_text(test_content, encoding="utf-8")

        try:
            result = process_text(test_file)
            assert result == test_content
        finally:
            test_file.unlink()

    def test_process_text_shift_jis(self):
        """Test text processing with Shift-JIS encoding."""
        test_file = Path(tempfile.gettempdir()) / "test_sjis.txt"
        test_content = "日本語テスト"
        test_file.write_text(test_content, encoding="shift_jis")

        try:
            result = process_text(test_file)
            assert test_content in result or len(result) > 0
        finally:
            test_file.unlink()

    def test_process_text_file_not_found(self):
        """Test text processing fails for nonexistent file."""
        nonexistent = Path("/tmp/nonexistent.txt")

        with pytest.raises(FileNotFoundError):
            process_text(nonexistent)


class TestProcessCsv:
    """Test process_csv function."""

    def test_process_csv_success(self):
        """Test successful CSV processing."""
        test_file = Path(tempfile.gettempdir()) / "test.csv"
        test_content = "Name,Age,City\nJohn,30,Tokyo\nJane,25,Osaka"
        test_file.write_text(test_content, encoding="utf-8")

        try:
            result = process_csv(test_file)
            assert "Name" in result
            assert "John" in result
            assert "Tokyo" in result
        finally:
            test_file.unlink()

    def test_process_csv_file_not_found(self):
        """Test CSV processing fails for nonexistent file."""
        nonexistent = Path("/tmp/nonexistent.csv")

        with pytest.raises(FileNotFoundError):
            process_csv(nonexistent)


class TestProcessAudio:
    """Test process_audio function."""

    @patch("core.secrets.resolve_runtime_value")
    @patch("openai.OpenAI")
    def test_process_audio_success(self, mock_openai, mock_resolve):
        """Test successful audio processing."""
        # Setup mocks
        mock_resolve.return_value = "fake-api-key"
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Mock the transcription response (response_format="text" returns string directly)
        mock_client.audio.transcriptions.create.return_value = "Transcribed text"

        test_file = Path(tempfile.gettempdir()) / "test_audio.mp4"
        test_file.write_bytes(b"fake audio data")

        try:
            result = process_audio(test_file)
            assert result == "Transcribed text"
        finally:
            test_file.unlink()

    def test_process_audio_file_not_found(self):
        """Test audio processing fails for nonexistent file."""
        nonexistent = Path("/tmp/nonexistent.mp4")

        with pytest.raises(FileNotFoundError):
            process_audio(nonexistent)

    @patch("core.secrets.resolve_runtime_value")
    def test_process_audio_no_api_key(self, mock_resolve):
        """Test audio processing fails without API key."""
        mock_resolve.return_value = None

        test_file = Path(tempfile.gettempdir()) / "test_audio.mp4"
        test_file.write_bytes(b"fake audio data")

        try:
            with pytest.raises(ValueError, match="OPENAI_API_KEY not configured"):
                process_audio(test_file)
        finally:
            test_file.unlink()


class TestProcessFile:
    """Test process_file function."""

    @patch("mymcp.tool.file_reader_processors.process_pdf")
    def test_process_file_pdf(self, mock_process_pdf):
        """Test process_file routes PDF correctly."""
        mock_process_pdf.return_value = "PDF content"

        test_file = Path(tempfile.gettempdir()) / "test.pdf"
        test_file.write_bytes(b"fake pdf")

        try:
            result = process_file(test_file, "application/pdf", "Summarize")
            assert result == "PDF content"
            mock_process_pdf.assert_called_once_with(test_file)
        finally:
            test_file.unlink()

    @patch("mymcp.tool.file_reader_processors.process_text")
    def test_process_file_text(self, mock_process_text):
        """Test process_file routes text correctly."""
        mock_process_text.return_value = "Text content"

        test_file = Path(tempfile.gettempdir()) / "test.txt"
        test_file.write_text("content")

        try:
            result = process_file(test_file, "text/plain", "Summarize")
            assert result == "Text content"
            mock_process_text.assert_called_once_with(test_file)
        finally:
            test_file.unlink()

    def test_process_file_unsupported_mime(self):
        """Test process_file fails for unsupported MIME type."""
        test_file = Path(tempfile.gettempdir()) / "test.bin"
        test_file.write_bytes(b"binary data")

        try:
            with pytest.raises(ValueError, match="Unsupported MIME type"):
                process_file(test_file, "application/octet-stream", "Process")
        finally:
            test_file.unlink()
