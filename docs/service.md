# Настройки типового сервиса

Библиотека не знает, как называются слои проекта и где живёт его ORM: у сервиса
это `domain` и `infra/database`, у утилиты таких слоёв нет вовсе. Поэтому таблиц
внутри неё нет — их приносит шаблон при генерации проекта.

Здесь лежит то, что было общего у четырёх сервисов (`personal_bot`, `beauty`,
`betting`, `trading`) на момент переноса. Это заготовка для шаблона и
одновременно запись того, что именно считалось правильным.

## Слои

```toml
[tool.python-checks.contracts]
# Связывать слои между собой — вся их работа, поэтому им можно всё.
composition-root = ["ioc", "bootstrap", "entrypoints"]

# Зависимости смотрят внутрь: домен не знает ничего, приложение знает домен,
# а всё, что разговаривает с внешним миром, знает приложение и невидимо для
# него. `presentation` намеренно не видит `domain`: край переводит свои типы в
# DTO приложения и обратно, и роутер, читающий доменный объект, связал форму
# внешнего мира с формой правил.
[tool.python-checks.contracts.layers]
domain = ["domain", "shared"]
application = ["domain", "application", "shared"]
infra = ["domain", "application", "infra", "shared", "config"]
presentation = ["application", "presentation", "shared", "config"]
observability = ["observability", "shared", "config"]
config = ["config", "shared"]
shared = ["shared"]
```

В `trading` между приложением и краем стоит ещё один слой — операция, которой
нужны два модуля, и есть workflow:

```toml
workflows = ["domain", "application", "workflows", "shared"]
presentation = ["application", "workflows", "presentation", "shared", "config"]
```

## Где чей фреймворк

```toml
[tool.python-checks.confined-imports.packages]
sqlalchemy = ["infra/database", "ioc"]
asyncpg = ["infra/database", "ioc"]
aiosqlite = ["infra/database"]
alembic = ["infra/database"]
fastapi = ["presentation", "bootstrap"]
starlette = ["presentation", "bootstrap"]
starlette_exporter = ["bootstrap"]
dishka = ["ioc", "bootstrap", "presentation"]
uvicorn = ["entrypoints"]
typer = ["entrypoints"]
sentry_sdk = ["observability"]
prometheus_client = ["observability", "bootstrap", "infra"]
opentelemetry = ["observability", "bootstrap", "infra"]
```

Своё дописывается рядом: `maxapi = ["presentation", "bootstrap/channels", "ioc"]`
у бота, `aiokafka = ["infra/kafka", "ioc"]` у trading, `sportsbook_contracts` у
betting и trading. Пустой список значит «нигде» — так держат убранную
библиотеку, чтобы она не вернулась: `agents = []`.

## Что запечатано

```toml
[tool.python-checks.sealed-imports]
# `modules` держит правила и интерфейсы вокруг них: DTO здесь — dataclass, а не
# модель фреймворка. `shared` печатают bot и betting: его импортирует домен
# каждого модуля, поэтому фреймворк, добравшийся туда, оказывается в каждом
# запечатанном слое сразу.
zones = ["modules", "shared"]

[tool.python-checks.sealed-imports.allow]
# Сценарий руководит и потому имеет право сказать, что произошло; правила верны
# независимо от того, слушает ли их кто-нибудь.
application = ["structlog"]
```

В `beauty` в `shared` живёт валидатор адреса, поэтому там запечатан только
`modules`.
