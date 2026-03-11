from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Minka API"
    ENVIRONMENT: str = "local"
    DEBUG: bool = True

    DATABASE_URL: str
    SECRET_KEY: str

    OPENAI_API_KEY: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
