"""Use case лежит в use_cases."""


class PlaceBetUseCase:
    async def execute(self, *, stake: int) -> int:
        return stake
