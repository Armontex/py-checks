from shop.modules.betslip.errors.denials import BetslipChangedError


class PlaceUseCase:
    async def execute(self, *, changed: bool, funds: int) -> None:
        if funds < 0:
            raise ValueError("not enough funds")
        if changed:
            raise BetslipChangedError("the betslip changed")
        raise BetslipChangedError
