"""Cross sections and shapes, right of the elevation (spec §6.7 and §6.8)

The sections and the shapes are drawn at the section scale (1:25) on the 1:50 sheet: their
geometry is magnified by ``DrawingConfig.section_magnification``, while their texts keep
the sheet's paper heights.
"""

from dataclasses import dataclass
from math import sqrt

from src.detailing.detailed_bar import DetailedBar
from src.detailing.detailed_clamps import DetailedClamps
from src.detailing.detailing_beam import DetailingBeam
from src.detailing.span_stirrups import SpanStirrups
from src.drawing.annotations import dimension, vertical_dimension
from src.drawing.config import MM_PER_CM, DrawingConfig
from src.drawing.formatting import (
    cut_length_label,
    fmt_len,
    scale_label,
    section_letter,
    section_piece_label,
    section_title,
    spacing_label,
    text_width,
)
from src.drawing.geometry import (
    arrange_row,
    clamp_rows_y,
    row_offsets,
    section_layers,
    section_positions,
    stirrup_bend,
)
from src.drawing.layers import (
    BEAM_OUTLINE,
    CLAMP,
    DIMENSION,
    SECTION_BAR,
    STIRRUP,
    TEXT,
)
from src.drawing.primitives import (
    Circle,
    Drawing,
    HAlign,
    Line,
    Point,
    Polyline,
    Text,
    VAlign,
)
from src.reinforcement.stirrups import StirrupZone

_FIRST_SECTION_MM = 15.0  # from the beam's end to the first section's left dimension
_AXIS_ROW_MM = 19.0  # the sections' tops line up with the axis dimension row
_SIDE_DIMENSION_MM = 3.0  # from a section's face to its dimension lines
_SIDE_ROOM_MM = 4.0  # room on each side of a section
_LABEL_GAP_MM = 4.0  # from a section's right face to its labels
_LEADER_GAP_MM = 1.0  # between a leader's end and its label
_SECTION_SPACING_MM = 8.0  # after a section's widest label
_LABEL_PITCH = 1.6  # least distance between two labels, in text heights
_TITLE_ABOVE_MM = 6.0
_SCALE_BELOW_TITLE_MM = 3.2
_MIN_BAR_RADIUS_MM = 0.35
_CLOSING_OFFSET_MM = 0.6  # from the stirrup's corner to where its hooks start
_SHAPES_BELOW_MM = 18.0  # from the lowest section item to the shapes' title
_SHAPES_TITLE_GAP_MM = 8.0  # from the shapes' title to the first row of shapes
_SHAPE_SPACING_MM = 10.0
_SHAPE_TEXT_GAP_MM = 3.0
_SHAPE_LINE_GAP_MM = 0.6  # half the gap between the two text lines of a shape


@dataclass(frozen=True)
class SectionPoint:
    """One bar or clamp leg crossing a section

    Attributes:
        u: Offset from the section's center (cm).
        y: Height from the section's bottom face (cm).
        diameter_mm: Bar diameter φ (mm).
    """

    source: DetailedBar | DetailedClamps
    u: float
    y: float
    diameter_mm: float


@dataclass(frozen=True)
class SectionsBlock:
    """The sections and the shapes of a beam

    Attributes:
        left: Left end of the block (cm).
        right: Right end of the block (cm).
    """

    drawing: Drawing
    left: float
    right: float


def section_cuts(beam: DetailingBeam, config: DrawingConfig) -> list[tuple[str, float]]:
    """Return the letter and the position of each cross section, left to right (cm)"""
    return [
        (section_letter(index), x)
        for index, x in enumerate(section_positions(beam, config))
    ]


def stirrups_at(beam: DetailingBeam, x: float) -> SpanStirrups | None:
    """Return the stirrups of the span holding a position, or None inside a pillar"""
    return next((span for span in beam.stirrups if span.start <= x <= span.end), None)


