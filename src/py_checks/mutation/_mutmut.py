"""Running mutmut and parsing what it printed."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Protocol

from py_checks.mutation._errors import GateError
from py_checks.mutation._process import said

if TYPE_CHECKING:
    from subprocess import CompletedProcess

    from py_checks.mutation._process import Shell

# `mutmut run` that got to the end exits with zero, survivors or not. One is
# its `exit(1)` — stats not collected, the clean run of the tests failed — or a
# crash of Python itself; the cache then still holds the previous run's
# verdicts, and reading them would call a run that checked nothing a pass.
# Except one message: names that match no mutant, which is a module with
# nothing to mutate, not a broken tool.
NOTHING_MATCHES: Final = "Filtered for specific mutants, but nothing matches"

# Two verdicts, not one: `survived` is a mutant every test walked past,
# `no tests` is a mutant no test reached. The second is the stronger: a module
# without a single test would otherwise score zero survivors.
ALIVE: Final = re.compile(r"^\s*(?P<mutant>\S+): (?:survived|no tests)$", re.MULTILINE)

# A mutant the run never tried: a run that was stopped exits with zero, and
# by the exit code it cannot be told from a run that checked everything; by
# this line it can.
UNCHECKED: Final = re.compile(r"^\s*(?P<mutant>\S+): not checked$", re.MULTILINE)

# Every line of the report: a mutant and its verdict.
VERDICT: Final = re.compile(r"^\s*(?P<mutant>\S+): (?P<verdict>.+?)\s*$", re.MULTILINE)

# Killed — the way mutmut itself counts it: a test failed, a test hung, or the
# mutant failed the type check. Alive — the same thing the gate refuses on.
# Not tried — not counted among those run.
KILLED: Final[frozenset[str]] = frozenset({"killed", "timeout", "caught by type check"})
SURVIVED: Final[frozenset[str]] = frozenset({"survived", "no tests"})
UNTRIED: Final[frozenset[str]] = frozenset({"not checked", "skipped"})

MUTANT_OF_MODULE: Final = "{module}.*"

# What mutmut prints when its own map of tests to functions broke: the tests
# may have collected and passed, and it is mutmut's plugin that failed.
STATS_FAILED: Final = "failed to collect stats"

# pytest's summary line for an error outside a test — a failed collection the
# first among them: `ERROR tests/test_x.py - FileNotFoundError: ...` — or for a
# test that failed: `FAILED tests/test_x.py::test_y - assert 20 == 21`.
COLLECTION_ERROR: Final = re.compile(r"^(?:ERROR|FAILED) (?P<error>.+)$", re.MULTILINE)


class Again(Protocol):
    """What to run by name once more, read from the report of the first pass."""

    def __call__(self, *, report: str) -> list[str]: ...


@dataclass(frozen=True, slots=True)
class Tally:
    """How many mutants the run tried and how that ended.

    `other` — verdicts that are neither a kill nor a survival: `suspicious`,
    `segfault`, an interrupted run. They are few and rare, but quietly folding
    them into one of the two piles would be lying about that pile.
    """

    killed: int
    alive: int
    other: int

    @property
    def tried(self) -> int:
        return self.killed + self.alive + self.other


@dataclass(frozen=True, slots=True)
class Mutmut:
    """How mutmut is called in this project."""

    shell: Shell
    command: tuple[str, ...]
    children: int | None

    def report(
        self,
        *,
        modules: tuple[str, ...] = (),
        named: tuple[str, ...] | None = None,
        again: Again | None = None,
    ) -> str:
        """The report after a run: of the named modules or of everything mutated.

        `named` — the mutants to run: by default every one of the modules, or
        everything when no module is named; an empty tuple runs nothing and
        reads the cache. `again` — what to run by name once more after reading
        the report.

        A run of everything reruns the survivors: the cache is keyed on the
        source, and a test written today kills a mutant in a file nobody
        touched, while the cache would go on counting it alive.
        """
        if named is None:
            named = tuple(MUTANT_OF_MODULE.format(module=module) for module in modules)
        finished = self._run(named=named) if named or not modules else None
        report = self._results()
        if again is None:
            alive = [] if modules else survivors(report=report)
        else:
            alive = again(report=report)
        if alive:
            finished = self._run(named=tuple(alive))
            report = self._results()
        untried = unchecked(
            report=report,
            modules=modules,
        )
        if untried:
            tried = tallied(
                report=report,
                modules=modules,
            ).tried
            head = (
                f"mutmut did not try {len(untried)} mutant(s), the first is {untried[0]}"
                if tried
                else f"0 of {len(untried)} mutants run"
            )
            raise GateError(
                self._refusal(
                    head=head,
                    finished=finished,
                )
            )
        return report

    def _run(self, *, named: tuple[str, ...]) -> CompletedProcess[str]:
        children = ("--max-children", str(self.children)) if self.children else ()
        finished = self.shell.finished(command=(*self.command, "run", *children, *named))
        output = finished.stdout + finished.stderr
        if finished.returncode and NOTHING_MATCHES not in output:
            raise GateError(
                self._refusal(
                    head="mutmut stopped before a verdict",
                    finished=finished,
                )
            )
        return finished

    def _results(self) -> str:
        return self.shell.answered(command=(*self.command, "results", "--all", "true"))

    @staticmethod
    def _refusal(
        *,
        head: str,
        finished: CompletedProcess[str] | None,
    ) -> str:
        """Why the run reached no verdict: the gate's reading first, mutmut's words after.

        The first collection error is named on its own: the tests run in
        mutants/, a copy that holds only `source_paths` and `also_copy`, and a
        test that reads a file outside them fails there and nowhere else.
        """
        if finished is None:
            return f"{head}; the cache holds them so, and nothing was run"
        output = finished.stdout + finished.stderr
        error = COLLECTION_ERROR.search(output)
        if error:
            cause = f"the tests fail in mutants/: {error['error']}"
        elif STATS_FAILED in output:
            cause = "mutmut failed to collect stats, its map of which test reaches which function"
        else:
            cause = "most likely the tests failed to collect in its copy of the project"
        return f"{head}; {cause}\n{said(finished=finished)}"


def survivors(*, report: str) -> list[str]:
    return ALIVE.findall(report)


def tallied(
    *,
    report: str,
    modules: tuple[str, ...] = (),
) -> Tally:
    """The count by verdict: of the whole report or of the named modules only."""
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
    """Mutants in the run's scope that it did not reach: all of them if no
    modules are named, otherwise only those of the named modules."""
    return [
        mutant
        for mutant in UNCHECKED.findall(report)
        if not modules or module_of(mutant=mutant) in modules
    ]


def module_of(*, mutant: str) -> str:
    """A mutant's module: its name without the last part, the mutant's own name."""
    return mutant.rsplit(".", 1)[0]


def by_module(*, alive: list[str]) -> dict[str, int]:
    counted: dict[str, int] = {}
    for mutant in alive:
        module = module_of(mutant=mutant)
        counted[module] = counted.get(module, 0) + 1
    return counted
