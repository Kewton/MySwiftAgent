from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings  # pydantic_settingsからインポート

load_dotenv()


class Settings(BaseSettings):
    OPENAI_API_KEY: str = Field(default="OPENAI_API_KEY", env="OPENAI_API_KEY")
    GOOGLE_API_KEY: str = Field(default="GOOGLE_API_KEY", env="GOOGLE_API_KEY")
    ANTHROPIC_API_KEY: str = Field(default="ANTHROPIC_API_KEY", env="ANTHROPIC_API_KEY")
    LOG_DIR: str = Field(default="./", env="LOG_DIR")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    GRAPH_AGENT_MODEL: str = Field(default="GRAPH_AGENT_MODEL", env="GRAPH_AGENT_MODEL")
    GOOGLE_APIS_TOKEN_PATH: str = Field(
        default="GOOGLE_APIS_TOKEN_PATH", env="GOOGLE_APIS_TOKEN_PATH"
    )
    GOOGLE_APIS_CREDENTIALS_PATH: str = Field(
        default="GOOGLE_APIS_CREDENTIALS_PATH", env="GOOGLE_APIS_CREDENTIALS_PATH"
    )
    PODCAST_SCRIPT_DEFAULT_MODEL: str = Field(
        default="gpt-4o-mini", env="PODCAST_SCRIPT_DEFAULT_MODEL"
    )
    MAIL_TO: str = Field(default="MAIL_TO", env="MAIL_TO")
    SPREADSHEET_ID: str = Field(default="SPREADSHEET_ID", env="SPREADSHEET_ID")
    OLLAMA_URL: str = Field(default="http://localhost:11434", env="OLLAMA_URL")
    OLLAMA_DEF_SMALL_MODEL: str = Field(
        default="gemma3:27b-it-qat", env="OLLAMA_DEF_SMALL_MODEL"
    )
    EXTRACT_KNOWLEDGE_MODEL: str = Field(
        default="gemma3:27b-it-qat", env="EXTRACT_KNOWLEDGE_MODEL"
    )
    SERPER_API_KEY: str = Field(default="SERPER_API_KEY", env="SERPER_API_KEY")
    MLX_LLM_SERVER_URL: str = Field(
        default="http://localhost:8080", env="MLX_LLM_SERVER_URL"
    )


# インスタンス生成
settings = Settings()
