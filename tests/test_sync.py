from __future__ import annotations

from typing import TYPE_CHECKING

from py_checks.contracts import FILE
from py_checks.sync import planned, stale, write

if TYPE_CHECKING:
    from pathlib import Path


def project(root: Path, section: str = "") -> Path:
    (root / "pyproject.toml").write_text(f"[project]\nname = 'demo'\n{section}", encoding="utf-8")
    for path in ("src/app/domain", "src/app/shared"):
        directory = root / path
        directory.mkdir(parents=True, exist_ok=True)
        while directory != root / "src":
            (directory / "__init__.py").touch()
            directory = directory.parent
    return root


SECTION = """
[tool.py-checks.contracts.layers]
domain = ["domain", "shared"]
shared = ["shared"]
"""


def test_contracts_land_in_the_root_where_import_linter_looks(tmp_path: Path) -> None:
    root = project(tmp_path, SECTION)

    assert write(root=root) == [root / FILE]
    assert (root / FILE).is_file()


def test_a_project_without_layers_gets_no_file(tmp_path: Path) -> None:
    root = project(tmp_path)

    assert planned(root=root) == {}
    assert write(root=root) == []


def test_a_file_that_fell_behind_the_settings_is_stale(tmp_path: Path) -> None:
    root = project(tmp_path, SECTION)
    write(root=root)
    (root / FILE).write_text("[importlinter]\nroot_packages =\n    app\n", encoding="utf-8")

    assert stale(root=root) == [root / FILE]


def test_a_missing_file_is_stale(tmp_path: Path) -> None:
    root = project(tmp_path, SECTION)

    assert stale(root=root) == [root / FILE]


def test_sync_puts_it_back(tmp_path: Path) -> None:
    root = project(tmp_path, SECTION)
    write(root=root)
    (root / FILE).unlink()

    write(root=root)

    assert stale(root=root) == []
