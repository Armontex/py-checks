"""The three things the gate does: judge the branch, judge the whole tree, write the record."""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING

from py_checks.mutation._baseline import recorded, write
from py_checks.mutation._cache import (
    collected,
    digests,
    forget,
    outdated,
    remember,
    remembered,
    stale,
    suite,
)
from py_checks.mutation._mutmut import (
    Mutmut,
    by_module,
    module_of,
    survivors,
    tallied,
    unchecked,
)
from py_checks.mutation._process import Shell
from py_checks.mutation._scope import against_ref, changed, scope
from py_checks.mutation._settings import mutation

if TYPE_CHECKING:
    from pathlib import Path, PurePosixPath

    from py_checks.config import Config
    from py_checks.mutation._mutmut import Tally
    from py_checks.mutation._settings import Mutation


@dataclass(frozen=True, slots=True)
class Verdict:
    """What the run said about the modules it judged, beside what is recorded.

    Judged per module, not by the total: the total stays put when one module
    gains survivors and another loses as many — and the new hole goes through
    under cover of somebody else's work.
    """

    counted: dict[str, int]
    recorded: dict[str, int]
    alive: tuple[str, ...]
    tally: Tally

    @property
    def grown(self) -> dict[str, tuple[int, int]]:
        """Modules with more survivors than recorded: now and on record."""
        return {
            module: (now, self.recorded.get(module, 0))
            for module, now in sorted(self.counted.items())
            if now > self.recorded.get(module, 0)
        }

    @property
    def total(self) -> int:
        return sum(self.counted.values())


@dataclass(frozen=True, slots=True)
class Diffed:
    """The verdict on a branch and what it was compared against.

    `stale` — functions of the changed modules mutmut's test map did not know,
    for which the map was collected again before the run.
    """

    against: str
    verdict: Verdict
    stale: int = 0


@dataclass(frozen=True, slots=True)
class Gate:
    """One project's gate: its root, its settings and how mutmut is called."""

    root: Path
    config: Config
    settings: Mutation
    mutmut: Mutmut

    @property
    def baseline(self) -> Path:
        return self.root / self.settings.baseline

    def full(self) -> Verdict:
        """Everything that is mutated, against the record — module by module.

        A module on record with no survivors left is counted too, with zero:
        otherwise its decrease is not seen, and the record goes on carrying
        ground already won.
        """
        report = self.mutmut.report()
        alive = survivors(report=report)
        reported = by_module(alive=alive)
        before = recorded(path=self.baseline)
        return Verdict(
            counted={module: reported.get(module, 0) for module in {*reported, *before}},
            recorded=before,
            alive=tuple(sorted(alive)),
            tally=tallied(report=report),
        )

    def diff(
        self,
        *,
        against: str | None,
        rerun: bool = False,
    ) -> Diffed | None:
        """Only the modules the branch touched — what a push runs.

        Per module, not in total, because a change has no total to be compared
        with: a change in one file must not leave IN THAT FILE more survivors
        than are recorded. `None` — nothing to compare against, and the caller
        decides for itself whether to run everything.

        Of those modules, only the mutants whose verdict no longer stands are
        run: of a function that changed, or one a changed test reaches. The
        rest keep the cached verdict. `rerun`, a cold cache or a test map
        collected again run every mutant of the modules.
        """
        target = against or against_ref(
            shell=self.mutmut.shell,
            candidates=self.settings.against,
        )
        if target is None:
            return None
        files = changed(
            shell=self.mutmut.shell,
            against=target,
            area=scope(
                root=self.root,
                src=self.config.src,
            ),
        )
        modules = tuple(files)
        unknown = stale(
            root=self.root,
            paths=files.values(),
        )
        if unknown:
            forget(root=self.root)
        return Diffed(
            against=target,
            verdict=_changed(
                report=self._report(
                    files=files,
                    everything=rerun or not collected(root=self.root),
                )
                if modules
                else "",
                modules=modules,
                before=recorded(path=self.baseline),
            ),
            stale=unknown,
        )

    def _report(
        self,
        *,
        files: dict[str, PurePosixPath],
        everything: bool,
    ) -> str:
        """The report on the changed modules, run only as far as the cache is out of date.

        A second pass takes what the first left untried — mutmut drops
        verdicts of its own when its settings change — and, once a test file
        changed, the survivors: a test written to kill one reaches it in the
        map only after a run collected it.
        """
        modules = tuple(files)
        before = remembered(root=self.root)
        report = (
            self.mutmut.report(modules=modules)
            if everything
            else self.mutmut.report(
                modules=modules,
                named=outdated(
                    now=digests(
                        root=self.root,
                        files=files,
                    ),
                    before=before.functions,
                ),
                again=partial(
                    _again,
                    modules=modules,
                    survivors_too=suite(root=self.root) != before.suite,
                ),
            )
        )
        remember(
            root=self.root,
            found=digests(
                root=self.root,
                files=files,
            ),
            tests=suite(root=self.root),
        )
        return report

    def record(self) -> dict[str, int]:
        """A full run, and its result per module written to the record file."""
        counted = by_module(alive=survivors(report=self.mutmut.report()))
        write(
            path=self.baseline,
            counted=counted,
        )
        return counted


def _changed(
    *,
    report: str,
    modules: tuple[str, ...],
    before: dict[str, int],
) -> Verdict:
    """The verdict on the branch's modules.

    The report prints the whole cache, modules the branch did not touch
    included; only what it changed is judged here. An empty list of modules is
    an empty verdict: there was nothing to run, and mutmut was not called.
    """
    alive = [mutant for mutant in survivors(report=report) if module_of(mutant=mutant) in modules]
    reported = by_module(alive=alive)
    return Verdict(
        counted={module: reported.get(module, 0) for module in modules},
        recorded=before,
        alive=tuple(sorted(alive)),
        tally=tallied(
            report=report,
            modules=modules,
        ),
    )


def _again(
    *,
    report: str,
    modules: tuple[str, ...],
    survivors_too: bool,
) -> list[str]:
    """What the first pass left untried, and the survivors once a test changed."""
    alive = survivors(report=report) if survivors_too else []
    return [
        *(mutant for mutant in alive if module_of(mutant=mutant) in modules),
        *unchecked(
            report=report,
            modules=modules,
        ),
    ]


def gate(
    *,
    root: Path,
    config: Config,
    children: int | None = None,
) -> Gate:
    """The project's gate. `children` from the command line wins over the setting."""
    settings = mutation(config=config)
    return Gate(
        root=root,
        config=config,
        settings=settings,
        mutmut=Mutmut(
            shell=Shell(
                root=root,
                env=settings.env,
            ),
            command=settings.command,
            children=children or settings.children,
        ),
    )
