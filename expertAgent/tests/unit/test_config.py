"""Tests for core.config module."""

from core.config import settings


class TestSettings:
    """Test Settings configuration."""

    def test_settings_has_required_fields(self):
        """Test that settings has all required fields."""
        assert hasattr(settings, "OPENAI_API_KEY")
        assert hasattr(settings, "GOOGLE_API_KEY")
        assert hasattr(settings, "ANTHROPIC_API_KEY")
        assert hasattr(settings, "LOG_DIR")
        assert hasattr(settings, "LOG_LEVEL")

    def test_log_level_default(self):
        """Test LOG_LEVEL has default value."""
        assert settings.LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR"]

    def test_ollama_url_default(self):
        """Test OLLAMA_URL has default value."""
        assert settings.OLLAMA_URL.startswith("http")

    def test_podcast_model_default(self):
        """Test PODCAST_SCRIPT_DEFAULT_MODEL has value."""
        assert settings.PODCAST_SCRIPT_DEFAULT_MODEL
