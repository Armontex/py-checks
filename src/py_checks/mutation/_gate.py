"""The three things the gate does: judge the branch, judge the whole tree, write the record."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from py_checks.mutation._baseline import recorded, write
from py_checks.mutation._mutmut import Mutmut, by_module, module_of, survivors, tallied
from py_checks.mutation._process import Shell
from py_checks.mutation._scope import against_ref, changed, scope
from py_checks.mutation._settings import mutation

if TYPE_CHECKING:
    from pathlib import Path

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
    """The verdict on a branch and what it was compared against."""

    against: str
    verdict: Verdict


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

    def diff(self, *, against: str | None) -> Diffed | None:
        """Only the modules the branch touched — what a push runs.

        Per module, not in total, because a change has no total to be compared
        with: a change in one file must not leave IN THAT FILE more survivors
        than are recorded. `None` — nothing to compare against, and the caller
        decides for itself whether to run everything.
        """
        target = against or against_ref(
            shell=self.mutmut.shell,
            candidates=self.settings.against,
        )
        if target is None:
            return None
        modules = changed(
            shell=self.mutmut.shell,
            against=target,
            area=scope(
                root=self.root,
                src=self.config.src,
            ),
        )
        return Diffed(
            against=target,
            verdict=_changed(
                report=self.mutmut.report(modules=modules) if modules else "",
                modules=modules,
                before=recorded(path=self.baseline),
            ),
        )

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
