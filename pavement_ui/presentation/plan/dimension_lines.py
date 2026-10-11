"""Automatic dimension lines between pillar coordinates — pure, no Qt."""

from collections.abc import Sequence
from dataclasses import dataclass

from pavement_ui.core.results.plan_geometry import PillarShape

_SAME_COORDINATE_M = 0.01  # coordinates closer than 1 cm share a dimension stop
_OFFSET_M = 0.8  # distance from the pillar envelope to the dimension line


@dataclass(frozen=True, slots=True)
class DimensionSegment:
    """One dimension between two coordinates (m)

    Attributes:
        start_m: First coordinate along the measured axis.
        end_m: Second coordinate along the measured axis.
        position_m: Coordinate of the line on the other axis.
        horizontal: True for X distances (line below), False for Y (line at left).
    """

    start_m: float
    end_m: float
    position_m: float
    horizontal: bool

    @property
    def length_m(self) -> float:
        return self.end_m - self.start_m


def _distinct(values: Sequence[float]) -> list[float]:
    stops: list[float] = []
    for value in sorted(values):
        if not stops or value - stops[-1] > _SAME_COORDINATE_M:
            stops.append(value)
    return stops


def _chain(
    stops: list[float], position_m: float, horizontal: bool
) -> list[DimensionSegment]:
    return [
        DimensionSegment(a, b, position_m, horizontal)
        for a, b in zip(stops, stops[1:], strict=False)
    ]


def dimension_segments(pillars: Sequence[PillarShape]) -> list[DimensionSegment]:
    """Dimensions between distinct pillar X (below the set) and Y (left of it)"""
    if not pillars:
        return []
    bottom = min(p.y_m - p.depth_m / 2 for p in pillars) - _OFFSET_M
    left = min(p.x_m - p.width_m / 2 for p in pillars) - _OFFSET_M
    return [
        *_chain(_distinct([p.x_m for p in pillars]), bottom, True),
        *_chain(_distinct([p.y_m for p in pillars]), left, False),
    ]
