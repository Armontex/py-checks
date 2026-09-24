"""Прогон mutmut и разбор того, что он напечатал."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from py_checks.mutation._errors import GateError
from py_checks.mutation._process import said

if TYPE_CHECKING:
    from py_checks.mutation._process import Shell

# `mutmut run` выходит с единицей ровно тогда, когда кто-то выжил: здесь это
# обычный исход, а не сбой инструмента. Всё, что выше, — сбой, и читаться как
# чистый прогон он не должен.
ALIVE_EXIT: Final = 1

# Два вердикта, а не один: `survived` — мутант, мимо которого прошли все тесты,
# `no tests` — мутант, до которого не дошёл ни один. Второе сильнее: модуль без
# единого теста иначе давал бы ноль выживших.
ALIVE: Final = re.compile(r"^\s*(?P<mutant>\S+): (?:survived|no tests)$", re.MULTILINE)

# Мутант, которого прогон так и не попробовал. Когда падает сбор тестов, mutmut
# всё равно выходит с единицей, и по коду выхода такой прогон не отличить от
# прогона с выжившими; по этой строке — отличить.
UNCHECKED: Final = re.compile(r"^\s*(?P<mutant>\S+): not checked$", re.MULTILINE)

# Каждая строка отчёта: мутант и вердикт.
VERDICT: Final = re.compile(r"^\s*(?P<mutant>\S+): (?P<verdict>.+?)\s*$", re.MULTILINE)

# Убит — так же, как считает сам mutmut: тест упал, тест завис, или мутант не
# прошёл проверку типов. Жив — то же, по чему гейт отказывает. Не пробовали —
# в счёт запущенных не идёт.
KILLED: Final[frozenset[str]] = frozenset({"killed", "timeout", "caught by type check"})
SURVIVED: Final[frozenset[str]] = frozenset({"survived", "no tests"})
UNTRIED: Final[frozenset[str]] = frozenset({"not checked", "skipped"})

MUTANT_OF_MODULE: Final = "{module}.*"


@dataclass(frozen=True, slots=True)
class Tally:
    """Сколько мутантов прогон попробовал и чем это кончилось.

    `other` — вердикты, которые не убийство и не выживание: `suspicious`,
    `segfault`, прерванный прогон. Их мало и они редки, но молча растворить их
    в одной из двух кучек значило бы соврать о ней.
    """

    killed: int
    alive: int
    other: int

    @property
    def tried(self) -> int:
        return self.killed + self.alive + self.other


@dataclass(frozen=True, slots=True)
class Mutmut:
    """Как звать mutmut в этом проекте."""

    shell: Shell
    command: tuple[str, ...]
    children: int | None

    def report(self, *, modules: tuple[str, ...] = ()) -> str:
        """Отчёт после прогона: названных модулей или всего, что мутируется.

        Названные модули прогоняются заново, даже когда в кэше есть их
        вердикт, — ради этого их и называют: кэш привязан к исходнику, и тест,
        который ослабили, оставляет стоять все вердикты, что он раньше
        заработал.

        Прогон всего перезапускает выживших по той же причине, прочитанной
        наоборот: тест, написанный сегодня, убивает мутанта в файле, которого
        никто не трогал, а кэш продолжал бы считать его живым.
        """
        named = tuple(MUTANT_OF_MODULE.format(module=module) for module in modules)
        self._run(named=named)
        report = self._results()
        if not modules:
            report = self._again(alive=survivors(report=report))
        untried = unchecked(
            report=report,
            modules=modules,
        )
        if untried:
            raise GateError(
                f"mutmut не попробовал {len(untried)} мутант(ов), первый — {untried[0]}; "
                f"скорее всего, не собрались тесты в его копии проекта"
            )
        return report

    def _run(self, *, named: tuple[str, ...]) -> None:
        children = ("--max-children", str(self.children)) if self.children else ()
        finished = self.shell.finished(command=(*self.command, "run", *children, *named))
        if finished.returncode > ALIVE_EXIT:
            raise GateError(said(finished=finished))

    def _results(self) -> str:
        return self.shell.answered(command=(*self.command, "results", "--all", "true"))

    def _again(self, *, alive: list[str]) -> str:
        """Выжившие, прогнанные по имени, и отчёт после этого."""
        if alive:
            self._run(named=tuple(alive))
        return self._results()


def survivors(*, report: str) -> list[str]:
    return ALIVE.findall(report)


def tallied(
    *,
    report: str,
    modules: tuple[str, ...] = (),
) -> Tally:
    """Счёт по вердиктам: всего отчёта или только названных модулей."""
    verdicts = [
        found["verdict"]
        for found in VERDICT.finditer(report)
        if not modules or module_of(mutant=found["mutant"]) in modules
    ]
    tried = [verdict for verdict in verdicts if verdict not in UNTRIED]
    killed = sum(verdict in KILLED for verdict in tried)
    alive = sum(verdict in SURVIVED for verdict in tried)
    return Tally(
        killed=killed,
        alive=alive,
        other=len(tried) - killed - alive,
    )


def unchecked(
    *,
    report: str,
    modules: tuple[str, ...] = (),
) -> list[str]:
    """Мутанты из области прогона, которых он не достиг: все, если модули не
    названы, иначе только мутанты названных."""
    return [
        mutant
        for mutant in UNCHECKED.findall(report)
        if not modules or module_of(mutant=mutant) in modules
    ]


def module_of(*, mutant: str) -> str:
    """Модуль мутанта: его имя без последнего куска, имени самого мутанта."""
    return mutant.rsplit(".", 1)[0]


def by_module(*, alive: list[str]) -> dict[str, int]:
    counted: dict[str, int] = {}
    for mutant in alive:
        module = module_of(mutant=mutant)
        counted[module] = counted.get(module, 0) + 1
    return counted
