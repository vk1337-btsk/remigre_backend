from pathlib import Path

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    """Базовый класс для конфигурации переменных окружения проекта."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    is_debug: bool = Field(alias="IS_DEBUG", title="Флаг дебага (влияет на логирование)")
    is_project: bool = Field(alias="IS_PROJECT", title="Флаг проекта (влияет на настройки запуска локально/на сервере)")

    @model_validator(mode="before")
    def set_project_or_develop_config(cls, values) -> dict:
        """Определяет переменный окружения для проекта в зависимости от DEBUG, удаляет лишние переменные."""

        is_project = values.get("IS_PROJECT", "") == "True"
        prefix_save = "project_" if is_project else "develop_"
        prefix_drop = "develop_" if is_project else "project_"

        updated_values = {
            key.replace(prefix_save, "").upper() if key.startswith(prefix_save) else key: value
            for key, value in values.items()
            if not key.startswith(prefix_drop)
        }
        return updated_values


class SSHTunnelConfig(BaseConfig):
    """Настройки SSH-туннелирования"""

    host: str = Field(alias="SSH_HOST", title="Хост для SSH-туннеля")
    port: int = Field(alias="SSH_PORT", title="Порт для SSH-туннеля")
    user: str = Field(alias="SSH_USER", title="Имя пользователя для SSH-туннеля")
    key_path: str = Field(alias="SSH_KEY_PATH")

    @field_validator("key_path")
    def resolve_key_path(cls, value: str) -> str:
        return str(Path().absolute() / value)


class DatabaseConfig(BaseConfig):
    """Настройки переменных окружения базы данных."""

    db_user: str = Field(alias="POSTGRES_USER", title="Имя пользователя БД")
    db_password: SecretStr = Field(alias="POSTGRES_PASSWORD", title="Пароль пользователя БД")
    db_name: str = Field(alias="POSTGRES_DB", title="Названия БД")
    db_host: str = Field(alias="POSTGRES_HOST", title="Хост/IP БД")
    db_port: int = Field(alias="POSTGRES_PORT", title="Порт БД")

    db_echo: bool = Field(default=False, alias="DB_ECHO", title="Логгирование операций с БД")


class CORSConfig(BaseConfig):
    """Класс для настроек CORS."""

    allow_origins: list[str] = Field(default=["*"], alias="ALLOW_ORIGINS", title="Разрешённые источники")
    allow_credentials: bool = Field(default=True, alias="ALLOW_CREDENTIALS", title="Передача учётных данных")
    allow_methods: list[str] = Field(default=["*"], alias="ALLOW_METHODS", title="Разрешённые методы")
    allow_headers: list[str] = Field(default=["*"], alias="ALLOW_HEADERS", title="Разрешённые заголовки")


class FastAPIConfig(BaseConfig):
    """Настройки для запуска проекта"""

    host: str = Field(default="0.0.0.0", alias="FASTAPI_HOST", title="Host FastAPI")
    port: int = Field(default=8000, alias="FASTAPI_PORT", title="Port FastAPI")
    secret_key: str = Field(alias="SECRET_KEY", title="SECRET_KEY")
    docs_username: str = Field(alias="DOCS_USERNAME", title="SECRET_KEY")
    docs_password: str = Field(alias="DOCS_PASSWORD", title="SECRET_KEY")

class MainConfig(BaseConfig):
    """Класс для настроек переменных окружения проекта."""

    db: DatabaseConfig = DatabaseConfig()  # type:ignore
    cors: CORSConfig = CORSConfig()  # type:ignore
    project: FastAPIConfig = FastAPIConfig()  # type:ignore
    ssh: SSHTunnelConfig = SSHTunnelConfig()  # type: ignore


settings = MainConfig()  # type:ignore
