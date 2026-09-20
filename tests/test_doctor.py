from typing import TYPE_CHECKING, ClassVar

import pytest
from typer.testing import CliRunner

from py_checks.cli import app
from py_checks.config import CheckSettings
from py_checks.core import Checks, Scope, Violation

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from py_checks.core import ParsedFile

runner = CliRunner()


class Zoned(CheckSettings):
    zones: tuple[str, ...] = ()


class StatementKeys:
    """Правило, которое работает не везде: у него есть `zones`."""

    code: ClassVar[str] = "statement-keys"
    Settings: ClassVar[type[CheckSettings]] = Zoned
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = "# db-ok"

    def run(self, *, file: ParsedFile, settings: CheckSettings) -> Iterator[Violation]:
        _ = file, settings
        return
        yield


class Limits(CheckSettings):
    max_lines: int = 50


class ModuleLength:
    """Правило, у которого умолчание рабочее: пустая секция ему не помеха."""

    code: ClassVar[str] = "module-length"
    Settings: ClassVar[type[CheckSettings]] = Limits
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = "# signature-ok"

    def run(self, *, file: ParsedFile, settings: CheckSettings) -> Iterator[Violation]:
        _ = file, settings
        return
        yield


class ClassModules:
    """Правило, читающее общую таблицу: его секция зовётся не как его код."""

    code: ClassVar[str] = "class-modules"
    Settings: ClassVar[type[CheckSettings]] = CheckSettings
    section: ClassVar[str] = "layout"
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = "# placement-ok"

    def run(self, *, file: ParsedFile, settings: CheckSettings) -> Iterator[Violation]:
        _ = file, settings
        return
        yield


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "src" / "app" / "infra" / "database").mkdir(parents=True)
    (tmp_path / "src" / "app" / "infra" / "database" / "repositories").mkdir()
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
def registry(monkeypatch: pytest.MonkeyPatch) -> None:
    checks = Checks(
        files={
            StatementKeys.code: StatementKeys(),
            ClassModules.code: ClassModules(),
            ModuleLength.code: ModuleLength(),
        },
        project={},
    )
    monkeypatch.setattr("py_checks.cli.commands._doctor.available", lambda: checks)
    monkeypatch.setattr("py_checks.core._registry.available", lambda: checks)


def settings(*, project: Path, written: str) -> None:
    (project / "py-checks.toml").write_text(written, encoding="utf-8")


def test_a_config_that_holds_together_says_so(project: Path) -> None:
    settings(
        project=project,
        written='src = "src"\n\n[statement-keys]\nzones = ["infra/database/repositories"]\n',
    )

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "ok: настройки согласованы" in result.output


def test_a_section_nobody_reads_is_named_with_its_neighbours(project: Path) -> None:
    settings(
        project=project,
        written='src = "src"\n\n[statement-key]\nzones = ["infra"]\n',
    )

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 1
    assert "[statement-key] — такой секции нет" in result.output
    assert "statement-keys" in result.output


def test_an_empty_section_without_defaults_is_a_rule_that_says_nothing(project: Path) -> None:
    settings(
        project=project,
        written='src = "src"\n\n[layout]\n',
    )

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 1
    assert "[layout] — секция пуста, а умолчаний у правила нет" in result.output


def test_an_empty_section_with_working_defaults_is_left_alone(project: Path) -> None:
    """Пустая секция у правила с рабочим умолчанием значит «работай как написано»."""
    settings(
        project=project,
        written='src = "src"\n\n[module-length]\n',
    )

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0


def test_a_rule_that_works_nowhere_is_a_rule_that_judges_nowhere(project: Path) -> None:
    settings(
        project=project,
        written='src = "src"\n\n[statement-keys]\nzones = []\n',
    )

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 1
    assert "[statement-keys] — зон не названо" in result.output


def test_an_address_without_a_directory_is_reported(project: Path) -> None:
    settings(
        project=project,
        written='src = "src"\n\n[layout."application/handlers"]\nonly = ["class"]\n',
    )

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 1
    assert "'application/handlers' не нашлось" in result.output


def test_a_key_that_is_not_an_address_is_left_alone(project: Path) -> None:
    """Ключ обычной секции — имя типа, а не путь: его на диске искать нечего."""
    settings(
        project=project,
        written=(
            'src = "src"\n\n[statement-keys]\nzones = ["infra/database/repositories"]\n\n'
            '[statement-keys.instead]\nFloat = "возьми Numeric"\n'
        ),
    )

    result = runner.invoke(app, ["doctor"])

    assert "не нашлось" not in result.output


def test_ignore_that_names_nothing_is_reported(project: Path) -> None:
    settings(
        project=project,
        written='src = "src"\nignore = ["statement-key"]\n',
    )

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 1
    assert "такого правила нет" in result.output
