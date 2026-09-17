from pathlib import Path

import pytest

from python_checks.core import Edit, ParsedFile, ParseError, Violation, apply, fix


def edit(*, line: int, column: int, text: str, end_column: int | None = None) -> Edit:
    return Edit(
        line=line,
        column=column,
        end_line=line,
        end_column=end_column if end_column is not None else column,
        text=text,
    )


def test_insertion_leaves_the_rest_of_the_line_alone() -> None:
    text = "def f(a: int) -> None: ...\n"

    assert apply(text=text, edits=[edit(line=1, column=7, text="*, ")]) == (
        "def f(*, a: int) -> None: ...\n"
    )


def test_edits_are_applied_from_the_end_of_the_file() -> None:
    text = "def f(a):\n    pass\n\n\ndef g(b):\n    pass\n"

    fixed = apply(
        text=text,
        edits=[edit(line=1, column=7, text="*, "), edit(line=5, column=7, text="*, ")],
    )

    assert fixed == "def f(*, a):\n    pass\n\n\ndef g(*, b):\n    pass\n"


def test_an_edit_over_an_applied_one_is_skipped() -> None:
    """Правки идут с конца, поэтому первой ложится правая, а левая её не трогает."""
    text = "value = 1\n"

    fixed = apply(
        text=text,
        edits=[
            edit(line=1, column=1, text="other", end_column=6),
            edit(line=1, column=4, text="!", end_column=5),
        ],
    )

    assert fixed == "val!e = 1\n"


def test_fix_rewrites_the_file_and_keeps_what_it_cannot_fix(tmp_path: Path) -> None:
    path = tmp_path / "a.py"
    path.write_text("def f(a):\n    pass\n", encoding="utf-8")
    fixable = Violation(
        path=path,
        line=1,
        column=1,
        code="keyword-only-arguments",
        message="m",
        edit=edit(line=1, column=7, text="*, "),
    )
    stubborn = Violation(path=path, line=1, column=1, code="other", message="m")

    changed, left = fix(violations=[fixable, stubborn])

    assert changed == [path]
    assert left == [stubborn]
    assert path.read_text(encoding="utf-8") == "def f(*, a):\n    pass\n"


def test_cst_module_keeps_comments_and_is_parsed_once() -> None:
    file = ParsedFile(path=Path("a.py"), text="x = 1  # почему\n")

    assert file.module is file.module
    assert file.module.code == "x = 1  # почему\n"


def test_cst_module_reports_broken_syntax() -> None:
    file = ParsedFile(path=Path("a.py"), text="def (:\n")

    with pytest.raises(ParseError):
        _ = file.module
