"""Слои и то, что каждому из них разрешено импортировать."""

from __future__ import annotations

from typing import Final

# Зависимости смотрят внутрь: домен не знает ничего, приложение знает домен, а
# всё, что разговаривает с внешним миром, знает приложение и невидимо для него.
#
# `presentation` намеренно не видит `domain`: край переводит свои типы в DTO
# приложения и обратно, и роутер, читающий доменный объект, связал форму
# внешнего мира с формой правил.
BASE: Final[dict[str, frozenset[str]]] = {
    "domain": frozenset({"domain", "shared"}),
    "application": frozenset({"domain", "application", "shared"}),
    "infra": frozenset({"domain", "application", "infra", "shared", "config"}),
    "presentation": frozenset({"application", "presentation", "shared", "config"}),
    "observability": frozenset({"observability", "shared", "config"}),
    "config": frozenset({"config", "shared"}),
    "shared": frozenset({"shared"}),
}

# Композиционный корень связывает слои между собой — это вся его работа, и
# поэтому ему можно всё. В таблице его нет: там перечислены те, кого ограничивают.
COMPOSITION_ROOT: Final[frozenset[str]] = frozenset({"ioc", "bootstrap", "entrypoints"})
