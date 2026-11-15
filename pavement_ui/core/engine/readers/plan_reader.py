"""Resolve the plan geometry: each beam independently, so the plan stays drawable
even when the structure is invalid."""

import math
from typing import cast

from pavement_ui.core.engine.keys import m_from_cm
from pavement_ui.core.model.pavement_records import PavementRecords
from pavement_ui.core.model.records import PillarRecord
from pavement_ui.core.results.plan_geometry import (
    BeamShape,
    PillarShape,
    PlanGeometry,
    Point,
    SlabShape,
)
from src.pavement_elements.continuous_beam import ContinuousBeam
from src.pavement_elements.geometry_utils import Axis
from src.pavement_elements.pavement import Pavement
from src.pavement_elements.pillar import Pillar


def _pillar_shape(record: PillarRecord) -> PillarShape:
    return PillarShape(
        record.id,
        record.x_m,
        record.y_m,
        m_from_cm(record.width_cm),
        m_from_cm(record.depth_cm),
    )


def _band(
    beam: ContinuousBeam, pillars: dict[str, Pillar]
) -> tuple[float, float, float, float]:
    """The resolved beam band (m): first to last pillar along the axis, centerline ± bw/2."""
    first, last = pillars[beam.pillar_ids[0]], pillars[beam.pillar_ids[-1]]
    centerline = cast(float, beam.centerline)
    low, high = centerline - beam.width / 2, centerline + beam.width / 2
    if beam.axis == Axis.X:
        x0, y0, x1, y1 = first.x, low, last.x, high
    else:
        x0, y0, x1, y1 = low, first.y, high, last.y
    return (m_from_cm(x0), m_from_cm(y0), m_from_cm(x1), m_from_cm(y1))


def _longest_segment_middle(points: list[Point]) -> Point | None:
    """Middle of the longest segment of a polyline (m)."""
    if len(points) < 2:
        return None
    a, b = max(
        zip(points, points[1:], strict=False),
        key=lambda seg: math.dist(seg[0], seg[1]),
    )
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def _beam_shape(beam: ContinuousBeam, pillars: dict[str, Pillar]) -> BeamShape:
    try:
        beam.resolve_and_validate(pillars)
    except ValueError:
        line = [
            (m_from_cm(pillars[pid].x), m_from_cm(pillars[pid].y))
            for pid in beam.pillar_ids
            if pid in pillars
        ]
        return BeamShape(
            beam.id, None, tuple(line), None, _longest_segment_middle(line)
        )
    axis = cast(Axis, beam.axis)
    centerline = m_from_cm(cast(float, beam.centerline))
    stops = [pillars[pid] for pid in beam.pillar_ids]  # sorted along the axis
    if axis == Axis.X:
        axis_points = [(m_from_cm(p.x), centerline) for p in stops]
    else:
        axis_points = [(centerline, m_from_cm(p.y)) for p in stops]
    return BeamShape(
        beam.id,
        _band(beam, pillars),
        (),
        axis.value,
        _longest_segment_middle(axis_points),
    )


def _counter_clockwise(points: list[Point]) -> tuple[Point, ...]:
    """Order points counter-clockwise around their centroid (for drawing only)."""
    cx = sum(x for x, _ in points) / len(points)
    cy = sum(y for _, y in points) / len(points)
    return tuple(sorted(points, key=lambda p: math.atan2(p[1] - cy, p[0] - cx)))


def read_plan(records: PavementRecords, pavement: Pavement) -> PlanGeometry:
    """Build the plan of the records, using a freshly built, unresolved pavement

    Args:
        records: What the user registered.
        pavement: Built from records; its beams are resolved here, one by one.
    """
    pillars = pavement.pillars
    slabs: list[SlabShape] = []
    for record in records.slabs:
        corners = [pillars[c] for c in record.corner_ids if c in pillars]
        polygon = None
        if len(corners) == 4 == len(record.corner_ids):
            polygon = _counter_clockwise(
                [(m_from_cm(p.x), m_from_cm(p.y)) for p in corners]
            )
        slabs.append(SlabShape(record.id, polygon, record.usage_key, record.lowered_cm))
    return PlanGeometry(
        pillars=tuple(_pillar_shape(r) for r in records.pillars),
        beams=tuple(_beam_shape(b, pillars) for b in pavement.beams.values()),
        slabs=tuple(slabs),
    )
