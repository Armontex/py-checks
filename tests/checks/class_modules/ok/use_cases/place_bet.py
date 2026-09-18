"""Один класс, и ничего рядом."""


class PlaceBetUseCase:
    async def execute(self, *, stake: int) -> int:
        return self._doubled(stake=stake)

    @staticmethod
    def _doubled(*, stake: int) -> int:
        return stake * 2
