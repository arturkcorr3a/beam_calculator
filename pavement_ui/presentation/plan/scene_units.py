"""Plan geometry (m) → scene coordinates (cm, the engine's unit)."""

from PySide6.QtCore import QPointF, QRectF

from pavement_ui.core.results.plan_geometry import PlanGeometry, Point

SCENE_UNITS_PER_M = 100.0


def to_scene(value_m: float) -> float:
    """Convert a length from meters to scene units (cm)"""
    return value_m * SCENE_UNITS_PER_M


def to_meters(value_scene: float) -> float:
    """Convert a length from scene units (cm) to meters"""
    return value_scene / SCENE_UNITS_PER_M


def point(x_m: float, y_m: float) -> QPointF:
    """A plan point in scene coordinates"""
    return QPointF(to_scene(x_m), to_scene(y_m))


def rect_from_corners_m(x0: float, y0: float, x1: float, y1: float) -> QRectF:
    """The normalized scene rectangle between two corners given in meters"""
    return QRectF(point(x0, y0), point(x1, y1)).normalized()


def _points_m(geometry: PlanGeometry) -> list[Point]:
    points: list[Point] = []
    for p in geometry.pillars:
        half_w, half_d = p.width_m / 2, p.depth_m / 2
        points += [(p.x_m - half_w, p.y_m - half_d), (p.x_m + half_w, p.y_m + half_d)]
    for beam in geometry.beams:
        if beam.rect_m is not None:
            x0, y0, x1, y1 = beam.rect_m
            points += [(x0, y0), (x1, y1)]
        points += list(beam.fallback_line_m)
    return points


def geometry_bounds(geometry: PlanGeometry) -> QRectF | None:
    """Scene rectangle enclosing every pillar and beam, or None for an empty plan"""
    points = _points_m(geometry)
    if not points:
        return None
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    return rect_from_corners_m(min(xs), min(ys), max(xs), max(ys))
