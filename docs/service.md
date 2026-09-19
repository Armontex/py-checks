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

[[tool.python-checks.class-placement.rules]]
kind = "model"
inside = ["schemas/requests", "schemas/responses"]
area = "presentation"
```

Правило говорит о виде (`kind`) или о суффиксе имени (`suffix`) — ровно об
одном из двух. Порядок значим: отвечает первое подошедшее правило, поэтому
исключение остаётся исключением, даже если его имя кончается на `Service`.

`area` сужает правило до части дерева и держит на себе половину смысла.
`dataclass` обязан лежать в `dto/` только внутри `application`: доменный value
object — тоже dataclass, и живёт он в домене. Область ищется подряд идущими
кусками адреса, поэтому `application` находится и в модульном сервисе, где путь
начинается с `modules/<имя>/`.

Последняя строка — вход HTTP: схема, объявленная рядом с маршрутом, случайно
оказывается общей, поэтому запрос и ответ живут в `schemas`. Две половины, а не
одна: модель прямо в `schemas` — это модель, направление которой читатель
угадывает по имени, а один класс на оба конца — запрос, отрастивший поле,
которого не хотел ответ. В beauty и trading половин нет, там адреса —
`requests` и `schemas`.

`inside` перечисляет равноправные адреса, и адрес включает имя модуля: `errors`
подходит и как директория, и как файл `exceptions.py`. У trading порт репозитория
называется `IOutboxRepository` и лежит в `shared/ports`, поэтому в его таблице
`ports` стоит рядом с `infra/database/repositories` — реализация и интерфейс
одного суффикса законно лежат в двух местах.

## Что модуль обязан объявить

```toml
[tool.python-checks.required-class.suffixes]
use_cases = "UseCase"
"application/services" = "Service"
repositories = "Repository"
config = "Settings"
models = "Model"
tools = "Tool"
```

Файл в `use_cases` существует ради сценария, файл в `repositories` — ради
репозитория. Класс идёт первым и идёт один: имя файла — это то, как читатель
находит класс, и модуль, названный ни одним из трёх лежащих в нём сценариев,
отвечает на вопрос «где `ResolveLimitsUseCase`» словами «прочти все три».

Выше требуемого класса разрешены константы, алиасы и перечисления. Перечисление —
не поблажка, а необходимость: тело класса выполняется в момент объявления, и
словарь, который класс называет у себя внутри, ниже него написать нельзя.

Правило не касается `__init__.py` (переэкспорт, а не объявление), пустого
модуля и модуля с подчёркиванием: `_base.py` держит машинерию своей директории,
а не один из её классов. Подчёркивание — единственная форма этой поблажки,
списка голых имён нет. В beauty и trading по три модуля в `models/` названы
`base.py`, `bound_check.py`, `enum_column.py` — это ровно тот случай, и
переименование в `_base.py` и есть ответ.

Ключ — путь: побеждает самая внутренняя из совпавших директорий, при равной
глубине — более длинный ключ. Поэтому `application/services` требует класс, а
`domain/services` не требует ничего: там лежат функции, правила, сравнивающие
два факта.

## Как устроена операция

```toml
[[tool.python-checks.operation-shape.operations]]
inside = "use_cases"
suffix = "UseCase"
method = "execute"
max-arguments = 3

