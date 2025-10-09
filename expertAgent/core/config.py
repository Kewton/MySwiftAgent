from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings  # pydantic_settingsからインポート

load_dotenv()


class Settings(BaseSettings):
    OPENAI_API_KEY: str = Field(default="")
    GOOGLE_API_KEY: str = Field(default="")
    ANTHROPIC_API_KEY: str = Field(default="")
    LOG_DIR: str = Field(default="./")
    LOG_LEVEL: str = Field(default="INFO")
    GRAPH_AGENT_MODEL: str = Field(default="gemini-2.0-flash-exp")
    GOOGLE_APIS_TOKEN_PATH: str = Field(default="./token/token.json")
    GOOGLE_APIS_CREDENTIALS_PATH: str = Field(default="./token/credentials.json")
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
    MYVAULT_BASE_URL: str = Field(default="http://localhost:8000")
    MYVAULT_SERVICE_NAME: str = Field(default="expertagent-service")
    MYVAULT_SERVICE_TOKEN: str = Field(default="")
    MYVAULT_DEFAULT_PROJECT: str = Field(
        default=""
    )  # Optional override for default project
    SECRETS_CACHE_TTL: int = Field(default=300)  # 5 minutes cache TTL

    # Admin Configuration
    ADMIN_TOKEN: str = Field(default="")  # For reload secrets endpoint


# インスタンス生成
settings = Settings()
