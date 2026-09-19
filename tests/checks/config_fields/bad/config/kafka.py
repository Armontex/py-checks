"""Значения приходят текстом из окружения, а границ никто не назвал."""

from pydantic import BaseModel, Field


class KafkaSettings(BaseModel):
    brokers: str = Field(default="localhost:9092")
    pool_size: int = Field(default=10)
    topic: str = "orders"
    retries: int
