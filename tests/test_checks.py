"""Каждая проверка описывается папками с примерами, а не отдельным тестом."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from python_checks.config import load
from python_checks.core import available, inspect, python_files

if TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion

FIXTURES = Path(__file__).parent / "checks"


def cases() -> list[str]:
    return sorted(path.name for path in FIXTURES.iterdir() if path.is_dir())


def rendered(case: str) -> list[str]:
    root = FIXTURES / case
    config = load(root=root)
    check = available().files[case.replace("_", "-")]
    files = python_files(paths=[], root=root, default=root / config.src, exclude=config.exclude)
    violations = inspect(files=files, checks=[check], config=config, root=root)
    return [violation.render(root=root) for violation in violations]


@pytest.mark.parametrize("case", cases())
def test_check_output_matches_the_snapshot(case: str, snapshot: SnapshotAssertion) -> None:
    assert rendered(case) == snapshot


@pytest.mark.parametrize("case", cases())
def test_nothing_is_reported_for_the_ok_examples(case: str) -> None:
    clean = [line for line in rendered(case) if line.startswith("ok/")]

    assert clean == []
