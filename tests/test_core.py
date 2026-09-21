from pathlib import Path

import pytest

from py_checks.checks.api import Edges
from py_checks.config import CheckSettings, Config, ConfigError, find_root, load
from py_checks.core import ParsedFile, ParseError, Violation, python_files, report


def write(root: Path, name: str, text: str = "") -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_violation_renders_relative_to_root(tmp_path: Path) -> None:
    violation = Violation(
        path=tmp_path / "src" / "a.py",
        line=3,
        column=5,
        code="module-length",
        message="слишком длинно",
    )

    assert violation.render(root=tmp_path) == "src/a.py:3:5: module-length: слишком длинно"


def test_violation_from_node_shifts_column_to_one_based(tmp_path: Path) -> None:
    file = ParsedFile(path=tmp_path / "a.py", text="x = 1\n")
    node = file.tree.body[0]

    violation = Violation.from_node(node=node, path=file.path, code="c", message="m")

    assert (violation.line, violation.column) == (1, 1)


def test_parsed_file_parses_once(tmp_path: Path) -> None:
    file = ParsedFile(path=tmp_path / "a.py", text="x = 1\n")

    assert file.tree is file.tree
    assert file.lines == ("x = 1",)


def test_parsed_file_reports_broken_syntax(tmp_path: Path) -> None:
    file = ParsedFile(path=tmp_path / "a.py", text="def (:\n")

    with pytest.raises(ParseError):
        _ = file.tree


def test_python_files_walks_directories_and_skips_excluded(tmp_path: Path) -> None:
    write(tmp_path, "src/a.py")
    write(tmp_path, "src/nested/b.py")
    write(tmp_path, "src/nested/notes.txt")
    write(tmp_path, ".venv/c.py")

    found = python_files(
        paths=[],
        root=tmp_path,
        default=tmp_path,
        exclude=(".venv/*",),
    )

    assert [path.relative_to(tmp_path).as_posix() for path in found] == [
        "src/a.py",
        "src/nested/b.py",
    ]


def test_python_files_takes_explicit_paths(tmp_path: Path) -> None:
    first = write(tmp_path, "src/a.py")
    write(tmp_path, "src/b.py")

    assert python_files(paths=[first], root=tmp_path, default=tmp_path) == [first]


def test_report_exit_codes(tmp_path: Path) -> None:
    violation = Violation(path=tmp_path / "a.py", line=1, column=1, code="c", message="m")

    assert report(violations=[], root=tmp_path, checked=1) == 0
    assert report(violations=[violation], root=tmp_path, checked=1) == 1


class Limits(CheckSettings):
    max_lines: int = 200


def test_config_reads_own_keys_and_check_sections(tmp_path: Path) -> None:
    write(
        tmp_path,
        "pyproject.toml",
        """
        [tool.py-checks]
        src = "app"
        ignore = ["module-length"]

        [tool.py-checks.module-length]
        max-lines = 120
        """.replace("        ", ""),
    )

    config = load(root=tmp_path)

    assert config.src == Path("app")
    assert config.enabled(code="module-length") is False
    assert config.settings_for(code="module-length", model=Limits) == Limits(max_lines=120)


def test_config_defaults_when_section_is_missing(tmp_path: Path) -> None:
    write(tmp_path, "pyproject.toml", "[project]\nname = 'x'\n")

    config = load(root=tmp_path)

    assert config == Config()
    assert config.settings_for(code="module-length", model=Limits) == Limits()


def test_config_rejects_unknown_key(tmp_path: Path) -> None:
    write(
        tmp_path,
        "pyproject.toml",
        "[tool.py-checks.module-length]\nmax-linez = 10\n",
    )

    with pytest.raises(ConfigError):
        load(root=tmp_path).settings_for(code="module-length", model=Limits)


def test_config_is_read_from_a_file_of_its_own(tmp_path: Path) -> None:
    write(
        tmp_path,
        "pychecks.toml",
        'src = "app"\n\n[module-length]\nmax-lines = 120\n',
    )

    config = load(root=tmp_path)

    assert config.src == Path("app")
    assert config.settings_for(code="module-length", model=Limits) == Limits(max_lines=120)


def test_a_file_of_its_own_names_the_root(tmp_path: Path) -> None:
    write(tmp_path, ".py-checks.toml", "")
    nested = tmp_path / "src" / "deep"
    nested.mkdir(parents=True)

    assert find_root(start=nested) == tmp_path


def test_a_pyproject_without_the_section_is_not_a_second_place(tmp_path: Path) -> None:
    write(tmp_path, "pyproject.toml", "[project]\nname = 'x'\n")
    write(tmp_path, "pychecks.toml", 'src = "app"\n')

    assert load(root=tmp_path).src == Path("app")


def test_settings_in_two_places_are_an_error(tmp_path: Path) -> None:
    write(tmp_path, "pyproject.toml", '[tool.py-checks]\nsrc = "app"\n')
    write(tmp_path, "pychecks.toml", 'src = "lib"\n')

    with pytest.raises(ConfigError, match="нескольких местах"):
        load(root=tmp_path)


def test_the_error_names_the_section_as_the_file_spells_it(tmp_path: Path) -> None:
    write(tmp_path, "pychecks.toml", "[module-length]\nmax-linez = 10\n")

    with pytest.raises(ConfigError, match=r"^\[module-length\]"):
        load(root=tmp_path).settings_for(code="module-length", model=Limits)


def test_find_root_walks_up(tmp_path: Path) -> None:
    write(tmp_path, "pyproject.toml", "")
    nested = tmp_path / "src" / "deep"
    nested.mkdir(parents=True)

    assert find_root(start=nested) == tmp_path


def test_config_keeps_nested_check_sections_typed(tmp_path: Path) -> None:
    write(
        tmp_path,
        "pyproject.toml",
        "[tool.py-checks.module-length]\nmax-lines = 120\n",
    )

    section = load(root=tmp_path).section(code="module-length")

    assert section == {"max-lines": 120}
    assert load(root=tmp_path).section(code="missing") == {}


def test_extend_exclude_adds_to_the_defaults(tmp_path: Path) -> None:
    write(
        tmp_path,
        "pyproject.toml",
        '[tool.py-checks]\nextend-exclude = ["tests/checks/*"]\n',
    )

    config = load(root=tmp_path)

    assert config.excluded == (*config.exclude, "tests/checks/*")


def test_a_retired_section_names_the_table_it_moved_into(tmp_path: Path) -> None:
    write(tmp_path, "pychecks.toml", "[endpoint-declarations]\nrequired = []\n")

    with pytest.raises(ConfigError, match=r"\[edge-declarations\]"):
        load(root=tmp_path)


def test_a_block_named_after_an_unknown_framework_is_refused(tmp_path: Path) -> None:
    write(tmp_path, "pychecks.toml", '[edge-declarations.litestar]\nrequired = ["path"]\n')

    with pytest.raises(ConfigError, match="про такой фреймворк правило не знает"):
        load(root=tmp_path).settings_for(code="edge-declarations", model=Edges)
