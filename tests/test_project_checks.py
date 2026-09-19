"""Правила, которые судят проект целиком, описываются проектами-примерами."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from python_checks.config import load
from python_checks.core import available, examine

if TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion

PROJECTS = Path(__file__).parent / "projects"

CASES = (
    ("bounded", "dependency-bounds"),
    ("floating", "dependency-bounds"),
)


def rendered(case: str, code: str) -> list[str]:
    root = PROJECTS / case
    violations = examine(
        checks=[available().project[code]],
        config=load(root=root),
        root=root,
    )
    return [violation.render(root=root) for violation in violations]


@pytest.mark.parametrize(("case", "code"), CASES)
def test_project_check_output_matches_the_snapshot(
    case: str,
    code: str,
    snapshot: SnapshotAssertion,
) -> None:
    assert rendered(case, code) == snapshot


def test_nothing_is_reported_for_the_bounded_project() -> None:
    assert rendered("bounded", "dependency-bounds") == []
