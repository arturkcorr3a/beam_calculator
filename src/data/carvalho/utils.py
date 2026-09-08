"""Shared interpolation utilities for Carvalho table lookups."""

from typing import Protocol, Sequence, TypeVar


class HasAspectRatio(Protocol):
    @property
    def aspect_ratio(self) -> float: ...


E = TypeVar("E", bound=HasAspectRatio)


def find_bracket_and_fraction(
    entries: Sequence[E],
    lambda_val: float,
) -> tuple[E, E, float]:
    """Return the bracketing entries and linear interpolation fraction for lambda_val.

    Assumes entries are sorted by aspect_ratio in ascending order and that
    lambda_val lies within the range covered by entries.
    """
    idx = 0
    while idx < len(entries) - 1 and entries[idx + 1].aspect_ratio < lambda_val:
        idx += 1
    lower = entries[idx]
    upper = entries[idx + 1]
    t = (lambda_val - lower.aspect_ratio) / (upper.aspect_ratio - lower.aspect_ratio)
    return lower, upper, t
