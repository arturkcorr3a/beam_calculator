"""Geometry of a detailed beam, read from the DetailingBeam for the drawings

The functions down to ``row_offsets`` port the detailing recipes without changing
their behavior; those recipes were checked against the calculation. The rest builds
on them.
"""

from math import pi, tan

from src.detailing.detailed_bar import DetailedBar
from src.detailing.detailed_clamps import DetailedClamps
from src.detailing.detailing_beam import DetailingBeam
from src.detailing.span_stirrups import SpanStirrups
from src.drawing.config import MM_PER_CM, DrawingConfig
from src.drawing.formatting import PHI, fmt_diam, fmt_len
from src.drawing.primitives import Point
from src.reinforcement.reinforcement import Reinforcement
from src.reinforcement.stirrups import HOOK_TIP_RATIO, MIN_HOOK_TIP

QUARTER_BULGE = tan(pi / 8)  # bulge of a quarter circle

HookPath = tuple[Point, Point, Point]


def pillar_ids(beam: DetailingBeam) -> list[str]:
    """Return the id of each support, left to right"""
    return [span.start_pillar_id for span in beam.stirrups] + [
        beam.stirrups[-1].end_pillar_id
    ]


def hook_path(bar: DetailedBar, left: bool) -> HookPath | None:
    """Return the curve start, the curve end and the tip of a hook's axis (cm), or None

    The curve is a quarter circle of radius (D + φ) / 2. Bottom bars bend up and top bars bend down, and the bar's end is the outer face of the leg.

    Args:
        left: Whether to read the left hook; otherwise the right.
    """
    hook = bar.left_hook if left else bar.right_hook
    if hook is None:
        return None
    diameter = bar.diameter_mm / MM_PER_CM  # cm
    radius = (hook.pin_diameter + diameter) / 2  # cm
    inward = 1.0 if left else -1.0
    upward = 1.0 if bar.is_bottom else -1.0
    leg_x = (bar.start if left else bar.end) + inward * diameter / 2  # cm
    return (
        (leg_x + inward * radius, bar.y),
        (leg_x, bar.y + upward * radius),
        (leg_x, bar.y + upward * (radius + hook.tip_length)),
    )


def stirrup_positions(stirrups: SpanStirrups) -> list[float]:
    """Return the position of every stirrup of a span, left to right (cm)

    Each zone is divided evenly; the stirrup closing the span counts in the last zone.
    """
    positions: list[float] = []
    last = len(stirrups.zones) - 1
    for index, (zone, quantity) in enumerate(
        zip(stirrups.zones, stirrups.zone_quantities, strict=True)
    ):
        gaps = quantity - 1 if index == last else quantity
        step = (zone.end - zone.start) / gaps  # cm
        positions += [zone.start + gap * step for gap in range(gaps)]
    positions.append(stirrups.end)
    return positions


def zone_labels(stirrups: SpanStirrups) -> list[str]:
    """Return one label per zone, such as 25 N9 φ6,3 c/20"""
    return [
        f"{quantity} {stirrups.mark} {PHI}{fmt_diam(stirrups.diameter_mm)} "
        f"c/{fmt_len(zone.spacing)}"
        for zone, quantity in zip(stirrups.zones, stirrups.zone_quantities, strict=True)
    ]


def stirrup_bend(stirrups: SpanStirrups) -> tuple[float, float]:
    """Return the bend diameter and the 135° hook tip of a stirrup (cm)

    References:
        ABNT NBR 6118:2026 — Section 9.4.6.1
    """
    diameter = stirrups.diameter_mm / MM_PER_CM  # cm
    bend_diameter = stirrups.steel.stirrup_bend_diameter(stirrups.diameter_mm)  # cm
    return bend_diameter, max(HOOK_TIP_RATIO * diameter, MIN_HOOK_TIP)