def section_points(beam: DetailingBeam, x: float) -> list[SectionPoint]:
    """Return every bar and clamp leg crossing a section, as offsets and heights (cm)

    The bars of each layer go in the order of ``arrange_row``, spread by ``row_offsets`` between the stirrup's inner faces; the clamps whose legs cover the section put a leg in each inner corner.
    """
    stirrups = stirrups_at(beam, x)
    stirrup_diameter = 0.0 if stirrups is None else stirrups.diameter_mm / MM_PER_CM
    outer_width = (
        beam.width - 2 * beam.nominal_covering
        if stirrups is None
        else stirrups.outer_width
    )
    inner_width = outer_width - 2 * stirrup_diameter  # cm
    points: list[SectionPoint] = []
    for is_bottom in (False, True):
        for _, runs in sorted(section_layers(beam, x, is_bottom).items()):
            row = arrange_row(runs)
            for bar, u in zip(row, row_offsets(row, inner_width), strict=True):
                points.append(SectionPoint(bar, u, bar.y, bar.diameter_mm))
    for clamps in beam.clamps:
        tip = clamps.position + (
            clamps.leg_length if clamps.left else -clamps.leg_length
        )
        if min(clamps.position, tip) <= x <= max(clamps.position, tip):
            offset = (clamps.width - clamps.diameter_mm / MM_PER_CM) / 2  # cm
            for y in clamp_rows_y(beam, clamps):
                points += [
                    SectionPoint(clamps, -offset, y, clamps.diameter_mm),
                    SectionPoint(clamps, offset, y, clamps.diameter_mm),
                ]
    return points


def _closing_hooks(
    corner: Point, tip: float, layer: str, config: DrawingConfig
) -> list[Line]:
    """Return the two 45° strokes closing a stirrup at its top left corner

    Args:
        corner: The stirrup's top left corner on the sheet (cm).
        tip: Length of the strokes on the sheet (cm).
    """
    offset = config.paper(_CLOSING_OFFSET_MM)
    step = tip / sqrt(2)
    x, y = corner
    return [
        Line((x + offset, y), (x + offset + step, y - step), layer),
        Line((x, y - offset), (x + step, y - offset - step), layer),
    ]


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


def _label_text(source: DetailedBar | DetailedClamps) -> str:
    """Return the label of a bar run or clamp set in a section, such as 2 N10 φ10"""
    return section_piece_label(source.quantity, str(source.mark), source.diameter_mm)


def section_labels(beam: DetailingBeam, x: float, config: DrawingConfig) -> list[str]:
    """Return the labels of a section: one per bar run and clamp set, and the stirrups'"""
    labels = list(dict.fromkeys(_label_text(p.source) for p in section_points(beam, x)))
    stirrups = stirrups_at(beam, x)
    if stirrups is not None:
        labels.append(spacing_label(str(stirrups.mark), _zone_at(stirrups, x).spacing))
    return labels


def _zone_at(stirrups: SpanStirrups, x: float) -> StirrupZone:
    """Return the stirrup zone holding a position; the last one past the end"""
    return next(
        (zone for zone in stirrups.zones if zone.start <= x <= zone.end),
        stirrups.zones[-1],
    )


