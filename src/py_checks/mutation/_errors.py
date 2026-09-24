"""The package's errors."""

from __future__ import annotations


class GateError(RuntimeError):
    """The gate could not answer: mutmut or git did not reach a verdict.

    An error of its own, because otherwise exactly what the gate exists to
    prevent would happen: a run that died on import prints no verdict, and a
    report with no verdicts reads as zero survivors — that is, as ground won.
    """
