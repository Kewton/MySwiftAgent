"""Tests for utility endpoints."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.api.v1.utility_endpoints import (
    get_overview_by_google_serper_api,
    google_search_by_serper_api,
    tts_and_upload_drive_api,
)
from app.schemas.utilitySchemas import SearchUtilityRequest, UtilityRequest


class TestTtsAndUploadDrive:
    """Test TTS and upload drive endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.utility_endpoints.send_email")
    @patch("app.api.v1.utility_endpoints.tts_and_upload_drive")
    @patch("app.api.v1.utility_endpoints.generate_subject_from_text")
    async def test_tts_and_upload_drive_success(self, mock_subject, mock_tts, mock_email):
        """Test successful TTS and upload."""
        mock_subject.return_value = "Test Title"
        mock_tts.return_value = "https://drive.google.com/file/123"
        mock_email.return_value = None
        request = UtilityRequest(user_input="Test text for TTS")

        result = await tts_and_upload_drive_api(request)

        assert result.result == "https://drive.google.com/file/123"
        mock_subject.assert_called_once_with("Test text for TTS", max_length=40)
        mock_tts.assert_called_once_with("Test text for TTS", "Test Title")
        mock_email.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.api.v1.utility_endpoints.generate_subject_from_text")
    async def test_tts_and_upload_drive_error(self, mock_subject):
        """Test TTS and upload error handling."""
        mock_subject.side_effect = Exception("Test error")
        request = UtilityRequest(user_input="Test text")

        with pytest.raises(HTTPException) as exc_info:
            await tts_and_upload_drive_api(request)

        assert exc_info.value.status_code == 500
        assert "internal server error" in exc_info.value.detail.lower()


class TestGoogleSearchBySerper:
    """Test Google search by Serper endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.utility_endpoints.google_search_by_serper_list")
    async def test_google_search_without_num(self, mock_search):
        """Test Google search without num parameter."""
        mock_search.return_value = "Search results"
        request = SearchUtilityRequest(queries=["test query", "another query"])

        result = await google_search_by_serper_api(request)

        assert result.result == "Search results"
        mock_search.assert_called_once_with(["test query", "another query"])

    @pytest.mark.asyncio
    @patch("app.api.v1.utility_endpoints.google_search_by_serper_list")
    async def test_google_search_with_num(self, mock_search):
        """Test Google search with num parameter."""
        mock_search.return_value = "Search results"
        request = SearchUtilityRequest(queries=["test query"], num=10)

        result = await google_search_by_serper_api(request)

        assert result.result == "Search results"
        mock_search.assert_called_once_with(["test query"], 10)

    @pytest.mark.asyncio
    @patch("app.api.v1.utility_endpoints.google_search_by_serper_list")
    async def test_google_search_error(self, mock_search):
        """Test Google search error handling."""
        mock_search.side_effect = Exception("Test error")
        request = SearchUtilityRequest(queries=["test query"])

        with pytest.raises(HTTPException) as exc_info:
            await google_search_by_serper_api(request)

        assert exc_info.value.status_code == 500
        assert "internal server error" in exc_info.value.detail.lower()


class TestGetOverviewByGoogleSerper:
    """Test Get overview by Google Serper endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.utility_endpoints.get_overview_by_google_serper")
    async def test_overview_without_num(self, mock_overview):
        """Test overview without num parameter."""
        mock_overview.return_value = "Overview results"
        request = SearchUtilityRequest(queries=["test query"])

        result = await get_overview_by_google_serper_api(request)

        assert result.result == "Overview results"
        mock_overview.assert_called_once_with(["test query"])

    @pytest.mark.asyncio
    @patch("app.api.v1.utility_endpoints.get_overview_by_google_serper")
    async def test_overview_with_num(self, mock_overview):
        """Test overview with num parameter."""
        mock_overview.return_value = "Overview results"
        request = SearchUtilityRequest(queries=["test query"], num=5)

        result = await get_overview_by_google_serper_api(request)

        assert result.result == "Overview results"
        mock_overview.assert_called_once_with(["test query"], 5)

    @pytest.mark.asyncio
    @patch("app.api.v1.utility_endpoints.get_overview_by_google_serper")
    async def test_overview_error(self, mock_overview):
        """Test overview error handling."""
        mock_overview.side_effect = Exception("Test error")
        request = SearchUtilityRequest(queries=["test query"])

        with pytest.raises(HTTPException) as exc_info:
            await get_overview_by_google_serper_api(request)

        assert exc_info.value.status_code == 500
        assert "internal server error" in exc_info.value.detail.lower()
