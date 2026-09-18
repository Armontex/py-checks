"""Сценарию можно логгер, но не веб-стек."""

import structlog
from fastapi import Depends

__all__ = ["Depends", "structlog"]
