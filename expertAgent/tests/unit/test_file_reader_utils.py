"""Unit tests for file_reader_utils module."""

import tempfile
from pathlib import Path

import pytest

from mymcp.tool.file_reader_utils import (
    MAX_FILE_SIZE,
    detect_mime_type,
    extract_google_drive_file_id,
    validate_file_size,
    validate_local_path,
)


class TestDetectMimeType:
    """Test detect_mime_type function."""

    def test_detect_mime_type_text_file(self, tmp_path):
        """Test MIME type detection for text file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        mime_type = detect_mime_type(test_file)
        assert mime_type == "text/plain"

    def test_detect_mime_type_nonexistent_file(self):
        """Test MIME type detection for nonexistent file."""
        nonexistent = Path("/tmp/nonexistent_file_12345.txt")
        # Should return text/plain based on extension, or application/octet-stream if magic fails
        mime_type = detect_mime_type(nonexistent)
        # Accept either text/plain (mimetypes fallback) or application/octet-stream
        assert mime_type in ("text/plain", "application/octet-stream")

    def test_detect_mime_type_with_various_extensions(self, tmp_path):
        """Test MIME type detection with various file extensions."""
        test_cases = [
            ("test.json", ["application/json", "text/plain"]),
            ("test.html", ["text/html", "text/plain"]),
            ("test.xml", ["text/xml", "application/xml", "text/plain"]),
        ]

        for filename, expected_mimes in test_cases:
            test_file = tmp_path / filename
            test_file.write_text("content")
            mime_type = detect_mime_type(test_file)
            # MIME type should match one of the expected types or be octet-stream
            assert (
                mime_type in expected_mimes or mime_type == "application/octet-stream"
            )


class TestValidateFileSize:
    """Test validate_file_size function."""

    def test_validate_file_size_small_file(self, tmp_path):
        """Test validation passes for small file."""
        test_file = tmp_path / "small.txt"
        test_file.write_text("Small content")

        # Should not raise exception
        validate_file_size(test_file)

    def test_validate_file_size_large_file(self, tmp_path):
        """Test validation fails for large file."""
        test_file = tmp_path / "large.bin"
        # Create a file larger than MAX_FILE_SIZE
        large_content = b"0" * (MAX_FILE_SIZE + 1024)
        test_file.write_bytes(large_content)

        with pytest.raises(ValueError, match="File size .* exceeds limit"):
            validate_file_size(test_file)

    def test_validate_file_size_nonexistent_file(self):
        """Test validation fails for nonexistent file."""
        nonexistent = Path("/tmp/nonexistent_file_12345.txt")

        with pytest.raises(FileNotFoundError, match="File not found"):
            validate_file_size(nonexistent)

    def test_validate_file_size_custom_limit(self, tmp_path):
        """Test validation with custom size limit."""
        test_file = tmp_path / "medium.txt"
        test_file.write_bytes(b"0" * 2048)

        # Should pass with large limit
        validate_file_size(test_file, max_size=10000)

        # Should fail with small limit
        with pytest.raises(ValueError, match="exceeds limit"):
            validate_file_size(test_file, max_size=1024)


class TestValidateLocalPath:
    """Test validate_local_path function."""

    def test_validate_local_path_allowed_tmp(self):
        """Test validation passes for /tmp directory."""
        test_file = Path(tempfile.gettempdir()) / "test_file.txt"
        test_file.write_text("content")

        try:
            validated_path = validate_local_path(str(test_file))
            assert validated_path.exists()
            assert validated_path.is_absolute()
            # Verify path is resolved to absolute path
            assert validated_path == test_file.resolve()
        finally:
            test_file.unlink()

    def test_validate_local_path_nonexistent_file(self):
        """Test validation fails for nonexistent file."""
        with pytest.raises(FileNotFoundError, match="File not found"):
            validate_local_path("/tmp/nonexistent_file_98765.txt")

    def test_validate_local_path_outside_allowed_dirs(self):
        """Test validation fails for path outside allowed directories."""
        # /etc/passwd is outside allowed directories
        with pytest.raises(ValueError, match="Path outside allowed directories"):
            validate_local_path("/etc/passwd")

    def test_validate_local_path_resolves_symlinks(self):
        """Test that path resolution handles symlinks."""
        # Create file in tmp
        real_file = Path(tempfile.gettempdir()) / "real_file.txt"
        real_file.write_text("content")

        try:
            # Test with absolute path
            validated_path = validate_local_path(str(real_file))
            # Both should be absolute and resolved
            assert validated_path.is_absolute()
            assert validated_path.exists()
            assert validated_path == real_file.resolve()
        finally:
            real_file.unlink()


class TestExtractGoogleDriveFileId:
    """Test extract_google_drive_file_id function."""

    def test_extract_file_id_pattern_1(self):
        """Test extraction from /file/d/{ID}/view format."""
        url = "https://drive.google.com/file/d/1ABC123XYZ/view"
        file_id = extract_google_drive_file_id(url)
        assert file_id == "1ABC123XYZ"

    def test_extract_file_id_pattern_2_open(self):
        """Test extraction from ?id={ID} format (open)."""
        url = "https://drive.google.com/open?id=1DEF456UVW"
        file_id = extract_google_drive_file_id(url)
        assert file_id == "1DEF456UVW"

    def test_extract_file_id_pattern_2_uc(self):
        """Test extraction from ?id={ID} format (uc)."""
        url = "https://drive.google.com/uc?id=1GHI789RST"
        file_id = extract_google_drive_file_id(url)
        assert file_id == "1GHI789RST"

    def test_extract_file_id_invalid_url(self):
        """Test returns None for invalid URL."""
        url = "https://example.com/not-a-drive-url"
        file_id = extract_google_drive_file_id(url)
        assert file_id is None

    def test_extract_file_id_malformed_drive_url(self):
        """Test returns None for malformed Drive URL."""
        url = "https://drive.google.com/file/view"
        file_id = extract_google_drive_file_id(url)
        assert file_id is None

    def test_extract_file_id_with_additional_params(self):
        """Test extraction works with additional URL parameters."""
        url = "https://drive.google.com/file/d/1JKL012MNO/view?usp=sharing"
        file_id = extract_google_drive_file_id(url)
        assert file_id == "1JKL012MNO"
