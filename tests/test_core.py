from pathlib import Path

import pytest

from python_checks.config import CheckSettings, Config, ConfigError, find_root, load
from python_checks.core import ParsedFile, ParseError, Violation, python_files, report


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
        [tool.python-checks]
        src = "app"
        ignore = ["module-length"]

        [tool.python-checks.module-length]
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
        "[tool.python-checks.module-length]\nmax-linez = 10\n",
    )

    with pytest.raises(ConfigError):
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
        "[tool.python-checks.module-length]\nmax-lines = 120\n",
    )

    section = load(root=tmp_path).section(code="module-length")

    assert section == {"max-lines": 120}
    assert load(root=tmp_path).section(code="missing") == {}


def test_extend_exclude_adds_to_the_defaults(tmp_path: Path) -> None:
    write(
        tmp_path,
        "pyproject.toml",
        '[tool.python-checks]\nextend-exclude = ["tests/checks/*"]\n',
    )

    config = load(root=tmp_path)

    assert config.excluded == (*config.exclude, "tests/checks/*")
