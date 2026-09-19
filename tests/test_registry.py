"""Правило существует, только если о нём сказано в манифесте.

Добавить проверку — значит написать модуль, выставить класс наружу из пакета
группы и объявить его в `pyproject.toml`. Забытый третий шаг выглядит как
работающая проверка, которую никто никогда не звал, — поэтому о нём тут и
спрашивают.
"""

from __future__ import annotations

import importlib
import pkgutil
from importlib.metadata import entry_points
from typing import TYPE_CHECKING, Any

import python_checks.checks
from python_checks.core import GROUP, FileCheck, ProjectCheck, available

if TYPE_CHECKING:
    from python_checks.core import Check


def a_check(*, candidate: object) -> bool:
    """Правило узнаётся по тому, из чего оно состоит: код и `run`.

    Модели настроек и вспомогательные типы, которые пакет группы тоже
    выставляет наружу, ни тем, ни другим не обладают.
    """
    return isinstance(candidate, type) and hasattr(candidate, "code") and hasattr(candidate, "run")


def declared() -> set[str]:
    """Коды правил, выставленных наружу пакетами групп."""
    found: set[str] = set()
    for module in pkgutil.iter_modules(python_checks.checks.__path__):
        group: dict[str, Any] = vars(importlib.import_module(f"python_checks.checks.{module.name}"))
        found.update(
            group[name].code for name in group.get("__all__", ()) if a_check(candidate=group[name])
        )
    return found


def word(*, check: Check) -> str:
    """Слово группы, в которой правило лежит, — не то, которое оно назвало само."""
    group: dict[str, Any] = vars(importlib.import_module(type(check).__module__.rsplit(".", 1)[0]))
    return group["MARKER"]


def test_every_declared_check_is_in_the_manifest() -> None:
    assert declared() == set(available().listed)


def test_no_two_checks_share_a_code() -> None:
    assert len(list(entry_points(group=GROUP))) == len(available().listed)


def test_every_check_matches_a_protocol() -> None:
    for check in available().listed.values():
        assert isinstance(check, FileCheck | ProjectCheck), check.code


def test_every_check_carries_the_word_of_its_group() -> None:
    for check in available().listed.values():
        assert check.marker == word(check=check), check.code
