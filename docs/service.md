# Настройки типового сервиса

Библиотека не знает, как называются слои проекта и где живёт его ORM: у сервиса
это `domain` и `infra/database`, у утилиты таких слоёв нет вовсе. Поэтому таблиц
внутри неё нет — их приносит шаблон при генерации проекта.

Здесь лежит то, что было общего у четырёх сервисов (`personal_bot`, `beauty`,
`betting`, `trading`) на момент переноса. Это заготовка для шаблона и
одновременно запись того, что именно считалось правильным.

Настройки ruff и pyright здесь по той же причине: библиотека их не возит, их
кладёт шаблон, и дальше это файлы проекта.

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

## Что лежит в директории

```toml
[tool.python-checks.class-modules.policies]
use_cases = ["class"]
"application/services" = ["class"]
repositories = ["class"]
tools = ["class", "port"]
ports = ["port", "alias"]
dto = ["dataclass", "alias"]
schemas = ["model", "alias"]
errors = ["error", "alias"]
```

Ключ — путь, а не имя: `application/services` держит класс-оркестратор, а
`domain/services` — функции, правила, сравнивающие два факта. Правило по имени
запретило бы всю доменную категорию целиком.

Виды: `class`, `port` (Protocol, ABC), `dataclass`, `model` (pydantic), `alias`,
`enum`, `error`, `function`. Импорты, константы, `if TYPE_CHECKING` и докстринг
разрешены везде.

Исключение узнаётся и по базе `Exception`, и по имени базы: `class
NotFound(OrderError)` наследуется от своего же корня, а не от `Exception`, но
имя корня кончается так же. Поэтому весь словарь отказов пакета собирается в
`errors/` или `exceptions.py`, и читатель находит его в одном месте.

## Где место классу

Обратная таблица: `class-modules` говорит, что можно держать в директории,
`class-placement` — куда обязан лечь класс, откуда бы его ни начали писать.

```toml
[[tool.python-checks.class-placement.rules]]
kind = "error"
inside = ["errors", "exceptions"]

[[tool.python-checks.class-placement.rules]]
kind = "port"
inside = ["ports"]
area = "application"

[[tool.python-checks.class-placement.rules]]
suffix = "Repository"
inside = ["infra/database/repositories", "ports"]

[[tool.python-checks.class-placement.rules]]
kind = "dataclass"
inside = ["dto"]
area = "application"

[[tool.python-checks.class-placement.rules]]
suffix = "UseCase"
inside = ["use_cases"]
area = "application"

[[tool.python-checks.class-placement.rules]]
suffix = "Service"
inside = ["application/services"]
area = "application"
```

Правило говорит о виде (`kind`) или о суффиксе имени (`suffix`) — ровно об
одном из двух. Порядок значим: отвечает первое подошедшее правило, поэтому
исключение остаётся исключением, даже если его имя кончается на `Service`.

`area` сужает правило до части дерева и держит на себе половину смысла.
`dataclass` обязан лежать в `dto/` только внутри `application`: доменный value
object — тоже dataclass, и живёт он в домене. Область ищется подряд идущими
кусками адреса, поэтому `application` находится и в модульном сервисе, где путь
начинается с `modules/<имя>/`.

`inside` перечисляет равноправные адреса, и адрес включает имя модуля: `errors`
подходит и как директория, и как файл `exceptions.py`. У trading порт репозитория
называется `IOutboxRepository` и лежит в `shared/ports`, поэтому в его таблице
`ports` стоит рядом с `infra/database/repositories` — реализация и интерфейс
одного суффикса законно лежат в двух местах.

## ruff

`ruff.toml` в корне; `pyproject.toml` секцию `[tool.ruff]` при этом не держит —
найдя свой файл в корне, ruff перестаёт читать pyproject целиком, и оставленная
там секция молча перестаёт действовать.

```toml
line-length = 100
target-version = "py314"

[lint]
select = [
    "E",
    "F",
    "I",
    "UP",
    "B",
    "S",       # bandit: assert, слабая случайность, инъекции
    "ASYNC",   # блокирующий вызов внутри async def
    "DTZ",     # datetime без зоны
    "N",       # именование
    "ARG",     # аргумент, который никто не читает
    "TC",      # импорт ради аннотации, нужный только проверяльщику типов
    "ERA",     # закомментированный код
    "T20",     # забытый print
    "PLR0912", # слишком много ветвей
    "PLR0915", # слишком много инструкций
    "PLR2004", # число в сравнении вместо константы
    "PGH",     # глухой ignore прячет и все будущие ошибки, называй код
]
# B008: вызов в значении по умолчанию — то, как fastapi и typer объявляют
# зависимости, там это подпись, а не спрятанное состояние.
ignore = ["B008"]
```

Отдельный bandit при этом не нужен: правила `S` — это он и есть, переписанный
внутри ruff. В четырёх сервисах он стоит рядом с ruff как вторая зависимость и
второй хук — при переезде выкидывается.

Послабления по папкам — проектные; то, что повторялось у всех:

```toml
[lint.per-file-ignores]
# Тест утверждает — для этого он и есть; число, с которым он сравнивает, и есть
# предмет теста, а имя вместо числа его прячет.
"tests/*" = ["S101", "PLR2004", "ARG001", "S105", "S106", "TC001", "TC002", "TC003"]
# fastapi, dishka и pydantic читают аннотации во время работы: импорт, уехавший
# под TYPE_CHECKING, здесь не экономия, а NameError при объявлении маршрута.
"src/*/presentation/*" = ["TC001", "TC002", "TC003"]
"src/*/bootstrap/*" = ["TC001", "TC002", "TC003"]
"src/*/ioc/*" = ["TC001", "TC002", "TC003"]
"src/*/config/*" = ["TC001", "TC002", "TC003"]
"src/*/infra/database/models/*" = ["TC001", "TC002", "TC003"]
# Ревизия — шаблон самого alembic, и SQL в ней написан словами и заморожен в
# день рождения миграции.
"migrations/versions/*" = ["TC003", "S608"]
```

## pyright

`pyrightconfig.json` в корне — и по той же причине: найдя его, pyright
перестаёт читать `[tool.pyright]` из pyproject.

```json
{
  "pythonVersion": "3.14",
  "typeCheckingMode": "strict",
  "venvPath": ".",
  "venv": ".venv",
  "include": ["src", "tests"]
}
```

Strict везде, а не по директориям: неаннотированная функция и `Any`, вылезший
на границу, — ошибка и в композиционном корне тоже.
