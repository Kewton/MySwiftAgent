from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings  # pydantic_settingsからインポート

load_dotenv()


class Settings(BaseSettings):
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")
    GOOGLE_API_KEY: str = Field(default="", env="GOOGLE_API_KEY")
    ANTHROPIC_API_KEY: str = Field(default="", env="ANTHROPIC_API_KEY")
    LOG_DIR: str = Field(default="./", env="LOG_DIR")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    GRAPH_AGENT_MODEL: str = Field(
        default="gemini-2.0-flash-exp", env="GRAPH_AGENT_MODEL"
    )
    GOOGLE_APIS_TOKEN_PATH: str = Field(
        default="./token/token.json", env="GOOGLE_APIS_TOKEN_PATH"
    )
    GOOGLE_APIS_CREDENTIALS_PATH: str = Field(
        default="./token/credentials.json", env="GOOGLE_APIS_CREDENTIALS_PATH"
    )
    PODCAST_SCRIPT_DEFAULT_MODEL: str = Field(
        default="gpt-4o-mini", env="PODCAST_SCRIPT_DEFAULT_MODEL"
    )
    MAIL_TO: str = Field(default="", env="MAIL_TO")
    SPREADSHEET_ID: str = Field(default="", env="SPREADSHEET_ID")
    OLLAMA_URL: str = Field(default="http://localhost:11434", env="OLLAMA_URL")
    OLLAMA_DEF_SMALL_MODEL: str = Field(
        default="gemma3:27b-it-q8_0", env="OLLAMA_DEF_SMALL_MODEL"
    )
    EXTRACT_KNOWLEDGE_MODEL: str = Field(
        default="gemma3:27b-it-q8_0", env="EXTRACT_KNOWLEDGE_MODEL"
    )
    SERPER_API_KEY: str = Field(default="", env="SERPER_API_KEY")
    MLX_LLM_SERVER_URL: str = Field(
        default="http://localhost:8080", env="MLX_LLM_SERVER_URL"
    )

    # MyVault Configuration
    MYVAULT_ENABLED: bool = Field(default=False, env="MYVAULT_ENABLED")
    MYVAULT_BASE_URL: str = Field(
        default="http://localhost:8000", env="MYVAULT_BASE_URL"
    )
    MYVAULT_SERVICE_NAME: str = Field(
        default="expertagent-service", env="MYVAULT_SERVICE_NAME"
    )
    MYVAULT_SERVICE_TOKEN: str = Field(default="", env="MYVAULT_SERVICE_TOKEN")
    MYVAULT_DEFAULT_PROJECT: str = Field(
        default="", env="MYVAULT_DEFAULT_PROJECT"
    )  # Optional override for default project
    SECRETS_CACHE_TTL: int = Field(
        default=300, env="SECRETS_CACHE_TTL"
    )  # 5 minutes cache TTL

    # Admin Configuration
    ADMIN_TOKEN: str = Field(
        default="", env="ADMIN_TOKEN"
    )  # For reload secrets endpoint


# インスタンス生成
settings = Settings()
