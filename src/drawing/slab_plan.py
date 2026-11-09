"""Slab drawings for the design report: the plan, and the supports with the yield lines

Model space is in cm. The plan uses the pavement's coordinates; the supports drawing
uses the slab's effective rectangle, with the origin at its bottom left corner, as
the influence areas do.
"""

from math import hypot
from typing import cast

from src.drawing.annotations import dimension, vertical_dimension
from src.drawing.config import DEFAULT_CONFIG, DrawingConfig
from src.drawing.formatting import fmt_dec, fmt_len
from src.drawing.layers import (
    BEAM_OUTLINE,
    DIMENSION,
    PILLAR,
    SLAB_OUTLINE,
    SLAB_SUPPORT,
    TEXT,
    YIELD_LINE,
)
from src.drawing.primitives import Drawing, HAlign, Line, Point, Polyline, Text, VAlign
from src.pavement_elements.pillar import Pillar
from src.pavement_elements.slab import CORNER_EDGE_DICT, Slab
from src.pavement_elements.slab_edge import Edges

M_TO_CM = 100.0
_LABEL_GAP_MM = 2.0  # from a beam band to its name
_DIMENSION_GAP_MM = 9.0  # from a beam band, or the slab's edge, to a dimension line
_LINE_PITCH = 1.6  # between the baselines of two stacked texts, in text heights
_HATCH_PITCH_MM = 2.0  # between the hatch ticks of a fixed edge
_HATCH_LENGTH_MM = 1.5  # of each hatch tick, along both directions
_TOLERANCE = 1e-6  # cm

# Each edge's corners, as fractions of (lx, ly), counter-clockwise like the regions
_EDGE_ENDS: dict[Edges, tuple[Point, Point]] = {
    Edges.BOTTOM: ((0.0, 0.0), (1.0, 0.0)),
    Edges.RIGHT: ((1.0, 0.0), (1.0, 1.0)),
    Edges.TOP: ((1.0, 1.0), (0.0, 1.0)),
    Edges.LEFT: ((0.0, 1.0), (0.0, 0.0)),
}


def _rectangle(
    left: float, bottom: float, right: float, top: float, layer: str
) -> Polyline:
    """Return a closed rectangle"""
    return Polyline(
        ((left, bottom), (right, bottom), (right, top), (left, top)),
        (0.0,) * 4,
        layer,
        closed=True,
    )


def _band(slab: Slab, edge: Edges) -> tuple[float, float, float, float]:
    """Return the edge beam's band between the slab's corner pillars: left, bottom, right, top (cm)"""
    beam = slab.edges[edge].beam
    centerline = cast(float, beam.centerline)
    low, high = centerline - beam.width / 2, centerline + beam.width / 2
    first, second = (slab.corners_pillar_dict[key] for key in CORNER_EDGE_DICT[edge])
    if edge in (Edges.BOTTOM, Edges.TOP):
        return (min(first.x, second.x), low, max(first.x, second.x), high)
    return (low, min(first.y, second.y), high, max(first.y, second.y))


def _slab_pillars(slab: Slab, pillars: dict[str, Pillar]) -> list[Pillar]:
    """Return the pillars on the slab's outline: corners and any along its edges"""
    corners = slab.corners_pillar_dict.values()
    x0, x1 = min(p.x for p in corners), max(p.x for p in corners)
    y0, y1 = min(p.y for p in corners), max(p.y for p in corners)
    return [
        pillar
        for pillar in pillars.values()
        if x0 - _TOLERANCE <= pillar.x <= x1 + _TOLERANCE
        and y0 - _TOLERANCE <= pillar.y <= y1 + _TOLERANCE
        and (
            min(abs(pillar.x - x0), abs(pillar.x - x1)) <= _TOLERANCE
            or min(abs(pillar.y - y0), abs(pillar.y - y1)) <= _TOLERANCE
        )
    ]


