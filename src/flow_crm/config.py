from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://flowcrm:flowcrm_dev_password@localhost:5432/flowcrm"
    app_env: str = "development"
    secret_key: str = "change-this-secret-key-before-production"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
