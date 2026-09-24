"""Effects: what the code takes from the world and what it says about it.

The clock, the dice and a new identifier come through a port, not a global
function: otherwise the same input gives a different output, and the test
either freezes the world with a mock or asserts nothing at all. A log line
names its event by an enum member: that name is read not by a human but by a
counter and an alert.
"""

from py_checks.checks.effects._determinism import Determinism, DeterminismSettings
from py_checks.checks.effects._log_events import LogEvents, LogEventsSettings
from py_checks.checks.effects._marker import MARKER

__all__ = [
    "MARKER",
    "Determinism",
    "DeterminismSettings",
    "LogEvents",
    "LogEventsSettings",
]
