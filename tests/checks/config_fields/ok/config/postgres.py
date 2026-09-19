"""Каждое поле названо целиком."""

from typing import Annotated, ClassVar

from pydantic import BaseModel, Field

Port = Annotated[int, Field(ge=1, le=65535)]


class PostgresSettings(BaseModel):
    prefix: ClassVar[str] = "POSTGRES_"

    host: str = Field(min_length=1)
    port: Port = Field(default=5432)
    pool_size: int = Field(default=10, ge=1, le=100)
    dsn: str | None = Field(default=None, pattern=r"^postgresql://")
    timeout: float = Field(default=1.0, gt=0)
    debug: bool = Field(default=False)


class Level(BaseModel):
    """Имя вместо голого типа — уже правило."""

    value: Port = Field(default=1)
