"""ruff ставит `...` заглушки на строку, которой кончается подпись в столбик."""

from typing import Protocol


class Consumer(Protocol):
    def subscribe(
        self,
        topics: list[str],
    ) -> None: ...  # check-ok: keyword-only-arguments: форма чужой библиотеки
