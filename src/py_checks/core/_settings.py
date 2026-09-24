"""Narrowing the settings to a particular check's model."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from py_checks.config import CheckSettings


class SettingsMismatchError(Exception):
    """A check was given settings that are not its own."""

    def __init__(
        self,
        *,
        code: str,
        expected: type[object],
        got: type[object],
    ) -> None:
        super().__init__(f"{code}: expected {expected.__name__}, got {got.__name__}")
        self.code = code


def settings_as[S: CheckSettings](
    *,
    settings: CheckSettings,
    model: type[S],
    code: str,
) -> S:
    """The same settings, but now of the check's own type.

    The core hands a check the general `CheckSettings`: otherwise the protocol
    would have to be parametrised by the settings type, and the registry would
    no longer fit into one dict. Narrowing here costs one line at the start of
    a rule, and from then on both the editor and pyright see the fields.
    """
    if not isinstance(settings, model):
        raise SettingsMismatchError(
            code=code,
            expected=model,
            got=type(settings),
        )
    return settings
