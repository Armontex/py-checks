"""`--fix` у keyword-only-arguments: подпись меняется вместе со всеми вызовами — или никак."""

import subprocess
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from py_checks.checks.signatures._callers import _environment  # pyright: ignore[reportPrivateUsage]
from py_checks.cli import app

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.usefixtures("own_repository")

runner = CliRunner()

# Порт и его реализация в одном модуле: обе подписи `get` меняются вместе.
BOTH = 2

PORT = """\
from typing import Protocol


class Repo:
    def get(self, key):
        return key


class RepoPort(Protocol):
    def get(self, key): ...


def price(market, stake=1):
    return market
"""


BOX = "class Box:\n    def __init__(self, value):\n        self.value = value\n"


def fixed(*, root: Path, files: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> str:
    """Проект из файлов, `run --fix` по правилу; вывод — то, что осталось."""
    (root / "pyproject.toml").write_text('[tool.py-checks]\nsrc = "src"\n', encoding="utf-8")
    for name, text in {"src/app/__init__.py": "", **files}.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    monkeypatch.chdir(root)
    return runner.invoke(app, ["run", "--fix", "-s", "keyword-only-arguments"]).output


def read(root: Path, name: str) -> str:
    return (root / name).read_text(encoding="utf-8")


def test_a_function_and_every_positional_call_change_together(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Импорт, алиас модуля, `as`, тесты: всё, что звало по позиции, теперь зовёт по имени."""
    fixed(
        root=tmp_path,
        files={
            "src/app/a.py": PORT,
            "src/app/b.py": (
                "import app.a as m\nfrom app.a import price\nfrom app.a import price as quote\n\n"
                "x = price(1)\ny = m.price(2, 3)\nz = quote(4)\nw = price(market=5)\n"
            ),
            "tests/test_b.py": "from app.a import price\n\n\ndef test_it():\n    assert price(7)\n",
        },
        monkeypatch=monkeypatch,
    )

    assert "def price(*, market, stake=1):" in read(tmp_path, "src/app/a.py")
    assert read(tmp_path, "src/app/b.py").endswith(
        "x = price(market=1)\ny = m.price(market=2, stake=3)\nz = quote(market=4)\n"
        "w = price(market=5)\n"
    )
    assert "assert price(market=7)" in read(tmp_path, "tests/test_b.py")


def test_a_port_and_its_implementation_change_together(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Вызов через порт jedi приписывает порту: меняются оба, иначе разойдутся."""
    fixed(
        root=tmp_path,
        files={
            "src/app/a.py": PORT,
            "src/app/b.py": (
                "from app.a import Repo, RepoPort\n\n\n"
                "def through(repo: RepoPort):\n    return repo.get(1)\n\n\n"
                "def direct():\n    return Repo().get(2)\n\n\n"
                'cache = {}.get("k")\n'
            ),
        },
        monkeypatch=monkeypatch,
    )

    assert read(tmp_path, "src/app/a.py").count("def get(self, *, key)") == BOTH
    fixed_b = read(tmp_path, "src/app/b.py")
    assert "repo.get(key=1)" in fixed_b
    assert "Repo().get(key=2)" in fixed_b
    assert '{}.get("k")' in fixed_b


def test_a_test_double_of_the_port_follows_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Двойник в тестах правило не судит, но и бросить его нельзя: он подставляется вместо порта."""
    fixed(
        root=tmp_path,
        files={
            "src/app/a.py": PORT,
            "tests/test_b.py": (
                "class FakeRepo:\n    def get(self, key):\n        return key\n\n\n"
                "def test_it():\n    assert FakeRepo().get(1)\n"
            ),
        },
        monkeypatch=monkeypatch,
    )

    fake = read(tmp_path, "tests/test_b.py")
    assert "def get(self, *, key):" in fake
    assert "FakeRepo().get(key=1)" in fake


@pytest.mark.parametrize(
    ("caller", "reason"),
    [
        ("def use(thing):\n    return thing.price(1)\n", "src/app/b.py:2 cannot be resolved"),
        ("from app.a import price\n\nhandlers = [price]\n", "src/app/b.py:3 passes it as a value"),
        (
            'from unittest import mock\n\npatched = mock.patch("app.a.price")\n',
            "src/app/b.py:3 names it in a string",
        ),
        ("import app.a\n\napp.a.price = print\n", "src/app/b.py:3 replaces it"),
    ],
)
def test_a_call_that_cannot_be_followed_stops_the_fix(
    caller: str, reason: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Подпись без всех своих вызовов хуже нетронутой: правка не применяется, причина названа."""
    output = fixed(
        root=tmp_path,
        files={"src/app/a.py": PORT, "src/app/b.py": caller},
        monkeypatch=monkeypatch,
    )

    assert "def price(market, stake=1):" in read(tmp_path, "src/app/a.py")
    assert f"price takes market, stake by position; put a `*` before them; not fixed: {reason}" in (
        output
    )


def test_a_double_with_other_parameters_stops_the_port(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Двойник зовёт параметр по-своему: именованный вызов на нём упадёт.

    pyright тесты не судит так строго, как исходники, — поймать это некому.
    """
    output = fixed(
        root=tmp_path,
        files={
            "src/app/a.py": PORT,
            "tests/test_b.py": "class FakeRepo:\n    def get(self, ident):\n        return ident\n",
        },
        monkeypatch=monkeypatch,
    )

    assert "def get(self, key):" in read(tmp_path, "src/app/a.py")
    assert "tests/test_b.py:2 has a method of that name with other parameters" in output


def test_a_constructor_is_left_with_the_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = fixed(
        root=tmp_path,
        files={"src/app/a.py": BOX},
        monkeypatch=monkeypatch,
    )

    assert "def __init__(self, value):" in read(tmp_path, "src/app/a.py")
    assert "__init__ is called through its class" in output


def test_a_method_a_foreign_base_may_call_is_left(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`ast.NodeVisitor` сам зовёт `visit_Name(node)` — по позиции."""
    output = fixed(
        root=tmp_path,
        files={
            "src/app/a.py": (
                "import ast\n\n\nclass Names(ast.NodeVisitor):\n"
                "    def visit_Name(self, node):\n        return node\n"
            )
        },
        monkeypatch=monkeypatch,
    )

    assert "def visit_Name(self, node):" in read(tmp_path, "src/app/a.py")
    assert "Names derives from NodeVisitor" in output


def test_a_venv_git_cannot_vouch_for_is_not_started(tmp_path: Path) -> None:
    """Проект из архива: git молчит, а `.venv/bin/python` внутри может быть чем угодно."""
    venv = tmp_path / ".venv"
    venv.mkdir()

    assert _environment(root=tmp_path) != str(venv)


def test_a_committed_venv_is_not_started(tmp_path: Path) -> None:
    """jedi запускает интерпретатор окружения: закоммиченный `.venv` — чужая программа."""
    venv = tmp_path / ".venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text("home = /usr/bin\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)  # noqa: S603, S607

    assert _environment(root=tmp_path) == str(venv)

    subprocess.run(["git", "-C", str(tmp_path), "add", "-f", ".venv"], check=True)  # noqa: S603, S607

    assert _environment(root=tmp_path) != str(venv)
