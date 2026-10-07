"""Переводы: штамп, команда, мёртвые шаблоны и проект без git."""

from __future__ import annotations

import hashlib
import subprocess
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from py_checks.checks.hygiene import Translations
from py_checks.cli import app
from py_checks.translations import TranslationError, TranslationsSettings, dead, stamp, stamped

pytestmark = pytest.mark.usefixtures("own_repository")

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()

CONFIG = '[tool.py-checks.translations]\nlangs = ["ru"]\nfiles = {files}\n'


def project(root: Path, files: str = '["*.md"]') -> Path:
    """Репозиторий с документом и его ещё не проштампованным переводом."""
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)  # noqa: S607
    (root / "pyproject.toml").write_text(CONFIG.format(files=files), encoding="utf-8")
    (root / "README.md").write_text("# Service\n", encoding="utf-8")
    translated = root / "docs" / "langs" / "ru" / "README.md"
    translated.parent.mkdir(parents=True)
    translated.write_text("# Сервис\n", encoding="utf-8")
    return root


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_stamp_puts_the_source_fingerprint_on_the_first_line(tmp_path: Path) -> None:
    root = project(tmp_path)

    stamp(root=root, translation="docs/langs/ru/README.md")

    text = (root / "docs/langs/ru/README.md").read_text(encoding="utf-8")
    assert text == f"<!-- sha256:{sha(root / 'README.md')} -->\n# Сервис\n"


def test_a_second_stamp_replaces_the_fingerprint_rather_than_adding_one(tmp_path: Path) -> None:
    root = project(tmp_path)
    stamp(root=root, translation="docs/langs/ru/README.md")
    (root / "README.md").write_text("# Service, edited\n", encoding="utf-8")

    stamp(root=root, translation="docs/langs/ru/README.md")

    path = root / "docs/langs/ru/README.md"
    assert stamped(path=path) == sha(root / "README.md")
    assert path.read_text(encoding="utf-8").count("sha256") == 1


@pytest.mark.parametrize(
    ("translation", "said"),
    [
        ("README.md", "is not a translation"),
        ("docs/langs/ru/missing.md", "does not exist"),
    ],
)
def test_stamp_refuses_what_it_cannot_stamp(tmp_path: Path, translation: str, said: str) -> None:
    root = project(tmp_path)

    with pytest.raises(TranslationError, match=said):
        stamp(root=root, translation=translation)


def test_stamp_refuses_a_translation_of_nothing(tmp_path: Path) -> None:
    root = project(tmp_path)
    (root / "docs/langs/ru/old.md").write_text("# Старое\n", encoding="utf-8")

    with pytest.raises(TranslationError, match="translates nothing"):
        stamp(root=root, translation="docs/langs/ru/old.md")


def test_the_command_stamps_and_the_check_falls_silent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = project(tmp_path)
    monkeypatch.chdir(root)
    before = runner.invoke(app, ["run", "--select", "translations"])

    result = runner.invoke(app, ["translations", "stamp", "docs/langs/ru/README.md"])

    assert before.exit_code == 1
    assert result.exit_code == 0
    assert "stamped docs/langs/ru/README.md" in result.output
    assert runner.invoke(app, ["run", "--select", "translations"]).exit_code == 0


def test_the_command_says_what_it_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(project(tmp_path))

    result = runner.invoke(app, ["translations", "stamp", "docs/langs/ru/missing.md"])

    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_a_symlink_is_not_a_document_of_its_own(tmp_path: Path) -> None:
    """`CLAUDE.md` -> `AGENTS.md`: переводят один раз, как `AGENTS.md`."""
    root = project(tmp_path)
    stamp(root=root, translation="docs/langs/ru/README.md")
    (root / "CLAUDE.md").symlink_to("README.md")
    settings = TranslationsSettings(langs=("ru",), files=("*.md",))

    assert list(Translations.run(root=root, settings=settings)) == []


def test_a_directory_excluded_without_its_files_is_a_dead_pattern() -> None:
    """`!.github/` выносит директорию, а не файлы: `*.md` всё равно их берёт."""
    paths = ["README.md", ".github/PULL_REQUEST_TEMPLATE.md"]

    assert dead(paths=paths, files=("*.md", "!.github/")) == ["!.github/"]
    assert dead(paths=paths, files=("*.md", "!.github/**")) == []


def test_outside_git_the_check_says_so_instead_of_guessing(tmp_path: Path) -> None:
    settings = TranslationsSettings(langs=("ru",), files=("*.md",))

    found = list(Translations.run(root=tmp_path, settings=settings))

    assert len(found) == 1
    assert "not a git repository" in found[0].message


def test_doctor_names_a_pattern_that_changes_nothing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = project(tmp_path, files='["*.md", "!.github/"]')
    (root / ".github").mkdir()
    (root / ".github" / "PULL_REQUEST_TEMPLATE.md").write_text("Describe.\n", encoding="utf-8")
    monkeypatch.chdir(root)

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 1
    assert "'!.github/' selects or excludes no file" in result.output
