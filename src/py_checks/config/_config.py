"""Общие настройки проекта."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, ValidationError

from py_checks.config._base import CheckSettings
from py_checks.config._constants import DEFAULT_EXCLUDE, PYPROJECT, SECTION
from py_checks.config._errors import ConfigError
from py_checks.config._toml import TomlTable


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
