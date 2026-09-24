"""Три вопроса гейта: что сломала ветка, что по всему дереву, и записать."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from py_checks.mutation._baseline import recorded, write
from py_checks.mutation._mutmut import Mutmut, by_module, module_of
from py_checks.mutation._process import Shell
from py_checks.mutation._scope import against_ref, changed, scope
from py_checks.mutation._settings import mutation

if TYPE_CHECKING:
    from pathlib import Path

    from py_checks.config import Config
    from py_checks.mutation._settings import Mutation


@dataclass(frozen=True, slots=True)
class Verdict:
    """Что прогон сказал о модулях, которые судил, рядом с тем, что записано.

    Судят по модулю, а не по сумме: сумма стоит на месте, когда в одном модуле
    выживших прибавилось, а в другом столько же убыло, — и новая дыра проходит
    под прикрытием чужой работы.
    """

    counted: dict[str, int]
    recorded: dict[str, int]
    alive: tuple[str, ...]

    @property
    def grown(self) -> dict[str, tuple[int, int]]:
        """Модули, где выживших больше записанного: сейчас и по записи."""
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
    """Вердикт по ветке и то, с чем её сравнивали."""

    against: str
    verdict: Verdict


@dataclass(frozen=True, slots=True)
class Gate:
    """Гейт одного проекта: его корень, настройки и то, как звать mutmut."""

    root: Path
    config: Config
    settings: Mutation
    mutmut: Mutmut

    @property
    def baseline(self) -> Path:
        return self.root / self.settings.baseline

    def full(self) -> Verdict:
        """Всё, что мутируется, против записи — модуль за модулем.

        Модуль из записи, где выживших не осталось, тоже попадает в счёт, с
        нулём: иначе убыль в нём не видна, и запись так и носит отвоёванное.
        """
        alive = self.mutmut.alive()
        reported = by_module(alive=alive)
        before = recorded(path=self.baseline)
        return Verdict(
            counted={module: reported.get(module, 0) for module in {*reported, *before}},
            recorded=before,
            alive=tuple(sorted(alive)),
        )

    def diff(self, *, against: str | None) -> Diffed | None:
        """Только модули, которые тронула ветка, — то, что гоняет пуш.

        По модулю, а не в сумме, потому что у правки нет суммы, с которой
        её сравнить: правка в одном файле не должна оставлять В ЭТОМ ФАЙЛЕ
        больше выживших, чем записано. `None` — сравнивать не с чем, и
        вызывающий решает сам, гнать ли всё.
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
        before = recorded(path=self.baseline)
        if not modules:
            return Diffed(
                against=target,
                verdict=Verdict(
                    counted={},
                    recorded=before,
                    alive=(),
                ),
            )
        # Отчёт печатает весь кэш, и модули, которых ветка не трогала, тоже;
        # судят здесь только то, что она поменяла.
        alive = [
            mutant
            for mutant in self.mutmut.alive(modules=modules)
            if module_of(mutant=mutant) in modules
        ]
        reported = by_module(alive=alive)
        return Diffed(
            against=target,
            verdict=Verdict(
                counted={module: reported.get(module, 0) for module in modules},
                recorded=before,
                alive=tuple(sorted(alive)),
            ),
        )

    def record(self) -> dict[str, int]:
        """Полный прогон, и его итог по модулям — в файл записи."""
        counted = by_module(alive=self.mutmut.alive())
        write(
            path=self.baseline,
            counted=counted,
        )
        return counted


def gate(
    *,
    root: Path,
    config: Config,
    children: int | None = None,
) -> Gate:
    """Гейт проекта. `children` из командной строки побеждает настройку."""
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
