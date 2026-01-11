from pydantic import AliasChoices, Field
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
    # Default: 8004 for local development (--local-only mode)
    # Override via environment variable for Docker (8104) or other setups
    EXPERTAGENT_BASE_URL: str = Field(default="http://localhost:8004")

    # Google APIs Configuration
    GOOGLE_APIS_DEFAULT_PROJECT: str = Field(
        default="default_project"
    )  # Default project for Google APIs (gmail, drive, sheets)

    # Admin Configuration
    # Uses EXPERTAGENT_ADMIN_TOKEN preferentially to avoid conflicts with other services
    ADMIN_TOKEN: str = Field(
        default="",
        validation_alias=AliasChoices("EXPERTAGENT_ADMIN_TOKEN", "ADMIN_TOKEN"),
    )

    # Job/Task Generator Configuration (Issue #111)
    JOB_GENERATOR_MAX_TOKENS: int = Field(default=32768)
    JOB_GENERATOR_REQUIREMENT_ANALYSIS_MODEL: str = Field(default="claude-haiku-4-5")
    JOB_GENERATOR_EVALUATOR_MODEL: str = Field(default="claude-haiku-4-5")
    JOB_GENERATOR_INTERFACE_DEFINITION_MODEL: str = Field(default="claude-haiku-4-5")
    JOB_GENERATOR_VALIDATION_MODEL: str = Field(default="claude-haiku-4-5")

    # Workflow Generator Configuration (Issue #110)
    # Issue #338: Changed to gemini-3-pro-preview for better workflow quality and rule compliance
    WORKFLOW_GENERATOR_MODEL: str = Field(default="gemini-3-pro-preview")
    WORKFLOW_GENERATOR_MAX_TOKENS: int = Field(default=16384)

    # LLM Evaluator Configuration (Issue #305)
    LLM_EVALUATOR_ENABLED: bool = Field(default=True)
    LLM_EVALUATOR_MODEL: str = Field(default="gpt-4o-mini")
    LLM_EVALUATOR_THRESHOLD: int = Field(default=70)
    LLM_EVALUATOR_TIMEOUT: int = Field(default=30)

    # Test Data Regenerator Configuration (Issue #305)
    TEST_DATA_QUALITY_THRESHOLD: int = Field(default=50)
    MAX_TEST_DATA_REGENERATION: int = Field(default=2)
    TEST_DATA_REGENERATOR_MODEL: str = Field(default="gpt-4o-mini")

    # Result Summary Configuration (Issue #305)
    RESULT_SUMMARY_ENABLED: bool = Field(default=True)
    RESULT_SUMMARY_FORMAT: str = Field(default="markdown")  # markdown or json

    # Langfuse Observability Configuration (Issue #113)
    LANGFUSE_PUBLIC_KEY: str = Field(default="")
    LANGFUSE_SECRET_KEY: str = Field(default="")
    LANGFUSE_HOST: str = Field(default="http://localhost:3001")

    # Valkey Configuration (Issue #169)
    CONVERSATION_STORE_TYPE: str = Field(default="memory")  # 'memory' or 'valkey'
    VALKEY_ENABLED: bool = Field(default=False)  # Enable Valkey persistence
    VALKEY_URL: str = Field(default="redis://localhost:6379")  # Redis-compatible URL
    VALKEY_HOST: str = Field(default="localhost")
    VALKEY_PORT: int = Field(default=6379)
    VALKEY_DB: int = Field(default=0)
    VALKEY_TTL: int = Field(default=86400)  # 24 hours in seconds

    # JobQueue API Configuration
    JOBQUEUE_API_URL: str = Field(default="http://localhost:8001")

    # Job Generator V2 Feature Flag (Issue #342)
    USE_JOB_GENERATOR_V2: bool = Field(
        default=False,
        description="Enable new Job Generator V2 architecture with improved retry management"
    )

    # Workflow Generator V2 Configuration (Issue #342 Phase F)
    WORKFLOW_GENERATOR_V2_MODEL: str = Field(
        default="gemini-3-flash-preview",
        description="LLM model for V2 workflow generation"
    )
    WORKFLOW_GENERATOR_V2_TEMPERATURE: float = Field(
        default=0.3,
        description="Sampling temperature for V2 workflow generation"
    )
    WORKFLOW_GENERATOR_V2_MAX_RETRY: int = Field(
        default=2,
        description="Maximum retry count for V2 workflow generation"
    )
    WORKFLOW_GENERATOR_V2_ENABLE_EXECUTION_TEST: bool = Field(
        default=False,
        description="Enable execution testing of generated workflows"
    )

    # GraphAI Server Configuration
    # Default: 8005 for local development
    # Override via environment variable for Docker (graphaiserver:8000)
    GRAPHAISERVER_BASE_URL: str = Field(default="http://localhost:8005")
    # Admin token for GraphAI Server workflow registration (Issue #350)
    GRAPHAISERVER_ADMIN_TOKEN: str = Field(default="")

    # Server Configuration
    HOST: str = Field(default="0.0.0.0")  # noqa: S104  # Development default, override via .env for production
    PORT: int = Field(default=8000)

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
        extra = (
            "ignore"  # Ignore extra fields from .env (e.g., Langfuse service config)
        )


# インスタンス生成
settings = Settings()
