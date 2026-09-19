from __future__ import annotations

from pathlib import Path

from py_checks.checks._location import place
from py_checks.core import ParsedFile


def parsed(path: str, source: Path | None) -> ParsedFile:
    return ParsedFile(path=Path(path), text="", source=source)


def test_place_is_counted_from_the_source_root() -> None:
    where = place(file=parsed("/repo/src/app/infra/database/engine.py", Path("/repo/src")))

    assert where is not None
    assert where.package == "app"
    assert where.where == "infra/database/engine"


def test_a_folder_without_an_init_does_not_break_the_address() -> None:
    """В одном из сервисов половина репозиториев лежит в папках без `__init__.py`."""
    where = place(
        file=parsed("/repo/src/app/infra/database/repositories/items.py", Path("/repo/src"))
    )

    assert where is not None
    assert where.under(prefix="infra/database")


def test_the_package_init_is_addressed_by_its_package() -> None:
    where = place(file=parsed("/repo/src/app/presentation/__init__.py", Path("/repo/src")))

    assert where is not None
    assert where.where == "presentation"


def test_without_a_source_root_the_rule_says_nothing() -> None:
    assert place(file=parsed("/repo/src/app/infra/engine.py", None)) is None


def test_a_file_outside_the_source_root_says_nothing() -> None:
    assert place(file=parsed("/other/script.py", Path("/repo/src"))) is None


def test_a_file_lying_straight_in_the_source_root_says_nothing() -> None:
    assert place(file=parsed("/repo/src/manage.py", Path("/repo/src"))) is None
