from dataclasses import dataclass

from shop.shared.refusals import Refusal


@dataclass(frozen=True, slots=True)
class BetslipChangedError(Exception):
    refusal: Refusal
