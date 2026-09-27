"""Команда берёт команду, и ссылка вперёд — та же команда."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application.dto.commands import PlaceBetCommand


class PlaceBetUseCase:
    async def execute(self, *, command: "PlaceBetCommand") -> bool:  # noqa: UP037
        return command is not None