def clamp_rows_y(beam: DetailingBeam, clamps: DetailedClamps) -> list[float]:
    """Return the height of each clamp row's axis, from the bottom face (cm)

    The rows are stacked past the last layer of the anchored bars, with the minimum vertical spacing, as the calculation does.

    Raises:
        ValueError: If no bar on the clamps' face comes from their interest point.

    References:
        ABNT NBR 6118:2026 — Section 18.3.2.2
    """
    diameter = clamps.diameter_mm / MM_PER_CM  # cm
    bars = [
        bar
        for bar in beam.bars
        if clamps.source_position in bar.source_positions
        and bar.is_bottom == clamps.is_bottom
    ]
    if not bars:
        raise ValueError(
            f"Beam '{beam.beam_id}': no bar anchored by the clamps {clamps.mark} "
            f"at {clamps.source_position} cm."
        )
    last_layer = max(bar.layer_index for bar in bars)
    last_row = [bar for bar in bars if bar.layer_index == last_layer]
    largest = max(last_row, key=lambda bar: bar.diameter_mm)
    largest_diameter = largest.diameter_mm / MM_PER_CM  # cm
    first_gap = Reinforcement.get_vertical_spacing(max(largest_diameter, diameter))
    row_gap = Reinforcement.get_vertical_spacing(diameter)
    upward = 1.0 if clamps.is_bottom else -1.0
    first = largest.y + upward * (largest_diameter / 2 + first_gap + diameter / 2)
    return [
        first + upward * row * (row_gap + diameter) for row in range(clamps.quantity)
    ]


def section_layers(
    beam: DetailingBeam, x: float, is_bottom: bool
) -> dict[int, list[DetailedBar]]:
    """Return the bar runs crossing a section, by layer

    Args:
        x: Position of the section along the beam (cm).
    """
    layers: dict[int, list[DetailedBar]] = {}
    for bar in beam.bars_at(x, is_bottom):
        layers.setdefault(bar.layer_index, []).append(bar)
    return layers


def arrange_row(runs: list[DetailedBar]) -> list[DetailedBar]:
    """Return one item per bar of a layer: symmetric, largest bars on the outside

    Reproduces the order of ``Reinforcement.arrange_bars_in_layer``, left to right.
    """
    by_diameter: dict[float, list[DetailedBar]] = {}
    for run in runs:
        by_diameter.setdefault(run.diameter_mm, []).extend([run] * run.quantity)
    left: list[DetailedBar] = []
    right: list[DetailedBar] = []
    leftovers: list[DetailedBar] = []
    for diameter in sorted(by_diameter, reverse=True):
        bars = by_diameter[diameter]
        pairs = len(bars) // 2
        left += bars[:pairs]
        right += bars[pairs : 2 * pairs]
        if len(bars) % 2 == 1:
            leftovers.append(bars[-1])
    return left + leftovers[0::2] + leftovers[1::2][::-1] + right[::-1]


def row_offsets(row: list[DetailedBar], inner_width: float) -> list[float]:
    """Return each bar's offset from the section's center (cm)

    The bars at the ends touch the stirrup and the gaps are equal: a drawing choice, since the model only keeps the order. A negative gap means the bars do not fit.

    Args:
        row: The bars in order, from ``arrange_row``.
        inner_width: Width between the stirrup's inner faces (cm).
    """
    diameters = [bar.diameter_mm / MM_PER_CM for bar in row]  # cm
    if len(row) == 1:
        return [0.0]
    gap = (inner_width - sum(diameters)) / (len(row) - 1)  # cm
    offsets: list[float] = []
    edge = -inner_width / 2  # cm
    for diameter in diameters:
        offsets.append(edge + diameter / 2)
        edge += diameter + gap
    return offsets


def _quarter_bulge(start: Point, end: Point, center: Point) -> float:
    """Return the bulge of the quarter circle from start to end around center"""
    cross = (start[0] - center[0]) * (end[1] - center[1]) - (start[1] - center[1]) * (
        end[0] - center[0]
    )
    return QUARTER_BULGE if cross > 0 else -QUARTER_BULGE


