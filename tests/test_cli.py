from typing import TYPE_CHECKING, ClassVar

import pytest
from typer.testing import CliRunner

from python_checks.cli import app
from python_checks.config import CheckSettings
from python_checks.core import Checks, Scope, Violation

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from python_checks.core import ParsedFile

runner = CliRunner()


class Limits(CheckSettings):
    max_lines: int = 2


class ModuleLength:
    """Падает, если модуль длиннее лимита.

    Лимит задаётся настройкой `max-lines`.
    """

    code: ClassVar[str] = "module-length"
    Settings: ClassVar[type[CheckSettings]] = Limits
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = "# signature-ok"

    def run(self, *, file: ParsedFile, settings: CheckSettings) -> Iterator[Violation]:
        assert isinstance(settings, Limits)
        if len(file.lines) > settings.max_lines:
            yield Violation(
                path=file.path,
                line=settings.max_lines + 1,
                column=1,
                code=self.code,
                message=f"{len(file.lines)} строк, предел {settings.max_lines}",
            )


class NeedsTree:
    """Проверка, которой нужно дерево: на ней видно поведение на сломанном файле."""

    code: ClassVar[str] = "needs-tree"
    Settings: ClassVar[type[CheckSettings]] = CheckSettings
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = "# tree-ok"

    def run(self, *, file: ParsedFile, settings: CheckSettings) -> Iterator[Violation]:
        _ = settings
        for _node in file.tree.body:
            pass
        return
        yield


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
def registry(monkeypatch: pytest.MonkeyPatch) -> None:
    checks = Checks(files={ModuleLength.code: ModuleLength()}, project={})
    for module in ("_run", "_list"):
        monkeypatch.setattr(f"python_checks.cli.commands.{module}.available", lambda: checks)
    monkeypatch.setattr("python_checks.core._registry.available", lambda: checks)


def test_run_is_clean_when_nothing_is_wrong(project: Path) -> None:
    (project / "src" / "short.py").write_text("x = 1\n", encoding="utf-8")

    result = runner.invoke(app, ["run"])

    assert result.exit_code == 0


def test_run_reports_the_violation_and_fails(project: Path) -> None:
    (project / "src" / "long.py").write_text("x = 1\n" * 5, encoding="utf-8")

    result = runner.invoke(app, ["run"])

    assert result.exit_code == 1
    assert "src/long.py:3:1: module-length: 5 строк, предел 2" in result.output


def test_run_takes_settings_from_pyproject(project: Path) -> None:
    (project / "pyproject.toml").write_text(
        "[tool.python-checks.module-length]\nmax-lines = 10\n",
        encoding="utf-8",
    )
    (project / "src" / "long.py").write_text("x = 1\n" * 5, encoding="utf-8")

    assert runner.invoke(app, ["run"]).exit_code == 0


def test_run_skips_a_check_the_config_ignores(project: Path) -> None:
    (project / "pyproject.toml").write_text(
        "[tool.python-checks]\nignore = ['module-length']\n",
        encoding="utf-8",
    )
    (project / "src" / "long.py").write_text("x = 1\n" * 5, encoding="utf-8")

    assert runner.invoke(app, ["run"]).exit_code == 0


def test_select_wins_over_ignore(project: Path) -> None:
    (project / "pyproject.toml").write_text(
        "[tool.python-checks]\nignore = ['module-length']\n",
        encoding="utf-8",
    )
    (project / "src" / "long.py").write_text("x = 1\n" * 5, encoding="utf-8")

    assert runner.invoke(app, ["run", "--select", "module-length"]).exit_code == 1


def test_run_takes_explicit_paths(project: Path) -> None:
    (project / "src" / "long.py").write_text("x = 1\n" * 5, encoding="utf-8")
    picked = project / "src" / "short.py"
    picked.write_text("x = 1\n", encoding="utf-8")

    assert runner.invoke(app, ["run", str(picked)]).exit_code == 0


def test_broken_syntax_is_one_violation_not_a_crash(
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "python_checks.cli.commands._run.available",
        lambda: Checks(files={NeedsTree.code: NeedsTree()}, project={}),
    )
    (project / "src" / "broken.py").write_text("def (:\n", encoding="utf-8")

    result = runner.invoke(app, ["run"])

    assert result.exit_code == 1
    assert "syntax:" in result.output


@pytest.mark.usefixtures("project")
def test_unknown_check_is_named_with_the_known_ones() -> None:
    result = runner.invoke(app, ["run", "--select", "nope"])

    assert result.exit_code != 0
    assert "module-length" in str(result.exception)


@pytest.mark.usefixtures("project")
def test_list_shows_the_check_and_its_state() -> None:
    result = runner.invoke(app, ["list"])

    assert "module-length" in result.output
    assert "вкл" in result.output


@pytest.mark.usefixtures("project")
def test_explain_shows_the_rule_and_its_settings() -> None:
    result = runner.invoke(app, ["explain", "module-length"])

    assert "Лимит задаётся настройкой" in result.output
    assert "max-lines = 2" in result.output
