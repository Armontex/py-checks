from pathlib import Path

from python_checks.core import MARKER, ParsedFile, Violation, complaints, read, surviving

ALIASES = {"# signature-ok": "keyword-only-arguments"}


def parsed(text: str) -> ParsedFile:
    return ParsedFile(path=Path("a.py"), text=text)


def violation(*, line: int, end_line: int | None = None, code: str = "keyword-only-arguments"):
    return Violation(
        path=Path("a.py"),
        line=line,
        column=1,
        code=code,
        message="m",
        end_line=end_line,
    )


def test_marker_reads_codes_and_reason() -> None:
    marker = read(line=f"def f(a): ...  {MARKER} a-rule, b-rule: так зовёт библиотека", aliases={})

    assert marker is not None
    assert marker.codes == {"a-rule", "b-rule"}
    assert marker.reason == "так зовёт библиотека"


def test_old_word_of_a_check_still_works() -> None:
    marker = read(line="def f(a): ...  # signature-ok: sqlalchemy", aliases=ALIASES)

    assert marker is not None
    assert marker.codes == {"keyword-only-arguments"}
    assert marker.reason == "sqlalchemy"


def test_a_line_without_a_marker_is_none() -> None:
    assert read(line="def f(a): ...  # просто комментарий", aliases=ALIASES) is None


def test_marker_removes_the_violation_it_names() -> None:
    file = parsed(f"def f(a): ...  {MARKER} keyword-only-arguments: причина\n")

    assert surviving(violations=[violation(line=1)], file=file, aliases={}) == []


def test_marker_of_another_check_leaves_the_violation() -> None:
    file = parsed(f"def f(a): ...  {MARKER} module-length: причина\n")

    assert surviving(violations=[violation(line=1)], file=file, aliases={}) != []


def test_marker_is_looked_for_in_the_whole_span() -> None:
    file = parsed(
        "def f(\n    a: int,\n) -> None:  # check-ok: keyword-only-arguments: причина\n    ...\n",
    )

    assert surviving(violations=[violation(line=1, end_line=3)], file=file, aliases={}) == []


def test_marker_without_a_code_is_a_violation() -> None:
    file = parsed(f"x = 1  {MARKER}\n")

    found = list(complaints(file=file, aliases={}, known=["module-length"]))

    assert [v.code for v in found] == ["check-ok", "check-ok"]
    assert "нужен код проверки" in found[0].message


def test_marker_with_an_unknown_code_is_a_violation() -> None:
    file = parsed(f"x = 1  {MARKER} module-lenght: опечатка\n")

    found = list(complaints(file=file, aliases={}, known=["module-length"]))

    assert "нет проверки `module-lenght`" in found[0].message


def test_marker_without_a_reason_is_a_violation() -> None:
    file = parsed(f"x = 1  {MARKER} module-length\n")

    found = list(complaints(file=file, aliases={}, known=["module-length"]))

    assert "нужна причина" in found[0].message


def test_the_shape_written_in_a_docstring_is_not_a_marker() -> None:
    assert read(line=f"Пишется так: `{MARKER} <код>: <причина>`", aliases={}) is None