def bar_path(bar: DetailedBar) -> tuple[tuple[Point, ...], tuple[float, ...]]:
    """Return the axis polyline of a bar run and its bulges (cm)

    From the left tip to the right tip. Without a hook, the end point is the bar's start or end. With one, the path runs through the tip, the curve end and the curve start of ``hook_path``, with a quarter-circle bulge on the vertex where the curve begins.
    """
    points: list[Point] = []
    bulges: list[float] = []
    left = hook_path(bar, left=True)
    if left is None:
        points.append((bar.start, bar.y))
        bulges.append(0.0)
    else:
        curve_start, curve_end, tip = left
        center = (curve_start[0], curve_end[1])
        points += [tip, curve_end, curve_start]
        bulges += [0.0, _quarter_bulge(curve_end, curve_start, center), 0.0]
    right = hook_path(bar, left=False)
    if right is None:
        points.append((bar.end, bar.y))
        bulges.append(0.0)
    else:
        curve_start, curve_end, tip = right
        center = (curve_start[0], curve_end[1])
        points += [curve_start, curve_end, tip]
        bulges += [_quarter_bulge(curve_start, curve_end, center), 0.0, 0.0]
    return tuple(points), tuple(bulges)


def overlap_pairs(
    beam: DetailingBeam, is_bottom: bool
) -> list[tuple[DetailedBar, DetailedBar, float, float]]:
    """Return the left run, the right run, the start and the end of each end-to-end overlap

    Two runs of one layer overlap end to end when the right one starts inside the left one and ends past it. ``lap_splices`` is not read: it leaves out the construction bars' laps.
    """
    bars = beam.bars_on_face(is_bottom)
    return [
        (left, right, right.start, left.end)
        for index, left in enumerate(bars)
        for right in bars[index + 1 :]
        if left.layer_index == right.layer_index
        and left.start < right.start <= left.end < right.end
    ]


def lowest_hook_point(beam: DetailingBeam) -> float:
    """Return the lowest height reached by a hook leg's outer face, or 0 if none passes the bottom face (cm)

    Only the top bars' legs go down; a frame-node leg may pass the beam's bottom face, into the pillar.
    """
    lowest = 0.0
    for bar in beam.bars:
        if bar.is_bottom:
            continue
        radius = bar.diameter_mm / MM_PER_CM / 2  # cm
        for left in (True, False):
            path = hook_path(bar, left)
            if path is not None:
                lowest = min(lowest, path[2][1] - radius)
    return lowest


def overlap_stretches(beam: DetailingBeam) -> list[tuple[float, float]]:
    """Return the overlap stretches of both faces, as start and end (cm)"""
    return [
        (start, end)
        for is_bottom in (False, True)
        for _, _, start, end in overlap_pairs(beam, is_bottom)
    ]


def section_positions(beam: DetailingBeam, config: DrawingConfig) -> list[float]:
    """Return one cut position per span, left to right (cm)

    Starts at the clear span's center. If it falls inside an overlap stretch of either face (closed interval from ``overlap_pairs``), tries x0 + d and x0 − d for d = step, 2·step, … within the span less the edge margin at each end, and keeps the first free one. If none is free, keeps x0.
    """
    stretches = overlap_stretches(beam)

    def is_free(x: float) -> bool:
        return not any(start <= x <= end for start, end in stretches)

    positions: list[float] = []
    for span in beam.clear_spans:
        center = (span.start + span.end) / 2  # cm
        low = span.start + config.section_edge_margin  # cm
        high = span.end - config.section_edge_margin  # cm
        chosen = center
        if not is_free(center):
            step = 1
            while True:
                distance = step * config.section_search_step  # cm
                candidates = [
                    x
                    for x in (center + distance, center - distance)
                    if low <= x <= high
                ]
                if not candidates:
                    break
                free = [x for x in candidates if is_free(x)]
                if free:
                    chosen = free[0]
                    break
                step += 1
        positions.append(chosen)
    return positions
