"""Matching an address against a path.

An address in the settings is not a prefix and not a directory name but
consecutive pieces of a path: `application/use_cases` is found inside
`modules/<name>/` as well. Rules use it to ask whether a file sits in the named
place; the `doctor` command uses the same thing to ask whether the directory a
setting speaks of exists at all. One question, so one answerer: two similar
comparisons would drift apart, and `doctor` would give reassurance about an
address the rule walks past.
"""

from __future__ import annotations

from typing import Final

SEPARATOR: Final = "/"

# Any one piece of a path: `modules/*/domain` is the domain of any module.
ANY: Final = "*"


def depth(
    *,
    parts: tuple[str, ...],
    path: str,
) -> int | None:
    """The end of the last occurrence of consecutive path pieces, or `None`.

    The end, not the start: the nesting of two addresses of different length
    can only be compared by where they end — the one that ends later is
    deeper.
    """
    needle = tuple(path.split(SEPARATOR))
    span = len(needle)
    ends = [
        start + span
        for start in range(len(parts) - span + 1)
        if _same(
            found=parts[start : start + span],
            needle=needle,
        )
    ]
    return max(ends) if ends else None


def _same(
    *,
    found: tuple[str, ...],
    needle: tuple[str, ...],
) -> bool:
    return all(wanted in (ANY, part) for part, wanted in zip(found, needle, strict=True))
