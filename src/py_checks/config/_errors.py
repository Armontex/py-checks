"""Errors in reading the settings."""

from __future__ import annotations


class ConfigError(Exception):
    """The config exists but cannot be read.

    One error for every case: broken TOML, an unknown key, a wrong value. For
    whoever ran the check it is the same event — the config needs fixing — and
    the text carries the details.
    """
