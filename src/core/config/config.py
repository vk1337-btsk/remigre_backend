from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    """Базовый класс для конфигурации переменных окружения проекта."""

    # Флаг, указывающий на project/developer
    debug: bool = Field(default=False, alias="DEBUG", title="Флаг, указывающий на project/developer")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="before")
    def set_project_or_develop_config(cls, values) -> dict:
        """Определяет переменный окружения для проекта в зависимости от DEBUG, удаляет лишние переменные."""

        debug = values.get("DEBUG", "") == "True"
        prefix_save = "develop_" if debug else "project_"
        prefix_drop = "project_" if debug else "develop_"

        updated_values = {
            key.replace(prefix_save, "").upper() if key.startswith(prefix_save) else key: value
            for key, value in values.items()
            if not key.startswith(prefix_drop)
        }
        return updated_values

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class DatabaseConfig(BaseConfig):
    """Настройки переменных окружения базы данных."""

    # Настройки БД
    db_user: str = Field(alias="POSTGRES_USER", title="Имя пользователя БД")
    db_password: SecretStr = Field(alias="POSTGRES_PASSWORD", title="Пароль пользователя БД")
    db_name: str = Field(alias="POSTGRES_DB", title="Названия БД")
    db_host: str = Field(alias="POSTGRES_HOST", title="Хост/IP БД")
    db_port: int = Field(alias="POSTGRES_PORT", title="Порт БД")

    db_echo: bool = Field(default=False, alias="DB_ECHO", title="Логгирование операций с БД")

    @field_validator("db_echo", mode="after")
    def get_db_echo(cls, v, info):
        return info.data["debug"]

    @property
    def url_async(self) -> SecretStr:
        return SecretStr(
            f"postgresql+asyncpg://{self.db_user}:{self.db_password.get_secret_value()}@"
            f"{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def url_sync(self) -> SecretStr:
        return SecretStr(
            f"postgresql+psycopg2://{self.db_user}:{self.db_password.get_secret_value()}@"
            f"{self.db_host}:{self.db_port}/{self.db_name}"
        )


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


class MainConfig(BaseConfig):
    """Класс для настроек переменных окружения проекта."""

    # Настройки БД
    db: DatabaseConfig = DatabaseConfig()  # type:ignore

    # Настройки CORS
    cors: CORSConfig = CORSConfig()  # type:ignore

    # Настройки CORS
    fastapi: FastAPIConfig = FastAPIConfig()  # type:ignore


settings = MainConfig()  # type:ignore