# Дверей у сервиса столько, сколько переходов у его сущности: `IBetWriter`
# держит шесть, по одной на переход, потому что переход — это один вызов, и
# вызывающий, которому пришлось бы сделать три, сделает два.
[[tool.python-checks.operation-shape.operations]]
inside = "application/services"
suffix = "Service"
forbids = ["UnitOfWork"]
```

Сценарий просят об одном деле: один публичный метод, и он называется
`execute`. Второй публичный метод — вторая операция, поделившая с первой
конструктор, и вызывающий, которому нужна одна, тащит зависимости обеих.
Приватных методов сколько угодно: длинная операция, разложившая себя на
`_begun`, `_judged` и `_risked`, остаётся одной операцией.

Вход этой двери — три поля, не больше. То, что пришло снаружи и заняло
четыре, — это вещь с именем: команда, запрос, DTO. Считаются публичные методы,
поэтому конструктор в счёт не идёт сам собой: через него приходят зависимости,
а это проводка, не вход. Первый аргумент метода определяется по месту, а не по
имени — `self` в `@staticmethod` считается как любой другой.

`PLR0913` из ruff это не заменяет: он не знает ни классов, ни исключения для
конструктора. С `max-args = 3` он даёт 29, 142, 96 и 108 срабатываний по
сервисам, а внутри одних только `use_cases` — 49, и все до единого приходятся
на `__init__`.

Рядом с операцией не стоит ничего: ни второй класс, ни функция — ни выше, ни
ниже. Константы и алиасы стоять могут, перечисление — нет, в отличие от других
директорий: словарь — это класс, и операция, которой он понадобился, называет
то, чем её модуль не владеет.

`forbids` ловит имя типа подстрокой, поэтому `UnitOfWork`, `IAuthUnitOfWork` и
`AuthUnitOfWorkFactory` отвергаются одинаково — запрещено держать транзакцию, а
не писать её имя одним конкретным образом. Строка, у кого этот запрет, у
сервисов проектная: в боте транзакцию открывает сценарий и передаёт сервису
репозитории, а в beauty, betting и trading фабрику держит сам сценарий — там
запрет стоит только на сервисах.

`application/services` и никогда `domain/services`: доменный сервис — это
функция, сравнивающая два факта, которые не принадлежат ни одному из них.

## Пределы длины и вложенности

```toml
[tool.python-checks.module-length]
max-lines = 600

# `with` в таблице нет намеренно: вложенный `with` ловит ruff `SIM117`, с
# автофиксом и с готовым ответом — «сделай один `with a, b:`».
[tool.python-checks.nesting.limits]
try = 1
if = 2
```

Строки модуля считаются как написаны, вместе с пустыми и комментариями:
держать в голове читателю приходится их все.

Глубина — это место, где логику перестают читать и начинают расшифровывать.
Предел у каждого вида свой, потому что стоят они разного: второй `try` внутри
первого прячет, какая строка бросила, а второй уровень `if` — обычная
развилка, лишним становится третий. `elif` — ветка, а не уровень; написанный
развёрнуто `else:` с `if` внутри — уровень, это и есть лишний отступ.

`PLR1702` из ruff это не заменяет. Во-первых, он preview-only: без `--preview`
ruff молча не выполняет правило и рапортует, что всё чисто. Во-вторых, он
считает общую глубину одним числом на все виды сразу — при пределе 3 пропускает
`try` внутри `try`, а при 1 роняет законную цепочку `for`/`try`/`with`/`if`,
какая нашлась в trading.

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
    "SIM117",  # вложенный `with` вместо одного `with a, b:`, с автофиксом
    "PLR0912", # слишком много ветвей
    "PLR0915", # слишком много инструкций
    "PLR2004", # число в сравнении вместо константы
    "PGH",     # глухой ignore прячет и все будущие ошибки, называй код
]
# B008: вызов в значении по умолчанию — то, как fastapi и typer объявляют
# зависимости, там это подпись, а не спрятанное состояние.
ignore = ["B008"]
```

### Что закрывает ruff, а что проверки

| Соглашение | Чем закрыто |
|---|---|
| Длина функции | ruff `PLR0915` — с оговоркой: он считает инструкции, а не строки, и на четырёх сервисах при пределе 50 не срабатывает ни разу, хотя десять функций там длиннее 50 строк |
| Число ветвей в функции | ruff `PLR0912` |
| Вложенный `with` | ruff `SIM117`, с автофиксом |
| Глубина `try` и `if` | правило `nesting`: в ruff такого нет — `PLR1702` считает все виды одним числом и живёт в preview |
| Число аргументов входа | правило `operation-shape`, настройка `max-arguments`: `PLR0913` не знает ни классов, ни исключения для конструктора |
| Длина модуля | правило `module-length`: в ruff правила нет, в pylint это `C0302` |
| Полная запись сигнатуры | правило `keyword-only-arguments`, с автофиксом |
| Число в сравнении, забытый `print`, закомментированный код | ruff `PLR2004`, `T20`, `ERA` |

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