def draw_section(
    beam: DetailingBeam,
    x: float,
    letter: str,
    origin: Point,
    config: DrawingConfig,
) -> Drawing:
    """Return one cross section with its stirrup, bars, labels, dimensions and title

    Args:
        x: Position of the cut along the beam (cm).
        origin: Where the section's bottom left corner goes on the sheet (cm).
    """
    m = config.section_magnification
    sx, sy = origin
    b, h = beam.width, beam.height
    small = config.paper(config.text_heights_mm.small)

    def place(u: float, y: float) -> Point:
        return (sx + m * (b / 2 + u), sy + m * y)

    drawing = Drawing([_rectangle(sx, sy, sx + m * b, sy + m * h, BEAM_OUTLINE)])
    labels: list[tuple[float, str, Point]] = []  # height, text, leader start
    stirrups = stirrups_at(beam, x)
    if stirrups is not None:
        diameter = stirrups.diameter_mm / MM_PER_CM  # cm
        half_width = (stirrups.outer_width - diameter) / 2
        bottom = (h - stirrups.outer_height + diameter) / 2
        top = h - bottom
        left_bottom = place(-half_width, bottom)
        right_top = place(half_width, top)
        drawing.add(
            _rectangle(*left_bottom, *right_top, STIRRUP),
            *_closing_hooks(
                (left_bottom[0], right_top[1]),
                m * stirrup_bend(stirrups)[1],
                STIRRUP,
                config,
            ),
        )
        labels.append(
            (
                sy + m * h / 2,
                spacing_label(str(stirrups.mark), _zone_at(stirrups, x).spacing),
                place(half_width, h / 2),
            )
        )
    rightmost: dict[int, tuple[SectionPoint, Point]] = {}
    for point in section_points(beam, x):
        center = place(point.u, point.y)
        radius = max(
            m * point.diameter_mm / MM_PER_CM / 2, config.paper(_MIN_BAR_RADIUS_MM)
        )
        drawing.add(Circle(center, radius, SECTION_BAR, filled=True))
        key = id(point.source)
        if key not in rightmost or center[0] > rightmost[key][1][0]:
            rightmost[key] = (point, (center[0] + radius, center[1]))
    for point, start in rightmost.values():
        labels.append((start[1], _label_text(point.source), start))
    label_x = sx + m * b + config.paper(_LABEL_GAP_MM)
    drawing.extend(_stacked_labels(labels, label_x, small, sy + m * h, config))
    drawing.extend(
        _section_annotations(
            origin,
            b,
            h,
            config,
            section_title(letter),
            scale_label(config.section_scale),
        )
    )
    return drawing


def draw_plain_section(
    width: float,
    height: float,
    origin: Point,
    config: DrawingConfig,
    title: str | None = None,
) -> Drawing:
    """Return a cross section without reinforcement: outline, b and h dimensions and an optional title

    Args:
        width: Section width b (cm).
        height: Section height h (cm).
        origin: Where the section's bottom left corner goes on the sheet (cm).
    """
    m = config.section_magnification
    sx, sy = origin
    drawing = Drawing(
        [_rectangle(sx, sy, sx + m * width, sy + m * height, BEAM_OUTLINE)]
    )
    drawing.extend(_section_annotations(origin, width, height, config, title))
    return drawing


def _section_annotations(
    origin: Point,
    b: float,
    h: float,
    config: DrawingConfig,
    title: str | None,
    subtitle: str | None = None,
) -> Drawing:
    """Return a section's b and h dimensions and its title, if any, with an optional line under it

    Args:
        origin: The section's bottom left corner on the sheet (cm).
        b: Section width (cm).
        h: Section height (cm).
    """
    m = config.section_magnification
    sx, sy = origin
    drawing = Drawing()
    drawing.extend(
        dimension(
            sx,
            sx + m * b,
            sy - config.paper(_SIDE_DIMENSION_MM),
            DIMENSION,
            config,
            below=fmt_len(b),
        )
    )
    drawing.extend(
        vertical_dimension(
            sx - config.paper(_SIDE_DIMENSION_MM),
            sy,
            sy + m * h,
            DIMENSION,
            config,
            fmt_len(h),
        )
    )
    if title is None:
        return drawing
    title_y = sy + m * h + config.paper(_TITLE_ABOVE_MM)
    middle = sx + m * b / 2
    drawing.add(
        Text(
            (middle, title_y),
            title,
            config.paper(config.text_heights_mm.label),
            TEXT,
            HAlign.CENTER,
        )
    )
    if subtitle is not None:
        drawing.add(
            Text(
                (middle, title_y - config.paper(_SCALE_BELOW_TITLE_MM)),
                subtitle,
                config.paper(config.text_heights_mm.small),
                TEXT,
                HAlign.CENTER,
            )
        )
    return drawing


