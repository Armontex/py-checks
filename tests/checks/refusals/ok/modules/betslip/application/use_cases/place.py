from shop.modules.betslip.errors.denials import BetslipChangedError
from shop.shared.refusals import Refusal


class PlaceUseCase:
    async def execute(self, *, changed: bool) -> None:
        if changed:
            raise BetslipChangedError(refusal=Refusal.BETSLIP_CHANGED)
        raise NotImplementedError


class LaterUseCase:
    def execute(self) -> None:
        """Внутренняя ошибка говорит, что код написан неверно, а не игроку."""
        raise InvariantError("the basket lost its owner")
