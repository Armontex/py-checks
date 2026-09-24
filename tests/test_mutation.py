"""Мутационный гейт, прогнанный с поддельным mutmut.

Настоящий mutmut — это минуты и живой проект; гейт же отвечает за то, как он
его зовёт и как читает ответ. Подделка печатает заготовленный отчёт и пишет в
журнал, с какими аргументами её звали, — этого хватает, чтобы проверить все
три режима, повторный прогон выживших и отказ на непопробованных мутантах.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path, PurePosixPath
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from py_checks.cli import app
from py_checks.config import load
from py_checks.mutation import GateError, gate
from py_checks.mutation._scope import Scope, scope

if TYPE_CHECKING:
    from py_checks.mutation import Gate

runner = CliRunner()

# Подделка: `run` считает свои вызовы и выходит с заданным кодом, `results`
# печатает отчёт, соответствующий числу прогонов на этот момент. Каждый вызов
# вместе с переменной, которую гейт обязан передать, пишется в журнал.
FAKE = dedent(
    """\
    import json, os, sys
    from pathlib import Path

    state = json.loads(Path("fake.json").read_text())
    runs = Path("fake.runs")
    done = int(runs.read_text()) if runs.exists() else 0
    with Path("fake.log").open("a") as log:
        log.write(json.dumps({"argv": sys.argv[1:], "env": os.environ.get("PROFILE")}) + "\\n")
    if sys.argv[1] == "run":
        runs.write_text(str(done + 1))
        sys.exit(state["exit"])
    reports = state["reports"]
    print(reports[min(done, len(reports)) - 1])
    """
)


def project(
    *,
    root: Path,
    reports: list[str],
    exit_code: int = 1,
    section: str = "",
) -> Path:
    (root / "fake_mutmut.py").write_text(FAKE, encoding="utf-8")
    (root / "fake.json").write_text(
        json.dumps({"exit": exit_code, "reports": reports}),
        encoding="utf-8",
    )
    command = json.dumps([sys.executable, str(root / "fake_mutmut.py")])
    (root / "pyproject.toml").write_text(
        dedent(
            f"""\
            [project]
            name = "demo"

            [tool.mutmut]
            source_paths = ["src/app/logic"]
            do_not_mutate = ["src/app/logic/ports/*"]

            [tool.py-checks.mutation]
            command = {command}
            env = {{ PROFILE = "deterministic" }}
            {section}
            """
        ),
        encoding="utf-8",
    )
    logic = root / "src" / "app" / "logic"
    logic.mkdir(parents=True)
    for name in ("__init__.py", "limits.py", "prices.py"):
        (logic / name).write_text("x = 1\n", encoding="utf-8")
    return root


def calls(*, root: Path) -> list[dict[str, object]]:
    return [
        json.loads(line) for line in (root / "fake.log").read_text(encoding="utf-8").splitlines()
    ]


def gate_of(*, root: Path, children: int | None = None) -> Gate:
    return gate(
        root=root,
        config=load(root=root),
        children=children,
    )


def git(*, root: Path, args: str) -> None:
    subprocess.run(  # noqa: S603 — тест строит свой репозиторий
        ["git", *args.split()],  # noqa: S607
        cwd=root,
        check=True,
        capture_output=True,
    )


def branched(*, root: Path) -> None:
    """Репозиторий с develop и веткой, которая тронула один мутируемый модуль."""
    git(root=root, args="init -q -b develop")
    git(root=root, args="config user.email t@t")
    git(root=root, args="config user.name t")
    git(root=root, args="add -A")
    git(root=root, args="commit -q -m base")
    git(root=root, args="switch -q -c feature")
    (root / "src" / "app" / "logic" / "limits.py").write_text("x = 2\n", encoding="utf-8")
    git(root=root, args="commit -q -am change")


def baseline(*, root: Path, counted: dict[str, int]) -> None:
    (root / "mutation-baseline.json").write_text(json.dumps(counted), encoding="utf-8")


# --- Область -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("src", "path", "module"),
    [
        ("src", "src/app/logic/limits.py", "app.logic.limits"),
        ("src", "src/app/logic/__init__.py", "app.logic"),
        (".", "app/logic/limits.py", "app.logic.limits"),
        ("src", "src/app/logic/ports/clock.py", None),
        ("src", "src/app/other.py", None),
        ("src", "src/app/logic/notes.md", None),
    ],
)
def test_a_path_becomes_the_name_mutmut_gives_its_mutants(
    src: str,
    path: str,
    module: str | None,
) -> None:
    area = Scope(
        sources=(PurePosixPath("src/app/logic"), PurePosixPath("app/logic")),
        spared=("src/app/logic/ports/*",),
        src=PurePosixPath(src),
    )

    assert area.module_of(path=PurePosixPath(path)) == module


def test_the_pyproject_table_wins_over_setup_cfg_as_it_does_for_mutmut(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[tool.mutmut]\nsource_paths = ["src/app/logic"]\n',
        encoding="utf-8",
    )
    (tmp_path / "setup.cfg").write_text(
        "[mutmut]\nsource_paths =\n    src/app/other\n",
        encoding="utf-8",
    )

    area = scope(root=tmp_path, src=Path("src"))

    assert area.sources == (PurePosixPath("src/app/logic"),)


def test_setup_cfg_is_read_line_by_line(tmp_path: Path) -> None:
    (tmp_path / "setup.cfg").write_text(
        "[mutmut]\n"
        "source_paths =\n    app/domain\n    app/shared\n"
        "do_not_mutate =\n    app/domain/ports/*\n",
        encoding="utf-8",
    )

    area = scope(root=tmp_path, src=Path("."))

    assert area.sources == (PurePosixPath("app/domain"), PurePosixPath("app/shared"))
    assert area.spared == ("app/domain/ports/*",)


def test_a_scope_nobody_declared_is_refused_rather_than_judged_empty(tmp_path: Path) -> None:
    with pytest.raises(GateError, match="source_paths"):
        scope(root=tmp_path, src=Path("src"))


# --- full --------------------------------------------------------------------


def test_full_reruns_what_the_cache_believes_alive(tmp_path: Path) -> None:
    """Кэш привязан к исходнику: мутант, которого убил сегодняшний тест, иначе
    числился бы живым, потому что его файл никто не трогал."""
    root = project(
        root=tmp_path,
        reports=[
            "app.logic.limits.x__mutmut_1: survived\napp.logic.prices.x__mutmut_2: survived",
            "app.logic.limits.x__mutmut_1: killed\napp.logic.prices.x__mutmut_2: survived",
        ],
    )

    verdict = gate_of(root=root).full()

    runs = [call["argv"] for call in calls(root=root) if call["argv"][0] == "run"]  # type: ignore[index]
    assert runs[1] == ["run", "app.logic.limits.x__mutmut_1", "app.logic.prices.x__mutmut_2"]
    assert verdict.counted == {"app.logic.prices": 1}


def test_full_judges_module_by_module_not_the_sum(tmp_path: Path) -> None:
    """Сумма та же, что в записи, но в одном модуле стало больше: это дыра,
    прикрытая чужой работой в другом."""
    root = project(
        root=tmp_path,
        reports=["app.logic.limits.a: survived\napp.logic.limits.b: survived"] * 2,
    )
    baseline(root=root, counted={"app.logic.limits": 1, "app.logic.prices": 1})

    verdict = gate_of(root=root).full()

    assert verdict.total == sum(verdict.recorded.values())
    assert verdict.grown == {"app.logic.limits": (2, 1)}
    assert verdict.counted["app.logic.prices"] == 0


def test_no_tests_counts_as_alive(tmp_path: Path) -> None:
    """Модуль без единого теста иначе давал бы ноль выживших."""
    root = project(root=tmp_path, reports=["app.logic.limits.a: no tests"] * 2)

    assert gate_of(root=root).full().counted == {"app.logic.limits": 1}


def test_a_run_that_died_is_refused_not_read_as_zero(tmp_path: Path) -> None:
    root = project(root=tmp_path, reports=[""], exit_code=2)

    with pytest.raises(GateError, match="завершился с кодом 2"):
        gate_of(root=root).full()


def test_mutants_never_tried_are_refused(tmp_path: Path) -> None:
    """Сбор тестов упал, а mutmut всё равно вышел с единицей: по коду выхода
    это не отличить от прогона с выжившими, по строке `not checked` — да."""
    root = project(root=tmp_path, reports=["app.logic.limits.a: not checked"] * 2)

    with pytest.raises(GateError, match="не попробовал 1"):
        gate_of(root=root).full()


def test_settings_reach_mutmut(tmp_path: Path) -> None:
    root = project(root=tmp_path, reports=[""])

    gate_of(root=root, children=3).full()

    first = calls(root=root)[0]
    assert first["argv"] == ["run", "--max-children", "3"]
    assert first["env"] == "deterministic"


# --- diff --------------------------------------------------------------------


def test_diff_runs_and_judges_only_what_the_branch_touched(tmp_path: Path) -> None:
    root = project(
        root=tmp_path,
        reports=["app.logic.limits.a: survived\napp.logic.prices.b: survived"],
    )
    branched(root=root)

    diffed = gate_of(root=root).diff(against="develop")

    assert diffed is not None
    assert calls(root=root)[0]["argv"] == ["run", "app.logic.limits.*"]
    assert diffed.verdict.counted == {"app.logic.limits": 1}
    assert diffed.verdict.alive == ("app.logic.limits.a",)


def test_diff_with_nothing_mutated_changed_runs_nothing(tmp_path: Path) -> None:
    root = project(root=tmp_path, reports=[""])
    branched(root=root)
    git(root=root, args="switch -q develop")

    diffed = gate_of(root=root).diff(against="develop")

    assert diffed is not None
    assert diffed.verdict.counted == {}
    assert not (root / "fake.log").exists()


def test_diff_with_nothing_to_compare_against_says_so(tmp_path: Path) -> None:
    root = project(root=tmp_path, reports=[""], section='against = ["nowhere"]')
    branched(root=root)

    assert gate_of(root=root).diff(against=None) is None


# --- record ------------------------------------------------------------------


def test_record_writes_the_map_a_diff_is_judged_against(tmp_path: Path) -> None:
    root = project(
        root=tmp_path,
        reports=["app.logic.prices.b: survived\napp.logic.limits.a: survived"] * 2,
    )

    gate_of(root=root).record()

    written = (root / "mutation-baseline.json").read_text(encoding="utf-8")
    assert json.loads(written) == {"app.logic.limits": 1, "app.logic.prices": 1}
    assert written.index("limits") < written.index("prices")


# --- Командная строка --------------------------------------------------------


def test_a_branch_that_grows_a_module_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = project(root=tmp_path, reports=["app.logic.limits.a: survived"])
    branched(root=root)
    monkeypatch.chdir(root)

    result = runner.invoke(app, ["mutation", "diff", "--against", "develop"])

    assert result.exit_code == 1
    assert "больше, чем записано" in result.output
    assert "app.logic.limits" in result.output


def test_a_branch_within_its_record_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = project(root=tmp_path, reports=["app.logic.limits.a: survived"])
    branched(root=root)
    baseline(root=root, counted={"app.logic.limits": 1})
    monkeypatch.chdir(root)

    result = runner.invoke(app, ["mutation", "diff", "--against", "develop"])

    assert result.exit_code == 0, result.output
    assert "ok: 1 выживш" in result.output


def test_full_below_the_record_asks_for_a_new_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = project(root=tmp_path, reports=["app.logic.limits.a: survived"] * 2)
    baseline(root=root, counted={"app.logic.limits": 3})
    monkeypatch.chdir(root)

    result = runner.invoke(app, ["mutation", "full"])

    assert result.exit_code == 0, result.output
    assert "по записи 3" in result.output
    assert "mutation record" in result.output


def test_full_that_grows_names_the_survivor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = project(root=tmp_path, reports=["app.logic.limits.x__mutmut_7: survived"] * 2)
    monkeypatch.chdir(root)

    result = runner.invoke(app, ["mutation", "full"])

    assert result.exit_code == 1
    assert "x__mutmut_7" in result.output


def test_record_says_what_it_wrote(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = project(root=tmp_path, reports=["app.logic.limits.a: survived"] * 2)
    monkeypatch.chdir(root)

    result = runner.invoke(app, ["mutation", "record"])

    assert result.exit_code == 0, result.output
    assert "записан mutation-baseline.json: 1 выживш" in result.output


def test_a_tool_that_could_not_answer_is_a_refusal_not_a_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = project(root=tmp_path, reports=[""], exit_code=2)
    monkeypatch.chdir(root)

    for command in ("full", "record"):
        result = runner.invoke(app, ["mutation", command])

        assert result.exit_code == 1, command
        assert "мутационный гейт" in result.output


def test_diff_with_nothing_to_compare_against_runs_everything(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = project(root=tmp_path, reports=[""] * 2, section='against = ["nowhere"]')
    branched(root=root)
    monkeypatch.chdir(root)

    result = runner.invoke(app, ["mutation", "diff"])

    assert result.exit_code == 0, result.output
    assert "гоню всё" in result.output


def test_diff_where_nothing_mutated_changed_says_so(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = project(root=tmp_path, reports=[""])
    branched(root=root)
    git(root=root, args="switch -q develop")
    monkeypatch.chdir(root)

    result = runner.invoke(app, ["mutation", "diff", "--against", "develop"])

    assert result.exit_code == 0, result.output
    assert "мутируемое не менялось" in result.output


def test_full_counts_what_was_tried_killed_and_left(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Справка, а не суд: сколько мутантов попробовали и чем кончилось."""
    report = (
        "app.logic.limits.a: killed\n"
        "app.logic.limits.b: timeout\n"
        "app.logic.limits.c: caught by type check\n"
        "app.logic.limits.d: survived\n"
        "app.logic.prices.e: no tests\n"
        "app.logic.prices.f: suspicious\n"
        "app.logic.prices.g: skipped"
    )
    root = project(root=tmp_path, reports=[report] * 2)
    baseline(root=root, counted={"app.logic.limits": 1, "app.logic.prices": 1})
    monkeypatch.chdir(root)

    result = runner.invoke(app, ["mutation", "full"])

    assert result.exit_code == 0, result.output
    assert "мутантов: запущено 6, убито 3, осталось 2, прочее 1" in result.output


def test_diff_counts_only_the_modules_it_judged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = project(
        root=tmp_path,
        reports=[
            "app.logic.limits.a: killed\napp.logic.limits.b: survived\n"
            "app.logic.prices.c: killed\napp.logic.prices.d: killed"
        ],
    )
    branched(root=root)
    baseline(root=root, counted={"app.logic.limits": 1})
    monkeypatch.chdir(root)

    result = runner.invoke(app, ["mutation", "diff", "--against", "develop"])

    assert result.exit_code == 0, result.output
    assert "в изменённых модулях: запущено 2, убито 1, осталось 1" in result.output
    assert "прочее" not in result.output
