from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from python_checks.config import Config, ConfigError
from python_checks.contracts import BASE, layers, render

if TYPE_CHECKING:
    from pathlib import Path


def layout(root: Path, *paths: str) -> Path:
    """Разложить пакеты: каждая папка пути — пакет, как в настоящем проекте."""
    for path in paths:
        directory = root / path
        directory.mkdir(parents=True, exist_ok=True)
        while directory != root / "src":
            (directory / "__init__.py").touch()
            directory = directory.parent
    return root


def test_layers_come_from_the_library_when_the_project_says_nothing() -> None:
    assert layers(config=Config()) == BASE


def test_a_project_adds_its_own_layer_and_rewrites_a_known_one() -> None:
    config = Config(
        checks={
            "layers": {
                "workflows": ["domain", "application", "workflows", "shared"],
                "presentation": ["application", "workflows", "shared"],
            },
        },
    )

    table = layers(config=config)

    assert table["workflows"] == frozenset({"domain", "application", "workflows", "shared"})
    assert table["presentation"] == frozenset({"application", "workflows", "shared"})
    assert table["domain"] == BASE["domain"]


def test_a_layer_written_as_something_else_is_refused() -> None:
    config = Config(checks={"layers": {"domain": "shared"}})

    with pytest.raises(ConfigError):
        layers(config=config)


def test_contracts_name_the_layers_the_project_actually_has(tmp_path: Path) -> None:
    layout(tmp_path, "src/app/infra", "src/app/shared", "src/app/modules/chat/domain")

    text = render(root=tmp_path, config=Config()) or ""

    assert "app.infra" in text
    assert "app.modules.*.domain" in text
    # Слоя нет на диске: контракт про него сломал бы весь прогон import-linter.
    assert "app.presentation" not in text


def test_modules_get_an_independence_contract(tmp_path: Path) -> None:
    layout(tmp_path, "src/app/infra", "src/app/shared", "src/app/modules/chat/domain")

    text = render(root=tmp_path, config=Config()) or ""

    assert "type = independence" in text
    assert "app.modules.*" in text


def test_only_the_history_of_migrations_is_checked(tmp_path: Path) -> None:
    layout(tmp_path, "src/app/infra", "src/app/shared")
    (tmp_path / "migrations" / "versions").mkdir(parents=True)

    text = render(root=tmp_path, config=Config()) or ""

    assert "source_modules = migrations.versions" in text


def test_a_layout_without_layers_gets_no_contracts(tmp_path: Path) -> None:
    layout(tmp_path, "src/app/core", "src/app/cli")

    assert render(root=tmp_path, config=Config()) is None


def test_two_packages_in_src_are_not_guessed_at(tmp_path: Path) -> None:
    layout(tmp_path, "src/app/domain", "src/other/domain")

    assert render(root=tmp_path, config=Config()) is None
