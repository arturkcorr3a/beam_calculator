"""Geometry of the plan view, in meters, resolved by the engine."""

from dataclasses import dataclass

type Point = tuple[float, float]


@dataclass(frozen=True, slots=True)
class PillarShape:
    """A pillar section centered at (x_m, y_m)"""

    id: str
    x_m: float
    y_m: float
    width_m: float
    depth_m: float


@dataclass(frozen=True, slots=True)
class BeamShape:
    """A beam band, or a fallback line when the engine could not resolve it

    Attributes:
        rect_m: (x0, y0, x1, y1) of the real band (bw and alignment), or None.
        fallback_line_m: Centers of the existing pillars, used when rect_m is None.
        axis_key: "X" or "Y" when resolved, otherwise None.
        label_m: Where to label the beam: the middle of its longest span, so the
            ID does not land on an interior pillar; None if nothing is drawn.
    """

    id: str
    rect_m: tuple[float, float, float, float] | None
    fallback_line_m: tuple[Point, ...]
    axis_key: str | None
    label_m: Point | None = None


@dataclass(frozen=True, slots=True)
class SlabShape:
    """A slab region out to the centerlines of its supporting beams

    Attributes:
        polygon_m: Corners counter-clockwise (an edge without a resolved beam runs
            through the pillar centers), or None if a corner pillar is missing.
        usage_key: Engine usage description.
        lowered_cm: Lowering below the floor level (cm); 0 when not lowered.
    """

    id: str
    polygon_m: tuple[Point, ...] | None
    usage_key: str
    lowered_cm: int = 0


@dataclass(frozen=True, slots=True)
class PlanGeometry:
    """Everything the plan draws, always consistent with the records"""

    pillars: tuple[PillarShape, ...] = ()
    beams: tuple[BeamShape, ...] = ()
    slabs: tuple[SlabShape, ...] = ()
