"""Секция `[mutation]`: как звать mutmut и с чем сравнивать."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import Field, ValidationError

from py_checks.config import CheckSettings, ConfigError, prefix
from py_checks.mutation._constants import BASELINE, SECTION

if TYPE_CHECKING:
    from py_checks.config import Config


class Mutation(CheckSettings):
    """Секция `[tool.py-checks.mutation]`.

    `command` — как позвать mutmut. По умолчанию из того же окружения, что и
    сама библиотека; список, а не строка, чтобы аргументы не разбирал шелл.

    `baseline` — файл, в котором `record` записывает выживших по модулям. С
    ним сравнивают и `diff`, и `full`.

    `against` — с чем сравнивать ветку, когда пуш сам этого не сказал:
    первое имя, которое знает этот клон.

    `children` — сколько мутантов проверять разом. Пусто — решает mutmut.

    `env` — переменные для прогона. Типичная — профиль hypothesis: свойство,
    которое каждый раз тянет новые примеры, убивает мутанта в одном прогоне
    и упускает в следующем, и запись начинает двигаться сама.

    Что мутировать, здесь не сказано: это `source_paths` и `do_not_mutate`
    самого mutmut, и гейт читает их оттуда же, откуда mutmut.
    """

    command: tuple[str, ...] = ("mutmut",)
    baseline: str = BASELINE
    against: tuple[str, ...] = ("origin/develop", "develop")
    children: int | None = Field(
        default=None,
        gt=0,
    )
    env: dict[str, str] = Field(default_factory=dict)


def mutation(*, config: Config) -> Mutation:
    try:
        return Mutation.model_validate(config.section(code=SECTION))
    except ValidationError as error:
        raise ConfigError(f"[{prefix(source=config.origin)}{SECTION}]: {error}") from error
