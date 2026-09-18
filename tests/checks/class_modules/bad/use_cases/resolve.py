"""Хелпер, заехавший в модуль use case."""


def rounded(*, stake: int) -> int:
    return stake


class ResolveUseCase:
    async def execute(self, *, stake: int) -> int:
        return rounded(stake=stake)
