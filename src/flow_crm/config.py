from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://flowcrm:flowcrm_dev_password@localhost:5432/flowcrm"
    app_env: str = "development"
    secret_key: str = "change-this-secret-key-before-production"
    backup_dir: str = "backups"
    backup_enabled: bool = True
    backup_schedule_hour: int = 2
    backup_schedule_minute: int = 0
    backup_retention_days: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