def _beam_label(
    edge: Edges,
    band: tuple[float, float, float, float],
    name: str,
    height: float,
    gap: float,
) -> Text:
    """Return a beam's name outside its band, turned along vertical bands"""
    left, bottom, right, top = band
    middle_x, middle_y = (left + right) / 2, (bottom + top) / 2
    match edge:
        case Edges.BOTTOM:
            return Text(
                (middle_x, bottom - gap), name, height, TEXT, HAlign.CENTER, VAlign.TOP
            )
        case Edges.TOP:
            return Text((middle_x, top + gap), name, height, TEXT, HAlign.CENTER)
        case Edges.LEFT:
            return Text(
                (left - gap, middle_y), name, height, TEXT, HAlign.CENTER, rotation=90.0
            )
        case Edges.RIGHT:
            return Text(
                (right + gap, middle_y),
                name,
                height,
                TEXT,
                HAlign.CENTER,
                VAlign.TOP,
                90.0,
            )


def _pillar(
    pillar: Pillar, center: Point, height: float, gap: float
) -> list[Polyline | Text]:
    """Return a pillar's outline and its name, off the corner farthest from the slab's center"""
    half_width, half_depth = pillar.width / 2, pillar.depth / 2
    east, north = pillar.x >= center[0], pillar.y >= center[1]
    corner = (
        pillar.x + (half_width if east else -half_width),
        pillar.y + (half_depth if north else -half_depth),
    )
    return [
        _rectangle(
            pillar.x - half_width,
            pillar.y - half_depth,
            pillar.x + half_width,
            pillar.y + half_depth,
            PILLAR,
        ),
        Text(
            (corner[0] + (gap if east else -gap), corner[1] + (gap if north else -gap)),
            pillar.id,
            height,
            TEXT,
            HAlign.LEFT if east else HAlign.RIGHT,
            VAlign.BASELINE if north else VAlign.TOP,
        ),
    ]


def build_slab_plan(
    slab: Slab, pillars: dict[str, Pillar], config: DrawingConfig = DEFAULT_CONFIG
) -> Drawing:
    """Return the slab's plan: outline, edge beams, pillars, names and the lx and ly dimensions

    Args:
        slab: A resolved slab.
        pillars: The pavement's pillars, by ID.
    """
    paper = config.paper
    label = paper(config.text_heights_mm.label)
    small = paper(config.text_heights_mm.small)
    bands = {edge: _band(slab, edge) for edge in Edges}
    drawing = Drawing(
        [
            _rectangle(
                bands[Edges.LEFT][2],
                bands[Edges.BOTTOM][3],
                bands[Edges.RIGHT][0],
                bands[Edges.TOP][1],
                SLAB_OUTLINE,
            )
        ]
    )
    for edge, band in bands.items():
        drawing.add(
            _rectangle(*band, BEAM_OUTLINE),
            _beam_label(
                edge, band, slab.edges[edge].beam.id, small, paper(_LABEL_GAP_MM)
            ),
        )
    lx, ly = slab.dimensions
    x0 = cast(float, slab.edges[Edges.LEFT].beam.centerline)
    y0 = cast(float, slab.edges[Edges.BOTTOM].beam.centerline)
    center = (x0 + lx / 2, y0 + ly / 2)
    for pillar in _slab_pillars(slab, pillars):
        drawing.add(*_pillar(pillar, center, small, paper(_LABEL_GAP_MM) / 2))
    drawing.add(
        Text(center, slab.id, label, TEXT, HAlign.CENTER),
        Text(
            (center[0], center[1] - _LINE_PITCH * label),
            f"h = {fmt_len(slab.thickness)} cm",
            small,
            TEXT,
            HAlign.CENTER,
        ),
    )
    drawing.extend(
        dimension(
            x0,
            x0 + lx,
            bands[Edges.BOTTOM][1] - paper(_DIMENSION_GAP_MM),
            DIMENSION,
            config,
            below=f"lx = {fmt_len(lx)}",
        )
    )
    drawing.extend(
        vertical_dimension(
            bands[Edges.LEFT][0] - paper(_DIMENSION_GAP_MM),
            y0,
            y0 + ly,
            DIMENSION,
            config,
            f"ly = {fmt_len(ly)}",
        )
    )
    return drawing


