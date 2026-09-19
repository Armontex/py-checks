"""API и события.

Маршрут объявляет в декораторе всё, чем он будет описан в схеме: механизм у
фреймворка есть, требования писать — нет.
"""

from python_checks.checks.api._endpoint_declarations import (
    EndpointDeclarations,
    EndpointDeclarationsSettings,
)
from python_checks.checks.api._marker import MARKER

__all__ = ["MARKER", "EndpointDeclarations", "EndpointDeclarationsSettings"]
