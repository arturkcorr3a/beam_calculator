"""One source of the distributed load on a beam span."""

from dataclasses import dataclass
from enum import StrEnum


class LoadKind(StrEnum):
    """Where a span load comes from"""

    OWN_WEIGHT = "own_weight"
    WALL = "wall"
    SLAB = "slab"


@dataclass(frozen=True, slots=True)
class LoadComponent:
    """A uniform load applied to a span, kept apart from the span totals

    Attributes:
        kind: Source of the load.
        source_id: ID of the slab that reacts on the span; None for the beam's
            own weight and wall.
        permanent: Permanent part of the load (kN/m).
        variable: Variable part of the load (kN/m).
    """

    kind: LoadKind
    source_id: str | None
    permanent: float
    variable: float = 0.0