def _stacked_labels(
    labels: list[tuple[float, str, Point]],
    x: float,
    height: float,
    top: float,
    config: DrawingConfig,
) -> Drawing:
    """Return labels left-aligned at x, each with a leader from its bar

    The labels start at their bar's height and, from the lowest up, are pushed up until their baselines are 1.6 text heights apart. Then, from the highest down, any label above the section's top is pulled down to it, pushing the ones under it down too, so the labels stay clear of the title.

    Args:
        top: Height of the section's top face on the sheet (cm).
    """
    pitch = _LABEL_PITCH * height
    ordered = sorted(labels, key=lambda label: label[0])
    heights: list[float] = []
    for y, _, _ in ordered:
        heights.append(y if not heights else max(y, heights[-1] + pitch))
    cap = top
    for index in reversed(range(len(heights))):
        heights[index] = min(heights[index], cap)
        cap = heights[index] - pitch
    drawing = Drawing()
    for y, (_, text, start) in zip(heights, ordered, strict=True):
        drawing.add(
            Line(start, (x - config.paper(_LEADER_GAP_MM), y), DIMENSION),
            Text((x, y), text, height, TEXT, HAlign.LEFT, VAlign.MIDDLE),
        )
    return drawing


def sections_block(beam: DetailingBeam, config: DrawingConfig) -> SectionsBlock:
    """Return the sections side by side right of the elevation, and the shapes under them"""
    paper = config.paper
    m = config.section_magnification
    small = paper(config.text_heights_mm.small)
    top = beam.height + paper(_AXIS_ROW_MM)
    sy = top - m * beam.height
    sx = beam.end + paper(_FIRST_SECTION_MM) + paper(_SIDE_ROOM_MM)
    left = sx - paper(_SIDE_ROOM_MM)
    drawing = Drawing()
    for letter, x in section_cuts(beam, config):
        drawing.extend(draw_section(beam, x, letter, (sx, sy), config))
        widest = max(
            (text_width(label, small) for label in section_labels(beam, x, config)),
            default=0.0,
        )
        sx += (
            m * beam.width
            + paper(_LABEL_GAP_MM)
            + widest
            + paper(_SECTION_SPACING_MM)
            + paper(_SIDE_ROOM_MM)
        )
    right = drawing.bounds()[2] if drawing.items else left
    shapes_top = (drawing.bounds()[1] if drawing.items else sy) - paper(
        _SHAPES_BELOW_MM
    )
    shapes = shapes_block(beam, left, shapes_top, max(right - left, 0.0), config)
    drawing.extend(shapes)
    return SectionsBlock(drawing, left, max(right, shapes.bounds()[2]))


def _stirrup_shape(
    stirrups: SpanStirrups, quantity: int, config: DrawingConfig
) -> Drawing:
    """Return a stirrup's shape at the origin: outer rectangle, closing strokes, dimensions and texts"""
    m = config.section_magnification
    width, height = m * stirrups.outer_width, m * stirrups.outer_height
    drawing = Drawing(
        [
            _rectangle(0.0, 0.0, width, height, STIRRUP),
            *_closing_hooks(
                (0.0, height), m * stirrup_bend(stirrups)[1], STIRRUP, config
            ),
        ]
    )
    drawing.extend(
        dimension(
            0.0,
            width,
            height + config.paper(_SIDE_DIMENSION_MM),
            DIMENSION,
            config,
            fmt_len(stirrups.outer_width),
        )
    )
    drawing.extend(
        vertical_dimension(
            -config.paper(_SIDE_DIMENSION_MM),
            0.0,
            height,
            DIMENSION,
            config,
            fmt_len(stirrups.outer_height),
        )
    )
    drawing.extend(
        _shape_texts(
            width,
            height / 2,
            section_piece_label(quantity, str(stirrups.mark), stirrups.diameter_mm),
            cut_length_label(stirrups.cut_length),
            config,
        )
    )
    return drawing


