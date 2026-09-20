"""Раскладка проекта: один блок на директорию.

Четыре правила говорят об одной и той же вещи с четырёх сторон: что здесь
может лежать (`class-modules`), что живёт только здесь (`class-placement`),
что модуль обязан объявить (`required-class`) и какой формы тут операция
(`operation-shape`). Раньше у каждого была своя таблица, и один факт про
`use_cases` приходилось писать четыре раза в четырёх синтаксисах, склеивая их
глазами по строковому ключу.

Теперь блок один на директорию, а правила читают из него свои колонки:

```toml
[layout."application/use_cases"]
only = ["class"]
suffix = "UseCase"
required = true
operation = { method = "execute", max-arguments = 3 }
```

Правила при этом друг о друге по-прежнему не знают — они просто читают одну
таблицу. Адрес в заголовке ищется подряд идущими кусками пути, поэтому
`application/use_cases` находится и в модульном сервисе, где путь начинается
с `modules/<имя>/`, а `*` подходит любому одному куску.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final, Self

from pydantic import Field, model_validator

from py_checks.checks._kind import Kind
from py_checks.config import CheckSettings

if TYPE_CHECKING:
    from collections.abc import Iterable

    from py_checks.checks._kind import Declaration
    from py_checks.checks._location import Place

SECTION: Final = "layout"


class Orm(StrEnum):
    """Чем директория приходится ORM-модели.

    Дом модели и место, где её собирают, — два конца одного соглашения, и
    писать их в отдельной таблице значило бы назвать те же две директории
    второй раз: раскладка уже знает их по имени.
    """

    # Здесь модели объявляют: где-то ещё это таблица, которую никто не ждёт по
    # этому адресу, а autogenerate alembic видит только их пакет.
    DECLARED = "declared"

    # Здесь модели собирают: собрать модель — значит записать строку.
    BUILT = "built"


class Operation(CheckSettings):
    """Форма операции, которую держат в этой директории.

    `method` — единственная публичная дверь: сценарий просят об одном деле, и
    второй публичный метод означает вторую операцию, поделившую с первой
    конструктор. Пусто — значит число дверей не ограничено: у сервиса модуля
    их столько, сколько переходов у его сущности.

    `forbids` — имена типов, которых операция не держит: `UnitOfWork` ловится
    и как `IPlacementUnitOfWork`, и как `UnitOfWorkFactory`, потому что
    запрещено держать транзакцию, а не писать её имя одним конкретным образом.

    `max_arguments` — сколько аргументов занимает вход. Дверь несёт то, что
    пришло снаружи, и вход длиннее нескольких полей — вещь с именем: команда,
    запрос, DTO.
    """

    method: str | None = None
    forbids: tuple[str, ...] = ()
    max_arguments: int | None = Field(
        default=None,
        gt=0,
    )


class Directory(CheckSettings):
    """Что проект держит в этой директории.

    `only` — виды, которым здесь место, и ничего другого рядом не садится.
    `home` — виды, которым место ТОЛЬКО здесь: порт, объявленный в другом
    конце дерева, — это порт, которого читатель не найдёт.
    `area` — часть дерева, внутри которой дом и имя вообще о чём-то говорят:
    правило про `dto` написано про слой приложения, а dataclass в загрузчике
    или в наблюдаемости — просто способ сложить три поля рядом.
    `suffix` — как зовут класс, ради которого директория существует; он же
    живёт только здесь.
    `required` — модуль обязан объявить такой класс, первым и один.
    `operation` — форма операции, если здесь держат операции.
    `orm` — чем директория приходится ORM-модели: домом или местом сборки.
    `base` — базовый класс, по которому модель узнают в доме моделей.
    """

    only: tuple[Kind, ...] = ()
    home: tuple[Kind, ...] = ()
    area: str | None = None
    suffix: str | None = None
    required: bool = False
    operation: Operation | None = None
    orm: Orm | None = None
    base: str | None = None

    @model_validator(mode="after")
    def _named(self) -> Self:
        """Обязанность и форма опираются на имя: без суффикса их не проверить."""
        if self.suffix is not None:
            return self
        if self.required:
            message = "`required` без `suffix`: непонятно, какой класс обязан быть"
            raise ValueError(message)
        if self.operation is not None:
            message = "`operation` без `suffix`: непонятно, какой класс здесь операция"
            raise ValueError(message)
        return self

    @model_validator(mode="after")
    def _claims(self) -> Self:
        """Область сужает притязание: без дома и имени сужать нечего."""
        if self.area is not None and not self.home and self.suffix is None:
            message = "`area` без `home` и `suffix`: эта директория ни на что не притязает"
            raise ValueError(message)
        return self

    @model_validator(mode="after")
    def _declares(self) -> Self:
        """`base` — про дом моделей: в месте сборки узнавать по базе нечего."""
        if self.base is not None and self.orm is not Orm.DECLARED:
            message = '`base` без `orm = "declared"`: базу называет дом моделей'
            raise ValueError(message)
        return self


class Layout(CheckSettings):
    """Секция `[layout]`: адрес директории — и блок про неё.

    Ключи приходят из проекта, поэтому модель принимает любые: имена
    директорий — это данные, а не поля. Проверяется содержимое блока.
    """

    model_config = CheckSettings.model_config | {"extra": "allow"}

    # Типизированный `extra` pydantic: ключ — адрес, значение — блок.
    __pydantic_extra__: dict[str, Directory]  # type: ignore[assignment]

    @property
    def directories(self) -> dict[str, Directory]:
        return self.__pydantic_extra__


def addressed(
    *,
    layout: dict[str, Directory],
    orm: Orm,
) -> tuple[str, ...]:
    """Адреса, объявившие себя этим концом соглашения про ORM-модель."""
    return tuple(address for address, directory in layout.items() if directory.orm is orm)


def innermost(
    *,
    where: Place,
    among: Iterable[tuple[str, Directory]],
) -> tuple[str, Directory] | None:
    """Блок самой внутренней из совпавших директорий.

    Побеждает самая глубокая: `modules/betslip/application/services` важнее,
    чем `application`. При равной глубине — более длинный адрес: путь говорит о
    месте больше, чем одно имя.
    """
    matched = [
        (depth, len(address), address, directory)
        for address, directory in among
        if (depth := where.within(directory=address)) is not None
    ]
    if not matched:
        return None
    deepest = max(matched, key=lambda found: found[:2])
    return deepest[2], deepest[3]


@dataclass(frozen=True, slots=True)
class Claim:
    """Чей это дом и почему объявление в него просится."""

    address: str
    said: str


def claimants(
    *,
    declared: Declaration,
    layout: dict[str, Directory],
    where: Place,
) -> list[Claim]:
    """Адреса, объявившие это объявление своим: по имени или по виду.

    Блок с `area` притязает только на то, что лежит внутри названной части
    дерева: соглашение про `dto` написано про слой приложения, и dataclass в
    загрузчике ему не подсуден.
    """
    found: list[Claim] = []
    for address, directory in layout.items():
        if directory.area is not None and not where.holds(path=directory.area):
            continue
        said = _claim(
            declared=declared,
            directory=directory,
        )
        if said is not None:
            found.append(
                Claim(
                    address=address,
                    said=said,
                )
            )
    return found


def _claim(
    *,
    declared: Declaration,
    directory: Directory,
) -> str | None:
    """Почему этот адрес считает объявление своим; `None` — не считает."""
    if directory.suffix is not None and declared.name.endswith(directory.suffix):
        return f"кончается на {directory.suffix}"
    if declared.kind is not None and declared.kind in directory.home:
        return f"— {declared.kind.said}"
    return None
