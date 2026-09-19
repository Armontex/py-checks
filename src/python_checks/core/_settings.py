"""Сужение настроек до модели конкретной проверки."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from python_checks.config import CheckSettings


class SettingsMismatchError(Exception):
    """Проверке отдали не её настройки."""

    def __init__(
        self,
        *,
        code: str,
        expected: type[object],
        got: type[object],
    ) -> None:
        super().__init__(f"{code}: ожидались {expected.__name__}, пришли {got.__name__}")
        self.code = code


def settings_as[S: CheckSettings](
    *,
    settings: CheckSettings,
    model: type[S],
    code: str,
) -> S:
    """Те же настройки, но уже своего типа.

    Ядро отдаёт проверке общий `CheckSettings`: иначе протокол пришлось бы
    параметризовать типом настроек, и реестр перестал бы складываться в один
    словарь. Сужение здесь — одна строка в начале правила, зато дальше поля
    видит и редактор, и pyright.
    """
    if not isinstance(settings, model):
        raise SettingsMismatchError(
            code=code,
            expected=model,
            got=type(settings),
        )
    return settings
