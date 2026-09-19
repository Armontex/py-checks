"""Каждая проверка описывается папками с примерами, а не отдельным тестом.

Папка называется кодом правила: `model_columns` — это `model-columns`. Когда
примеров у правила несколько, к имени дописывают вариант через два
подчёркивания: `dependency_bounds__floating`. Вариант `__ok` — тот, в котором
правилу сказать нечего.

`checks/` — правила, которым дают файл: внутри `ok/` и `bad/`. `projects/` —
правила, которым дают корень проекта: внутри сам проект.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

from py_checks.config import load
from py_checks.core import available, python_files, survey

if TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion

FIXTURES = Path(__file__).parent / "checks"

PROJECTS = Path(__file__).parent / "projects"

VARIANT: Final = "__"

CLEAN: Final = "__ok"


def cases(directory: Path) -> list[str]:
    return sorted(path.name for path in directory.iterdir() if path.is_dir())


def rendered(*, directory: Path, case: str) -> list[str]:
    root = directory / case
    config = load(root=root)
    chosen = available().only(codes={case.split(VARIANT)[0].replace("_", "-")})
    violations = survey(
        chosen=chosen,
        files=python_files(
            paths=[],
            root=root,
            default=root / config.src,
            exclude=config.exclude,
        ),
        config=config,
        root=root,
    )
    return [violation.render(root=root) for violation in violations]


@pytest.mark.parametrize("case", cases(FIXTURES))
def test_check_output_matches_the_snapshot(case: str, snapshot: SnapshotAssertion) -> None:
    assert rendered(directory=FIXTURES, case=case) == snapshot


@pytest.mark.parametrize("case", cases(FIXTURES))
def test_nothing_is_reported_for_the_ok_examples(case: str) -> None:
    clean = [line for line in rendered(directory=FIXTURES, case=case) if line.startswith("ok/")]

    assert clean == []


@pytest.mark.parametrize("case", cases(PROJECTS))
def test_project_check_output_matches_the_snapshot(case: str, snapshot: SnapshotAssertion) -> None:
    assert rendered(directory=PROJECTS, case=case) == snapshot


@pytest.mark.parametrize("case", [case for case in cases(PROJECTS) if case.endswith(CLEAN)])
def test_nothing_is_reported_for_the_ok_projects(case: str) -> None:
    assert rendered(directory=PROJECTS, case=case) == []
