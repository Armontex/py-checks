"""Какие проверки существуют и как их находят."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from importlib.metadata import entry_points
from typing import TYPE_CHECKING

from py_checks.core._constants import GROUP
from py_checks.core._errors import UnknownCheckError
from py_checks.core._protocols import Scope

if TYPE_CHECKING:
    from collections.abc import Collection

    from py_checks.core._protocols import Check, FileCheck, ProjectCheck


@dataclass(frozen=True, slots=True)
class Checks:
    """Правила, разобранные по тому, что им дают: файл или корень проекта.

    Один и тот же вид описывает и всё, что установлено, и то, что выбрали на
    этот прогон, — поэтому выбор не превращается в развилку у каждого, кто его
    получает: прогон, список и объяснение говорят об одном и том же наборе.
    """

    files: dict[str, FileCheck]
    project: dict[str, ProjectCheck]

    @property
    def listed(self) -> dict[str, Check]:
        """Все правила по коду, независимо от вида."""
        return {**self.files, **self.project}

    def only(self, *, codes: Collection[str]) -> Checks:
        """Тот же набор, суженный до названных кодов."""
        return Checks(
            files={code: check for code, check in self.files.items() if code in codes},
            project={code: check for code, check in self.project.items() if code in codes},
        )


@cache
def available() -> Checks:
    """Все проверки, объявленные через entry points.

    Так проект или команда добавляет своё правило: ставит рядом свой пакет с
    записью в этой же группе, а библиотеку форкать не нужно. Вид правила —
    файл ему дают или корень проекта — объявляет оно само.

    Читается один раз: загрузка означает импорт каждого объявленного модуля, а
    спрашивают реестр и прогон, и выбор, и объяснение.
    """
    files: dict[str, FileCheck] = {}
    project: dict[str, ProjectCheck] = {}
    for entry in sorted(entry_points(group=GROUP), key=lambda entry: entry.name):
        check = entry.load()()
        if check.scope is Scope.FILE:
            files[check.code] = check
        else:
            project[check.code] = check
    return Checks(
        files=files,
        project=project,
    )


def get(*, code: str) -> Check:
    checks = available().listed
    if code not in checks:
        raise UnknownCheckError(
            code=code,
            known=tuple(sorted(checks)),
        )
    return checks[code]