def _clamp_shape(
    clamps: DetailedClamps, quantity: int, config: DrawingConfig
) -> Drawing:
    """Return a clamp's shape at the origin: a U lying down, open to the right, with dimensions and texts"""
    m = config.section_magnification
    leg, width = m * clamps.leg_length, m * clamps.width
    drawing = Drawing(
        [
            Polyline(
                ((leg, width), (0.0, width), (0.0, 0.0), (leg, 0.0)),
                (0.0,) * 4,
                CLAMP,
            )
        ]
    )
    drawing.extend(
        dimension(
            0.0,
            leg,
            width + config.paper(_SIDE_DIMENSION_MM),
            DIMENSION,
            config,
            fmt_len(clamps.leg_length),
        )
    )
    drawing.extend(
        vertical_dimension(
            -config.paper(_SIDE_DIMENSION_MM),
            0.0,
            width,
            DIMENSION,
            config,
            fmt_len(clamps.width),
        )
    )
    drawing.extend(
        _shape_texts(
            leg,
            width / 2,
            section_piece_label(quantity, str(clamps.mark), clamps.diameter_mm),
            cut_length_label(clamps.total_length),
            config,
        )
    )
    return drawing


def _shape_texts(
    right: float, middle: float, first: str, second: str, config: DrawingConfig
) -> Drawing:
    """Return a shape's two text lines on its right, centered on its height"""
    x = right + config.paper(_SHAPE_TEXT_GAP_MM)
    gap = config.paper(_SHAPE_LINE_GAP_MM)
    height = config.paper(config.text_heights_mm.small)
    return Drawing(
        [
            Text((x, middle + gap), first, height, TEXT, HAlign.LEFT, VAlign.BASELINE),
            Text((x, middle - gap), second, height, TEXT, HAlign.LEFT, VAlign.TOP),
        ]
    )


def shape_pieces(beam: DetailingBeam, config: DrawingConfig) -> list[Drawing]:
    """Return one shape per distinct stirrup mark and clamp mark of the beam, in mark order

    A stirrup's quantity adds up the spans with its mark, and a clamp's the sets with its mark.
    """
    stirrups: dict[str, tuple[SpanStirrups, int]] = {}
    for span in beam.stirrups:
        mark = str(span.mark)
        count = stirrups[mark][1] if mark in stirrups else 0
        stirrups[mark] = (span, count + span.quantity)
    clamps: dict[str, tuple[DetailedClamps, int]] = {}
    for item in beam.clamps:
        mark = str(item.mark)
        count = clamps[mark][1] if mark in clamps else 0
        clamps[mark] = (item, count + item.quantity)
    pieces = [
        (mark, _stirrup_shape(span, count, config))
        for mark, (span, count) in stirrups.items()
    ] + [
        (mark, _clamp_shape(item, count, config))
        for mark, (item, count) in clamps.items()
    ]
    return [
        drawing
        for _, drawing in sorted(pieces, key=lambda piece: _mark_number(piece[0]))
    ]


def _mark_number(mark: str) -> int:
    """Return the number of a mark (N12 → 12), or 0 without one"""
    digits = mark.lstrip("N")
    return int(digits) if digits.isdigit() else 0


def shapes_block(
    beam: DetailingBeam,
    left: float,
    top: float,
    width: float,
    config: DrawingConfig,
) -> Drawing:
    """Return the shapes under the title FORMAS, in rows no wider than the sections

    Args:
        left: Left end of the block (cm).
        top: Height of the title's baseline (cm).
        width: Width of the sections' block, where rows break (cm).
    """
    paper = config.paper
    drawing = Drawing(
        [Text((left, top), "FORMAS", paper(config.text_heights_mm.label), TEXT)]
    )
    spacing = paper(_SHAPE_SPACING_MM)
    x, row_top = left, top - paper(_SHAPES_TITLE_GAP_MM)
    row_height = 0.0
    for piece in shape_pieces(beam, config):
        x_min, y_min, x_max, y_max = piece.bounds()
        piece_width, piece_height = x_max - x_min, y_max - y_min
        if x > left and x + piece_width > left + width:
            x, row_top = left, row_top - row_height - spacing
            row_height = 0.0
        drawing.extend(piece.translated(x - x_min, row_top - y_max))
        x += piece_width + spacing
        row_height = max(row_height, piece_height)
    return drawing
