"""Unit tests for multi-candidate suggestion schemas.

Tests schema validation for RequirementCandidate, CandidateSelectionEvent,
and CandidateSelectRequest models.
"""

import pytest
from pydantic import ValidationError

from app.schemas.chat import (
    CandidateSelectRequest,
    CandidateSelectionEvent,
    RequirementCandidate,
)


class TestRequirementCandidate:
    """Test suite for RequirementCandidate schema."""

    def test_valid_candidate_a(self):
        """Test valid candidate A creation."""
        candidate = RequirementCandidate(
            candidate_id="A",
            title="売上分析",
            data_source="CSVファイル",
            process_description="売上データを月別に集計・分析",
            output_format="Excelレポート",
            schedule="毎日実行",
            confidence=0.85,
        )
        assert candidate.candidate_id == "A"
        assert candidate.title == "売上分析"
        assert candidate.confidence == 0.85

    def test_valid_candidate_b(self):
        """Test valid candidate B creation."""
        candidate = RequirementCandidate(
            candidate_id="B",
            title="詳細レポート",
            data_source="データベース",
            process_description="売上データの詳細分析とトレンド予測",
            output_format="PDFレポート",
            schedule="毎週実行",
            confidence=0.75,
        )
        assert candidate.candidate_id == "B"
        assert candidate.title == "詳細レポート"
        assert candidate.confidence == 0.75

    def test_invalid_candidate_id(self):
        """Test validation error for invalid candidate_id."""
        with pytest.raises(ValidationError) as exc_info:
            RequirementCandidate(
                candidate_id="C",  # Invalid - only A or B allowed
                title="テスト",
                data_source="CSV",
                process_description="テスト処理",
                output_format="Excel",
                schedule="毎日",
                confidence=0.8,
            )
        assert "candidate_id" in str(exc_info.value)

    def test_confidence_range_valid_min(self):
        """Test confidence at minimum valid value (0.0)."""
        candidate = RequirementCandidate(
            candidate_id="A",
            title="テスト",
            data_source="CSV",
            process_description="テスト処理",
            output_format="Excel",
            schedule="毎日",
            confidence=0.0,
        )
        assert candidate.confidence == 0.0

    def test_confidence_range_valid_max(self):
        """Test confidence at maximum valid value (1.0)."""
        candidate = RequirementCandidate(
            candidate_id="A",
            title="テスト",
            data_source="CSV",
            process_description="テスト処理",
            output_format="Excel",
            schedule="毎日",
            confidence=1.0,
        )
        assert candidate.confidence == 1.0

    def test_confidence_range_invalid_negative(self):
        """Test validation error for negative confidence."""
        with pytest.raises(ValidationError) as exc_info:
            RequirementCandidate(
                candidate_id="A",
                title="テスト",
                data_source="CSV",
                process_description="テスト処理",
                output_format="Excel",
                schedule="毎日",
                confidence=-0.1,
            )
        assert "confidence" in str(exc_info.value)

    def test_confidence_range_invalid_over_one(self):
        """Test validation error for confidence > 1.0."""
        with pytest.raises(ValidationError) as exc_info:
            RequirementCandidate(
                candidate_id="A",
                title="テスト",
                data_source="CSV",
                process_description="テスト処理",
                output_format="Excel",
                schedule="毎日",
                confidence=1.1,
            )
        assert "confidence" in str(exc_info.value)

    def test_missing_required_fields(self):
        """Test validation error for missing required fields."""
        with pytest.raises(ValidationError):
            RequirementCandidate(
                candidate_id="A",
                # Missing all other required fields
            )

    def test_model_dump(self):
        """Test model serialization."""
        candidate = RequirementCandidate(
            candidate_id="A",
            title="テスト",
            data_source="CSV",
            process_description="テスト処理",
            output_format="Excel",
            schedule="毎日",
            confidence=0.8,
        )
        data = candidate.model_dump()
        assert data["candidate_id"] == "A"
        assert data["confidence"] == 0.8
        assert isinstance(data, dict)


