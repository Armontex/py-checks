"""ORM живёт у базы данных."""

from sqlalchemy.ext.asyncio import create_async_engine

__all__ = ["create_async_engine"]
