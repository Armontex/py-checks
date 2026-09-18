"""Где какому пакету место — общее для всех сервисов."""

from __future__ import annotations

from typing import Final

# Пакет — пути, под которыми он разрешён; путь считается от корневого пакета
# проекта (`src/<пакет>/`). Пустой список значит «нигде»: так снимают
# библиотеку, которую убрали, чтобы она не вернулась.
#
# База описывает типовой сервис: ORM живёт у базы данных, веб-стек на краю,
# контейнер в композиционном корне, запускалки в точках входа. Свой стек
# (`maxapi`, `aiokafka`, контракты компании) проект дописывает себе.
CONFINED: Final[dict[str, tuple[str, ...]]] = {
    "sqlalchemy": ("infra/database", "ioc"),
    "asyncpg": ("infra/database", "ioc"),
    "aiosqlite": ("infra/database",),
    "alembic": ("infra/database",),
    "fastapi": ("presentation", "bootstrap"),
    "starlette": ("presentation", "bootstrap"),
    "starlette_exporter": ("bootstrap",),
    "dishka": ("ioc", "bootstrap", "presentation"),
    "uvicorn": ("entrypoints",),
    "typer": ("entrypoints",),
    "sentry_sdk": ("observability",),
    "prometheus_client": ("observability", "bootstrap", "infra"),
    "opentelemetry": ("observability", "bootstrap", "infra"),
}

# Запечатанные зоны: внутри них чужих пакетов нет вовсе. `modules` держит
# правила и интерфейсы вокруг них, и DTO там — это dataclass, а не модель
# фреймворка. `shared` печатают не все: в него иногда кладут валидатор адреса,
# поэтому проект добавляет его себе сам.
ZONES: Final[tuple[str, ...]] = ("modules",)

# Слой запечатанной зоны — что ему всё-таки можно. `application` руководит и
# потому имеет право сказать, что произошло; `domain` держит правила, которые
# верны независимо от того, слушает ли их кто-нибудь, и не знает ничего.
ALLOW: Final[dict[str, tuple[str, ...]]] = {"application": ("structlog",)}
