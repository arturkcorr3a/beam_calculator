from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

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
            raise ValueError(
                f"Alignment '{self.value}' is not valid for horizontal (X-axis) beams."
            )
        if axis == Axis.Y and self not in vertical_alignments:
            raise ValueError(
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
