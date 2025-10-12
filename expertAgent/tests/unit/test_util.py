"""Unit tests for aiagent.langgraph.util module."""

from aiagent.langgraph.util import (
    isChatGPT_o,
    isChatGptAPI,
    isChatGPTImageAPI,
    isClaude,
    isGemini,
)


class TestIsChatGptAPI:
    """Tests for isChatGptAPI function."""

    def test_gpt_oss_models_return_false(self):
        """Test that gpt-oss models are not recognized as OpenAI models."""
        assert isChatGptAPI("gpt-oss:20b") is False
        assert isChatGptAPI("gpt-oss:120b") is False
        assert isChatGptAPI("gpt-oss") is False

    def test_openai_models_return_true(self):
        """Test that OpenAI official models are correctly recognized."""
        assert isChatGptAPI("gpt-4o-mini") is True
        assert isChatGptAPI("gpt-4o") is True
        assert isChatGptAPI("gpt-4") is True
        assert isChatGptAPI("gpt-3.5-turbo") is True
        assert isChatGptAPI("gpt-4-turbo") is True

    def test_non_gpt_models_return_false(self):
        """Test that non-GPT models return False."""
        assert isChatGptAPI("gemini-2.5-flash") is False
        assert isChatGptAPI("claude-3-opus") is False
        assert isChatGptAPI("llama3:8b") is False
        assert isChatGptAPI("qwen3:32b") is False


class TestIsChatGPT_o:
    """Tests for isChatGPT_o function."""

    def test_o_series_models_return_true(self):
        """Test that o1 and o3 models are recognized."""
        assert isChatGPT_o("o1-preview") is True
        assert isChatGPT_o("o1-mini") is True
        assert isChatGPT_o("o3-mini") is True

    def test_non_o_models_return_false(self):
        """Test that non-o models return False."""
        assert isChatGPT_o("gpt-4o") is False
        assert isChatGPT_o("gpt-4o-mini") is False
        assert isChatGPT_o("gpt-4") is False


class TestIsGemini:
    """Tests for isGemini function."""

    def test_gemini_models_return_true(self):
        """Test that Gemini models are recognized."""
        assert isGemini("gemini-2.5-flash") is True
        assert isGemini("gemini-pro") is True
        assert isGemini("gemini-1.5-pro") is True

    def test_non_gemini_models_return_false(self):
        """Test that non-Gemini models return False."""
        assert isGemini("gpt-4o") is False
        assert isGemini("claude-3-opus") is False


class TestIsClaude:
    """Tests for isClaude function."""

    def test_claude_models_return_true(self):
        """Test that Claude models are recognized."""
        assert isClaude("claude-3-opus") is True
        assert isClaude("claude-3-sonnet") is True
        assert isClaude("claude-2") is True

    def test_non_claude_models_return_false(self):
        """Test that non-Claude models return False."""
        assert isClaude("gpt-4o") is False
        assert isClaude("gemini-2.5-flash") is False


class TestIsChatGPTImageAPI:
    """Tests for isChatGPTImageAPI function."""

    def test_image_capable_models_return_true(self):
        """Test that image-capable models are recognized."""
        assert isChatGPTImageAPI("gpt-4o") is True
        assert isChatGPTImageAPI("gpt-4o-mini") is True
        assert isChatGPTImageAPI("o1-preview") is True
        assert isChatGPTImageAPI("o3-mini") is True

    def test_non_image_models_return_false(self):
        """Test that non-image models return False."""
        assert isChatGPTImageAPI("gpt-4") is False
        assert isChatGPTImageAPI("gpt-3.5-turbo") is False
        assert isChatGPTImageAPI("gemini-2.5-flash") is False
