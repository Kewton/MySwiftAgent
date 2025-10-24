from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings  # pydantic_settingsからインポート

# Load environment variables from expertAgent/.env (new policy)
# Note: override=False respects existing environment variables set by quick-start.sh or docker-compose
PROJECT_ROOT = Path(__file__).parent.parent
env_path = PROJECT_ROOT / ".env"

if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
else:
    # Fallback to auto-detection (for docker-compose where env vars are pre-set)
    load_dotenv(override=False)


class Settings(BaseSettings):
    OPENAI_API_KEY: str = Field(default="")
    GOOGLE_API_KEY: str = Field(default="")
    ANTHROPIC_API_KEY: str = Field(default="")
    LOG_DIR: str = Field(default="./")
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


# インスタンス生成
settings = Settings()
