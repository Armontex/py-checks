"""Две двери и хелпер рядом."""


class CancelBetUseCase:
    def execute(self) -> bool:
        return True

    def retry(self) -> bool:
        return False


def _rounded(*, amount: int) -> int:
    return amount
