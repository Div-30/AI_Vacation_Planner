from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    llm_provider: str = "google_genai"
    llm_model: str = "gemini-3.5-flash-lite"
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()