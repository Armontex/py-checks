"""Запросу подсунули команду, голую строку и аргумент без аннотации."""

from application.dto.commands import CreateBetCommand


class FindBetUseCase:
    async def execute(self, *, command: CreateBetCommand, name: str, raw) -> bool:  # noqa: ANN001
        return bool(command and name and raw)
