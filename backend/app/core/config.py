import uuid
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Field() без дефолтного значения, но с указанием, что оно берется из env
    DATABASE_URL: str = Field(default=...)
    SUPERADMIN_PASSWORD: str = Field(default=...)
    SUPERADMIN_TENANT_ID: uuid.UUID = Field(default=...)
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# Теперь Pylance понимает, что Pydantic берет инициализацию на себя,
# и ошибка reportCallIssue исчезнет.
settings = Settings()