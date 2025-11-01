from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with .env.local override support for git worktree parallel development."""

    OPENAI_API_KEY: str = Field(default="")
    GOOGLE_API_KEY: str = Field(default="")
    ANTHROPIC_API_KEY: str = Field(default="")
    LOG_DIR: str = Field(default="./logs")
    LOG_LEVEL: str = Field(default="INFO")
    GRAPH_AGENT_MODEL: str = Field(default="gemini-2.0-flash-exp")
    PODCAST_SCRIPT_DEFAULT_MODEL: str = Field(default="gpt-4o-mini")
    MAIL_TO: str = Field(default="")
    SPREADSHEET_ID: str = Field(default="")
    OLLAMA_URL: str = Field(default="http://localhost:11434")
    OLLAMA_DEF_SMALL_MODEL: str = Field(default="gemma3:27b-it-q8_0")
    EXTRACT_KNOWLEDGE_MODEL: str = Field(default="gemma3:27b-it-q8_0")
    SERPER_API_KEY: str = Field(default="")
    MLX_LLM_SERVER_URL: str = Field(default="http://localhost:8080")

    # MyVault Configuration
    MYVAULT_ENABLED: bool = Field(default=False)
    MYVAULT_BASE_URL: str = Field(default="http://localhost:8103")
    MYVAULT_SERVICE_NAME: str = Field(default="expertagent")
    MYVAULT_SERVICE_TOKEN: str = Field(default="")
    MYVAULT_DEFAULT_PROJECT: str = Field(
        default=""
    )  # Optional override for default project
    SECRETS_CACHE_TTL: int = Field(default=300)  # 5 minutes cache TTL

    # ExpertAgent Base URL (for Job/Task Generator)
    EXPERTAGENT_BASE_URL: str = Field(default="http://localhost:8104")

    # Google APIs Configuration
    GOOGLE_APIS_DEFAULT_PROJECT: str = Field(
        default="default_project"
    )  # Default project for Google APIs (gmail, drive, sheets)

    # Admin Configuration
    ADMIN_TOKEN: str = Field(default="")  # For reload secrets endpoint

    # Job/Task Generator Configuration (Issue #111)
    JOB_GENERATOR_MAX_TOKENS: int = Field(default=32768)
    JOB_GENERATOR_REQUIREMENT_ANALYSIS_MODEL: str = Field(default="claude-haiku-4-5")
    JOB_GENERATOR_EVALUATOR_MODEL: str = Field(default="claude-haiku-4-5")
    JOB_GENERATOR_INTERFACE_DEFINITION_MODEL: str = Field(default="claude-haiku-4-5")
    JOB_GENERATOR_VALIDATION_MODEL: str = Field(default="claude-haiku-4-5")

    class Config:
        """Pydantic settings configuration for git worktree support.

        Environment variable loading order (later takes precedence):
        1. System environment variables (set by quick-start.sh, docker-compose, etc.)
        2. .env file (shared settings: API keys, DB connections)
        3. .env.local file (worktree-specific settings: port numbers, log directories)

        Note: env_file_encoding ensures UTF-8 for cross-platform compatibility
        """

        env_file = [".env", ".env.local"]  # .env.local takes precedence
        env_file_encoding = "utf-8"
        case_sensitive = False


# インスタンス生成
settings = Settings()