class TestCandidateSelectionEvent:
    """Test suite for CandidateSelectionEvent schema."""

    def test_valid_event_with_two_candidates(self):
        """Test valid event with two candidates."""
        candidate_a = RequirementCandidate(
            candidate_id="A",
            title="簡易分析",
            data_source="CSV",
            process_description="基本的な集計",
            output_format="Excel",
            schedule="オンデマンド",
            confidence=0.9,
        )
        candidate_b = RequirementCandidate(
            candidate_id="B",
            title="詳細分析",
            data_source="データベース",
            process_description="詳細なトレンド分析",
            output_format="PDF",
            schedule="毎日",
            confidence=0.8,
        )
        event = CandidateSelectionEvent(
            candidates=[candidate_a, candidate_b],
            prompt_for_selection="どちらの解釈がお望みに近いですか？",
        )
        assert len(event.candidates) == 2
        assert event.candidates[0].candidate_id == "A"
        assert event.candidates[1].candidate_id == "B"
        assert "どちら" in event.prompt_for_selection

    def test_event_requires_at_least_one_candidate(self):
        """Test that event requires at least one candidate."""
        with pytest.raises(ValidationError) as exc_info:
            CandidateSelectionEvent(
                candidates=[],
                prompt_for_selection="候補を選んでください",
            )
        assert "candidates" in str(exc_info.value)

    def test_event_allows_single_candidate(self):
        """Test that event allows single candidate (fallback scenario)."""
        candidate = RequirementCandidate(
            candidate_id="A",
            title="唯一の候補",
            data_source="CSV",
            process_description="処理内容",
            output_format="Excel",
            schedule="毎日",
            confidence=0.95,
        )
        event = CandidateSelectionEvent(
            candidates=[candidate],
            prompt_for_selection="この解釈でよろしいですか？",
        )
        assert len(event.candidates) == 1

    def test_event_model_dump(self):
        """Test event serialization."""
        candidate = RequirementCandidate(
            candidate_id="A",
            title="テスト",
            data_source="CSV",
            process_description="処理",
            output_format="Excel",
            schedule="毎日",
            confidence=0.8,
        )
        event = CandidateSelectionEvent(
            candidates=[candidate],
            prompt_for_selection="選んでください",
        )
        data = event.model_dump()
        assert "candidates" in data
        assert "prompt_for_selection" in data
        assert len(data["candidates"]) == 1


class TestCandidateSelectRequest:
    """Test suite for CandidateSelectRequest schema."""

    def test_valid_select_request_a(self):
        """Test valid select request for candidate A."""
        request = CandidateSelectRequest(
            conversation_id="conv_123",
            selected_candidate_id="A",
        )
        assert request.conversation_id == "conv_123"
        assert request.selected_candidate_id == "A"

    def test_valid_select_request_b(self):
        """Test valid select request for candidate B."""
        request = CandidateSelectRequest(
            conversation_id="conv_456",
            selected_candidate_id="B",
        )
        assert request.selected_candidate_id == "B"

    def test_invalid_selected_candidate_id(self):
        """Test validation error for invalid selected_candidate_id."""
        with pytest.raises(ValidationError) as exc_info:
            CandidateSelectRequest(
                conversation_id="conv_123",
                selected_candidate_id="C",  # Invalid
            )
        assert "selected_candidate_id" in str(exc_info.value)

    def test_missing_conversation_id(self):
        """Test validation error for missing conversation_id."""
        with pytest.raises(ValidationError):
            CandidateSelectRequest(
                selected_candidate_id="A",
            )

    def test_missing_selected_candidate_id(self):
        """Test validation error for missing selected_candidate_id."""
        with pytest.raises(ValidationError):
            CandidateSelectRequest(
                conversation_id="conv_123",
            )

    def test_empty_conversation_id(self):
        """Test that empty conversation_id is allowed (validation is minimal)."""
        # Pydantic allows empty strings by default unless constrained
        request = CandidateSelectRequest(
            conversation_id="",
            selected_candidate_id="A",
        )
        assert request.conversation_id == ""

    def test_model_dump(self):
        """Test request serialization."""
        request = CandidateSelectRequest(
            conversation_id="conv_123",
            selected_candidate_id="A",
        )
        data = request.model_dump()
        assert data["conversation_id"] == "conv_123"
        assert data["selected_candidate_id"] == "A"