def _hatch(start: Point, end: Point, config: DrawingConfig) -> list[Line]:
    """Return the 45° ticks outside a fixed edge, run counter-clockwise around the slab"""
    (x0, y0), (x1, y1) = start, end
    length = hypot(x1 - x0, y1 - y0)
    tx, ty = (x1 - x0) / length, (y1 - y0) / length
    nx, ny = ty, -tx  # outward: right of a counter-clockwise run
    tick = config.paper(_HATCH_LENGTH_MM)
    count = max(int(length / config.paper(_HATCH_PITCH_MM)), 1)
    lines: list[Line] = []
    for index in range(count + 1):
        px, py = x0 + tx * length * index / count, y0 + ty * length * index / count
        lines.append(
            Line((px, py), (px + (nx + tx) * tick, py + (ny + ty) * tick), SLAB_SUPPORT)
        )
    return lines


def _on_boundary(start: Point, end: Point, lx: float, ly: float) -> bool:
    """Return whether a segment lies on the slab's rectangle"""
    for index, limit in ((0, 0.0), (0, lx), (1, 0.0), (1, ly)):
        if (
            abs(start[index] - limit) <= _TOLERANCE
            and abs(end[index] - limit) <= _TOLERANCE
        ):
            return True
    return False


def _yield_lines(regions: list[tuple[Point, ...]], lx: float, ly: float) -> list[Line]:
    """Return the regions' sides inside the slab, each once, leaving out zero-length ones"""
    seen: set[tuple[Point, Point]] = set()
    lines: list[Line] = []
    for polygon in regions:
        for start, end in zip(polygon, polygon[1:] + polygon[:1], strict=True):
            low, high = sorted((_rounded(start), _rounded(end)))
            if low == high or _on_boundary(start, end, lx, ly) or (low, high) in seen:
                continue
            seen.add((low, high))
            lines.append(Line(start, end, YIELD_LINE))
    return lines


def _rounded(point: Point) -> Point:
    """Return a point rounded to 1e-4 cm, to match shared sides"""
    return (round(point[0], 4), round(point[1], 4))


def build_slab_supports(slab: Slab, config: DrawingConfig = DEFAULT_CONFIG) -> Drawing:
    """Return the slab's support conditions and yield lines, with each edge's area

    Every edge is a line; fixed edges get hatch ticks outside. The yield lines split
    the effective rectangle into the edges' regions, each labelled with its beam and
    its area. Edges that carry no load (short edges of one-way slabs) have no region.

    Args:
        slab: A slab whose influence areas are resolved.
    """
    paper = config.paper
    label = paper(config.text_heights_mm.label)
    small = paper(config.text_heights_mm.small)
    lx, ly = slab.effective_dimensions
    drawing = Drawing()
    regions: list[tuple[Point, ...]] = []
    for edge, ((fx0, fy0), (fx1, fy1)) in _EDGE_ENDS.items():
        slab_edge = slab.edges[edge]
        start, end = (fx0 * lx, fy0 * ly), (fx1 * lx, fy1 * ly)
        drawing.add(Line(start, end, SLAB_SUPPORT))
        if slab_edge.support_condition == "fixed":
            drawing.add(*_hatch(start, end, config))
        if not slab_edge.influence_polygon:
            continue
        polygon = tuple(
            (p.x * M_TO_CM, p.y * M_TO_CM) for p in slab_edge.influence_polygon
        )
        regions.append(polygon)
        cx = sum(x for x, _ in polygon) / len(polygon)
        cy = sum(y for _, y in polygon) / len(polygon)
        drawing.add(
            Text((cx, cy), slab_edge.beam.id, label, TEXT, HAlign.CENTER),
            Text(
                (cx, cy - _LINE_PITCH * small),
                f"{fmt_dec(slab_edge.influence_area, 2)} m²",
                small,
                TEXT,
                HAlign.CENTER,
            ),
        )
    drawing.add(*_yield_lines(regions, lx, ly))
    drawing.extend(
        dimension(
            0.0,
            lx,
            -paper(_DIMENSION_GAP_MM),
            DIMENSION,
            config,
            below=f"lx,ef = {fmt_len(lx)}",
        )
    )
    drawing.extend(
        vertical_dimension(
            -paper(_DIMENSION_GAP_MM),
            0.0,
            ly,
            DIMENSION,
            config,
            f"ly,ef = {fmt_len(ly)}",
        )
    )
    return drawing
