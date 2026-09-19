"""Каждое поле названо целиком."""

from typing import Annotated, ClassVar

from pydantic import BaseModel, Field

Port = Annotated[int, Field(ge=1, le=65535)]


class PostgresSettings(BaseModel):
    prefix: ClassVar[str] = "POSTGRES_"

    host: str = Field(validation_alias="POSTGRES_HOST", min_length=1)
    port: Port = Field(validation_alias="POSTGRES_PORT", default=5432)
    pool_size: int = Field(validation_alias="POSTGRES_POOL_SIZE", default=10, ge=1, le=100)
    dsn: str | None = Field(
        validation_alias="POSTGRES_DSN",
        default=None,
        pattern=r"^postgresql://",
    )
    timeout: float = Field(validation_alias="POSTGRES_TIMEOUT", default=1.0, gt=0)
    debug: bool = Field(validation_alias="POSTGRES_DEBUG", default=False)


class Level(BaseModel):
    """Имя вместо голого типа — уже правило."""

    value: Port = Field(validation_alias="LEVEL_VALUE", default=1)


class Settings(BaseModel):
    """Секция собирается фабрикой: переменные читают её собственные поля."""

    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
