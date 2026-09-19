from __future__ import annotations

from pathlib import Path

import pytest

from py_checks.config import Config, ConfigError, TomlTable, load
from py_checks.contracts import contracts, render

SERVICE: dict[str, TomlTable] = {
    "contracts": {
        "composition-root": ["ioc"],
        "layers": {
            "domain": ["domain", "shared"],
            "application": ["domain", "application", "shared"],
            "infra": ["domain", "application", "infra", "shared"],
            "shared": ["shared"],
        },
    },
}


def layout(root: Path, *paths: str) -> Path:
    """Разложить пакеты: каждая папка пути — пакет, как в настоящем проекте."""
    for path in paths:
        directory = root / path
        directory.mkdir(parents=True, exist_ok=True)
        while directory != root / "src":
            (directory / "__init__.py").touch()
            directory = directory.parent
    return root


def test_a_project_that_declared_nothing_gets_no_contracts(tmp_path: Path) -> None:
    """Имена слоёв придумывает проект; библиотека за него не догадывается."""
    layout(tmp_path, "src/app/domain", "src/app/infra")

    assert render(root=tmp_path, config=Config()) is None


def test_layers_are_read_from_the_project_section() -> None:
    declared = contracts(config=Config(checks=SERVICE))

    assert declared.layers["domain"] == ("domain", "shared")
    assert declared.composition_root == ("ioc",)


def test_a_layer_written_as_something_else_is_refused() -> None:
    config = Config(checks={"contracts": {"layers": {"domain": "shared"}}})

    with pytest.raises(ConfigError):
        contracts(config=config)


def test_an_unknown_key_in_the_section_is_refused() -> None:
    config = Config(checks={"contracts": {"layerz": {}}})

    with pytest.raises(ConfigError):
        contracts(config=config)


def test_contracts_name_the_layers_the_project_actually_has(tmp_path: Path) -> None:
    layout(tmp_path, "src/app/infra", "src/app/shared", "src/app/modules/chat/domain")

    text = render(root=tmp_path, config=Config(checks=SERVICE)) or ""

    assert "app.infra" in text
    assert "app.modules.*.domain" in text
    # Слоя нет на диске: контракт про него сломал бы весь прогон import-linter.
    assert "app.presentation" not in text


def test_the_composition_root_becomes_a_forbidden_target(tmp_path: Path) -> None:
    """Слой, о котором таблица не знает, ничьим запретом не станет."""
    layout(tmp_path, "src/app/domain", "src/app/ioc")

    text = render(root=tmp_path, config=Config(checks=SERVICE)) or ""

    assert "app.ioc" in text


def test_modules_get_an_independence_contract(tmp_path: Path) -> None:
    layout(tmp_path, "src/app/infra", "src/app/shared", "src/app/modules/chat/domain")

    text = render(root=tmp_path, config=Config(checks=SERVICE)) or ""

    assert "type = independence" in text
    assert "app.modules.*" in text


def test_only_the_history_of_migrations_is_checked(tmp_path: Path) -> None:
    layout(tmp_path, "src/app/infra", "src/app/shared")
    (tmp_path / "migrations" / "versions").mkdir(parents=True)

    text = render(root=tmp_path, config=Config(checks=SERVICE)) or ""

    assert "source_modules =\n    migrations.versions" in text


def test_a_single_value_still_stands_in_a_column(tmp_path: Path) -> None:
    """import-linter разбирает поле-список, написанное в строку, посимвольно."""
    layout(tmp_path, "src/app/infra", "src/app/shared")

    text = render(root=tmp_path, config=Config(checks=SERVICE)) or ""

    assert "root_packages =\n    app\n" in text


def test_two_packages_in_src_are_not_guessed_at(tmp_path: Path) -> None:
    layout(tmp_path, "src/app/domain", "src/other/domain")

    assert render(root=tmp_path, config=Config(checks=SERVICE)) is None


def test_the_library_checks_its_own_layers() -> None:
    """Секция в pyproject этого репозитория — сам себе проект."""
    root = Path(__file__).resolve().parent.parent

    text = render(root=root, config=load(root=root)) or ""

    assert "[importlinter:contract:layer-core]" in text
    assert "py_checks.cli" in text
