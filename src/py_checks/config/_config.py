"""Общие настройки проекта."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from pydantic import Field, ValidationError

from py_checks.config._base import CheckSettings
from py_checks.config._constants import DEFAULT_EXCLUDE, PYPROJECT, SECTION
from py_checks.config._errors import ConfigError
from py_checks.config._toml import TomlTable

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True, slots=True)
class Moved:
    """Куда переехала секция и чем она там записывается."""

    into: str
    written: str


# Секции, которые больше не читаются. Молчать о них нельзя: незнакомая секция
# выглядит как работающая настройка, а на деле правило судит по пустой таблице.
#
# Четыре правила про раскладку говорили об одной директории с четырёх сторон, и
# один факт приходилось писать четыре раза в четырёх синтаксисах. `endpoint-
# declarations` переехал по той же причине с другого конца: маршрут оказался не
# единственным входом в процесс, а второй вид входа в плоскую секцию не встаёт.
RETIRED: Final[dict[str, Moved]] = {
    "class-modules": Moved(
        into="layout",
        written="`only`",
    ),
    "class-placement": Moved(
        into="layout",
        written="`home` и `suffix`",
    ),
    "required-class": Moved(
        into="layout",
        written="`required` рядом с `suffix`",
    ),
    "operation-shape": Moved(
        into="layout",
        written="`operation`",
    ),
    "model-boundary": Moved(
        into="layout",
        written="`orm` и `base`",
    ),
    "endpoint-declarations": Moved(
        into="edge-declarations",
        written="блок вида входа — `route` с теми же ключами",
    ),
}


def retired(
    *,
    checks: Mapping[str, object],
    source: Path | None,
) -> None:
    """Падает, если в настройках остались секции, которые слились в общие таблицы."""
    found = sorted(name for name in RETIRED if name in checks)
    if not found:
        return
    named = prefix(source=source)
    listed = "; ".join(
        f"[{named}{name}] -> [{named}{RETIRED[name].into}], {RETIRED[name].written}"
        for name in found
    )
    raise ConfigError(
        f"эти секции больше не читаются, их содержимое переехало в общие таблицы, "
        f"блок на предмет разговора: {listed}"
    )


def prefix(*, source: Path | None) -> str:
    """Как называется секция проверки в том файле, откуда пришли настройки.

    В `pyproject.toml` инструменты живут под своей приставкой, потому что файл
    общий; в своём файле приставки нет — весь файл принадлежит одному
    инструменту. Сообщение об ошибке обязано звать секцию так, как её и правда
    зовут в этом файле: иначе оно посылает читателя не туда.
    """
    if source is None or source.name == PYPROJECT:
        return f"tool.{SECTION}."
    return ""


class Config(CheckSettings):
    """Где искать код и что не проверять.

    Настройки самих проверок сюда не попадают: они лежат в своих секциях и
    разбираются моделью той проверки, которой принадлежат. Ядро держит их
    нетронутыми в `checks` и отдаёт владельцу через `settings_for`.
    """

    src: Path = Path("src")
    exclude: tuple[str, ...] = DEFAULT_EXCLUDE
    extend_exclude: tuple[str, ...] = ()
    ignore: tuple[str, ...] = ()
    checks: dict[str, TomlTable] = Field(
        default_factory=dict,
        exclude=True,
    )
    # Файл, из которого настройки прочитаны: он же и место, куда сообщение об
    # ошибке отправляет читателя.
    origin: Path | None = Field(
        default=None,
        exclude=True,
    )

    @property
    def excluded(self) -> tuple[str, ...]:
        """Что не проверяем: список по умолчанию плюс добавленный проектом.

        `exclude` задаёт весь список целиком, `extend-exclude` добавляет к нему:
        так проект добавляет свою папку, не переписывая `.venv` и остальное.
        """
        return self.exclude + self.extend_exclude

    def section(self, *, code: str) -> TomlTable:
        return self.checks.get(code, {})

    def settings_for(
        self,
        *,
        code: str,
        model: type[CheckSettings],
    ) -> CheckSettings:
        """Настройки проверки: её секция, проверенная её же моделью."""
        try:
            return model.model_validate(self.section(code=code))
        except ValidationError as error:
            raise ConfigError(f"[{prefix(source=self.origin)}{code}]: {error}") from error

    def enabled(self, *, code: str) -> bool:
        return code not in self.ignore
