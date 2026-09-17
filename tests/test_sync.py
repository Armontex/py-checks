from __future__ import annotations

from typing import TYPE_CHECKING

from python_checks.sync import DIRECTORY, MANAGED, canonical, leftovers, stale, write

if TYPE_CHECKING:
    from pathlib import Path


def project(tmp_path: Path, pyproject: str = "[project]\nname = 'demo'\n") -> Path:
    (tmp_path / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    return tmp_path


def test_sync_lays_out_the_copies_and_the_project_files(tmp_path: Path) -> None:
    root = project(tmp_path)

    write(root=root)

    for managed in MANAGED:
        assert (root / DIRECTORY / managed.name).read_text(encoding="utf-8") == canonical(
            name=managed.name,
        )
        assert (root / managed.project).is_file()


def test_the_project_file_is_written_once_and_left_alone(tmp_path: Path) -> None:
    root = project(tmp_path)
    own = root / MANAGED[0].project
    own.write_text("extend = '.python-checks/ruff.toml'\n# моё\n", encoding="utf-8")

    write(root=root)

    assert own.read_text(encoding="utf-8").endswith("# моё\n")


def test_a_copy_edited_by_hand_is_stale(tmp_path: Path) -> None:
    root = project(tmp_path)
    write(root=root)
    copy = root / DIRECTORY / MANAGED[0].name
    copy.write_text(
        copy.read_text(encoding="utf-8") + '\n[lint]\nselect = ["E"]\n', encoding="utf-8"
    )

    assert stale(root=root) == [copy]


def test_a_missing_copy_is_stale(tmp_path: Path) -> None:
    root = project(tmp_path)

    assert stale(root=root) == [root / DIRECTORY / managed.name for managed in MANAGED]


def test_sync_puts_everything_back(tmp_path: Path) -> None:
    root = project(tmp_path)
    write(root=root)
    (root / DIRECTORY / MANAGED[0].name).unlink()

    write(root=root)

    assert stale(root=root) == []


def test_a_section_left_in_pyproject_is_reported(tmp_path: Path) -> None:
    root = project(tmp_path, "[tool.ruff]\nline-length = 88\n")
    write(root=root)

    assert leftovers(root=root) == ["tool.ruff"]


def test_a_section_without_its_own_file_is_still_read(tmp_path: Path) -> None:
    root = project(tmp_path, "[tool.ruff]\nline-length = 88\n")

    assert leftovers(root=root) == []
