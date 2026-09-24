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


def zoned_in(path: str, zone: str) -> bool:
    where = place(file=parsed(f"/repo/src/app/{path}", Path("/repo/src")))
    assert where is not None
    return where.inside(zones=[zone])


def test_a_zone_is_a_directory_not_a_module_of_the_same_name() -> None:
    """В player-tenant зона `domain` судила `application/exceptions/domain.py`."""
    assert zoned_in("domain/order.py", "domain")
    assert zoned_in("domain/values/money.py", "domain")
    assert zoned_in("domain/__init__.py", "domain")
    assert not zoned_in("application/exceptions/domain.py", "domain")
    assert not zoned_in("infra/database/models.py", "infra/database/models")


def test_a_star_takes_the_module_as_well() -> None:
    """`domain/*` — всё, что в `domain/`, и файл прямо в нём тоже."""
    assert zoned_in("domain/exceptions.py", "domain/*")
    assert zoned_in("domain/entities/order.py", "domain/*")
    assert not zoned_in("application/exceptions/domain.py", "domain/*")


def test_an_address_still_names_a_module() -> None:
    """`declared-in = "shared/money"` — это модуль, и адрес его находит."""
    where = place(file=parsed("/repo/src/app/shared/money.py", Path("/repo/src")))

    assert where is not None
    assert where.anywhere(zones=["shared/money"])
