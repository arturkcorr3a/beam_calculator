"""Parse element IDs typed as free text."""

import re

_SEPARATORS = re.compile(r"[,;\s]+")


def parse_id_list(text: str) -> tuple[str, ...]:
    """Split typed IDs into a normalized tuple

    Separators are commas, semicolons or whitespace; empty items are dropped,
    IDs are upper-cased and duplicates removed, keeping the first occurrence.
    Format, count and existence are not checked here — that is the engine's job.

    Args:
        text: IDs as typed, e.g. " p1, P2;P2 p3 ".

    Returns:
        The IDs in typed order, e.g. ("P1", "P2", "P3").
    """
    ids = (item.upper() for item in _SEPARATORS.split(text) if item)
    return tuple(dict.fromkeys(ids))
