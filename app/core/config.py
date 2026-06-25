from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/filestorage"

    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    ADMIN_EMAIL: str = "admin@gmail.com"

    STORAGE_ROOT_PATH: str = "./storage"
    UPLOAD_CHUNK_SIZE: int = 1024 * 1024

    DEFAULT_MAX_FILE_SIZE: int = 100 * 1024 * 1024
    DEFAULT_MAX_STORAGE_SIZE: int = 1024 * 1024 * 1024

    CLEANUP_RETENTION_DAYS: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
