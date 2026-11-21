from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from src.errors import BeamInputError, InputError

if TYPE_CHECKING:
    from src.pavement_elements.pillar import Pillar

TOLERANCE = 0.001  # cm


class Axis(Enum):
    X = "X"  # horizontal beam — varies in x, perpendicular axis is y
    Y = "Y"  # vertical beam   — varies in y, perpendicular axis is x


class Alignment(Enum):
    TOP = "top"  # horizontal beam: beam top flush with pillar top face
    BOTTOM = "bottom"  # horizontal beam: beam bottom flush with pillar bottom face
    CENTER = "center"  # beam centerline through pillar center (works for both axes)
    LEFT = "left"  # vertical beam: beam left face flush with pillar left face
    RIGHT = "right"  # vertical beam: beam right face flush with pillar right face

    def validate(self, axis: Axis) -> None:
        """Raises ValueError if the alignment is not valid for the given axis."""
        horizontal_alignments = {Alignment.TOP, Alignment.CENTER, Alignment.BOTTOM}
        vertical_alignments = {Alignment.LEFT, Alignment.CENTER, Alignment.RIGHT}
        if axis == Axis.X and self not in horizontal_alignments:
            raise BeamInputError(
                f"Alignment '{self.value}' is not valid for horizontal (X-axis) beams."
            )
        if axis == Axis.Y and self not in vertical_alignments:
            raise BeamInputError(
                f"Alignment '{self.value}' is not valid for vertical (Y-axis) beams."
            )

    @staticmethod
    def get_horizontal() -> set[Alignment]:
        return {Alignment.TOP, Alignment.CENTER, Alignment.BOTTOM}

    @staticmethod
    def get_vertical() -> set[Alignment]:
        return {Alignment.LEFT, Alignment.CENTER, Alignment.RIGHT}


def between(value: float, low: float, high: float) -> bool:
    """Evaluates if value is between low and high, inclusive, with a tolerance."""
    return low - TOLERANCE <= value <= high + TOLERANCE


def ranges_overlap(range_1: tuple[float, float], range_2: tuple[float, float]) -> bool:
    """Evaluate whether two closed (low, high) ranges overlap, inclusive, with a tolerance."""
    low_1, high_1 = range_1
    low_2, high_2 = range_2
    return low_1 <= high_2 + TOLERANCE and high_1 >= low_2 - TOLERANCE


def get_pillar_perpendicular_range(pillar: Pillar, axis: Axis) -> tuple[float, float]:
    """
    Returns (low, high) of the pillar's cross-section extent perpendicular to a given axis.

    For an X-beam the perpendicular axis is Y, so we return y range.
    For a Y-beam the perpendicular axis is X, so we return x range.
    """
    if axis == Axis.X:
        return pillar.get_y_range()
    else:
        return pillar.get_x_range()


def effective_span(
    axis_distance: float,
    support_width_1: float,
    support_width_2: float,
    height: float,
) -> float:
    """Compute the effective span of a beam or slab between two supports

    The effective span is l_ef = l0 + a1 + a2, where l0 is the clear span between the support faces and a_i = min(t_i / 2, 0.3 h). The 0.3 h cap keeps the theoretical support from drifting too far into wide supports.

    Args:
        axis_distance: Distance between the support centroids (cm).
        support_width_1: Width t1 of the first support along the span direction (cm).
        support_width_2: Width t2 of the second support along the span direction (cm).
        height: Structural height h of the element — beam height or slab
            thickness (cm). Must be positive.

    Returns:
        Effective span l_ef (cm).

    Raises:
        InputError: If height is not positive or the supports leave no clear span.

    References:
        ABNT NBR 6118:2014 — Section 14.6.2.4 (beams), Section 14.7.2.2 (slabs), Figure 14.5
    """
    if height <= 0:
        raise InputError(f"Height must be positive. Got {height} cm.")
    clear_span = axis_distance - support_width_1 / 2 - support_width_2 / 2
    if clear_span <= 0:
        raise InputError(
            f"Supports leave no clear span: axis distance {axis_distance} cm, "
            f"support widths {support_width_1} cm and {support_width_2} cm."
        )

    # NOTE the 0.3 * h cap is disabled for now; phrasing on NBR 6118 allows for it to not be applies (can x have to); I am disabling it for now to avoid mismatching between structural beam and real beam
    a1 = support_width_1 / 2 # min(support_width_1 / 2, 0.3 * height)
    a2 = support_width_2 / 2 # min(support_width_2 / 2, 0.3 * height)
    return clear_span + a1 + a2


def round_up_to_multiple_of_5(value: float) -> int:
    """Rounds value up to the nearest multiple of 5."""
    return math.ceil(value / 5) * 5


def x_coord(pillar: Pillar) -> float:
    return pillar.x


def y_coord(pillar: Pillar) -> float:
    return pillar.y


@dataclass
class Point:
    x: float
    y: float


def calculate_polygon_area(vertices: list[Point]) -> float:
    """Calculates the polygon area from its vertices."""
    area = 0.0
    n = len(vertices)
    for i in range(n):
        j = (i + 1) % n
        area += vertices[i].x * vertices[j].y - vertices[j].x * vertices[i].y
    return abs(area) / 2.0
