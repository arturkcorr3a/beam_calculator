"""Bar rows under the elevation: every bar run and clamp set redrawn on its own row (spec §6.5, §6.6)

The rows keep the elevation's x, so each run sits under its place on the beam. Runs that
overlap on the elevation, such as the two bars of a lap, land on different rows, and the
lap is dimensioned between them.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from src.detailing.detailed_bar import BarRole, DetailedBar
from src.detailing.detailed_clamps import DetailedClamps
from src.detailing.detailing_beam import DetailingBeam
from src.drawing.annotations import (
    DIMENSION_TEXT_GAP_MM,
    bar_hover,
    bar_layer,
    clamp_hover,
    dimension,
)
from src.drawing.config import DrawingConfig
from src.drawing.formatting import (
    CLAMP_MARK,
    bar_paper_mark,
    fmt_len,
    piece_label,
    text_width,
)
from src.drawing.geometry import HookPath, bar_path, hook_path, overlap_pairs
from src.drawing.layers import AXIS, CLAMP, DIMENSION, LAP, TEXT
from src.drawing.primitives import (
    Circle,
    Drawing,
    HAlign,
    Line,
    Polyline,
    Text,
    VAlign,
    arc_points,
)

Box = tuple[float, float, float, float]  # x min, y min, x max, y max (cm)

_LABEL_DROP_MM = 3.7  # from the row to the label's baseline
_PAPER_MARK_DROP_MM = 3.1  # from the label's baseline to the paper mark's
_HOOK_TEXT_GAP_MM = 1.5  # from a hook leg to its texts and to a label pushed aside
_CLAMP_TEXT_GAP_MM = 2.0  # from a clamp's tips to its label
_CLAMP_LINE_GAP_MM = 0.5  # half the gap between a clamp's label and its paper mark
# First row of the top face, under the pillar names (mm of paper below y_bot)
_TOP_BLOCK_DROP_MM = 5.0 + 3.0 + 14.0
_SEPARATOR_GAP_MM = (
    11.0  # between the last top row, the separator and the first bottom row
)
_SEPARATOR_CLEARANCE_MM = 5.0  # between the separator and any item
_SEPARATOR_OVERRUN_MM = 5.0
_FACE_LEGEND_SHIFT_MM = 12.0
_CLAMP_GROUP = 1_000  # clamps come after every bar group
_LAP_SEARCH_STEP_MM = 1.0  # between the heights tried for a lap dimension
_LAP_CLEARANCE_MM = 0.5  # kept between a lap dimension and the row items
_LAP_TEXT_SIDE_GAP_MM = 2.0  # from the lap's end to a text set beside it


@dataclass(frozen=True)
class RowItem:
    """A bar run or a clamp set to place on a row

    Attributes:
        group: Packing group; lower groups get the upper rows.
        start: Left end of the item on the beam (cm), the order within a group.
        end: Right end of the item on the beam (cm).
    """

    group: int
    start: float
    end: float
    bar: DetailedBar | None = None
    clamps: DetailedClamps | None = None


@dataclass(frozen=True)
class PlacedItem:
    """A row item drawn on its row

    Attributes:
        row: Index of the row in its face, 0 being the top one.
        y: Height of the row (cm).
        boxes: Boxes of the drawn primitives, used to keep items apart (cm).
    """

    item: RowItem
    row: int
    y: float
    drawing: Drawing
    boxes: tuple[Box, ...]


@dataclass(frozen=True)
class BarRows:
    """The bar rows of a beam

    Attributes:
        top, bottom: The placed items of each face, in placing order.
        separator_y: Height of the line between the faces (cm).
        lowest: Lowest height reached by the rows (cm).
    """

    drawing: Drawing
    top: tuple[PlacedItem, ...]
    bottom: tuple[PlacedItem, ...]
    separator_y: float
    lowest: float


def row_items(beam: DetailingBeam, is_bottom: bool) -> list[RowItem]:
    """Return the items of a face in placing order

    Groups: main bars of layer 0, construction bars, main bars of layer 1, 2, …, and clamps last; left to right within each group.
    """
    items: list[RowItem] = []
    for bar in beam.bars_on_face(is_bottom):
        if bar.role is BarRole.CONSTRUCTION:
            group = 1
        elif bar.layer_index == 0:
            group = 0
        else:
            group = 1 + bar.layer_index
        items.append(RowItem(group, bar.start, bar.end, bar=bar))
    for clamps in beam.clamps:
        if clamps.is_bottom == is_bottom:
            tip = _clamp_tip(clamps)
            items.append(
                RowItem(
                    _CLAMP_GROUP,
                    min(clamps.position, tip),
                    max(clamps.position, tip),
                    clamps=clamps,
                )
            )
    return sorted(items, key=lambda item: (item.group, item.start, item.end))


def _clamp_tip(clamps: DetailedClamps) -> float:
    """Return the x of a clamp's leg tips (cm)"""
    return clamps.position + (clamps.leg_length if clamps.left else -clamps.leg_length)


def draw_item(
    beam: DetailingBeam, item: RowItem, y: float, config: DrawingConfig
) -> Drawing:
    """Return an item drawn on a row at height y (cm)"""
    if item.bar is not None:
        return draw_bar(beam, item.bar, y, config)
    assert item.clamps is not None  # a row item holds a bar or clamps
    return draw_clamps(item.clamps, y, config)


def _moved(path: HookPath | None, dy: float) -> HookPath | None:
    """Return a hook path moved up by dy (cm)"""
    if path is None:
        return None
    start, end, tip = path
    return (
        (start[0], start[1] + dy),
        (end[0], end[1] + dy),
        (tip[0], tip[1] + dy),
    )


def draw_bar(
    beam: DetailingBeam, bar: DetailedBar, y: float, config: DrawingConfig
) -> Drawing:
    """Return a bar run drawn on a row: the bar, its straight length, hook tips, label and paper mark

    The hooks keep their elevation direction: bottom bars bend up and top bars down.
    """
    heights = config.text_heights_mm
    small = config.paper(heights.small)
    label_height = config.paper(heights.label)
    gap = config.paper(_HOOK_TEXT_GAP_MM)
    dy = y - bar.y
    points, bulges = bar_path(bar)
    drawing = Drawing(
        [
            Polyline(
                tuple((px, py + dy) for px, py in points),
                bulges,
                bar_layer(bar),
                meta=bar_hover(beam, bar),
            )
        ]
    )
    middle = (bar.start + bar.end) / 2
    drawing.add(
        Text(
            (middle, y + config.paper(DIMENSION_TEXT_GAP_MM)),
            fmt_len(bar.straight_length),
            small,
            DIMENSION,
            HAlign.CENTER,
        )
    )
    legs: list[tuple[float, float]] = []  # x and lowest y of each leg
    for left in (True, False):
        path = _moved(hook_path(bar, left), dy)
        hook = bar.left_hook if left else bar.right_hook
        if path is None or hook is None:
            continue
        _, curve_end, tip = path
        leg_x = tip[0]
        legs.append((leg_x, min(tip[1], curve_end[1])))
        drawing.add(
            Text(
                (leg_x - gap if left else leg_x + gap, (curve_end[1] + tip[1]) / 2),
                fmt_len(round(hook.tip_length)),
                small,
                DIMENSION,
                HAlign.CENTER,
                VAlign.BASELINE if left else VAlign.TOP,
                90.0,
            )
        )
    label = piece_label(bar.quantity, str(bar.mark), bar.diameter_mm, bar.total_length)
    baseline = y - config.paper(_LABEL_DROP_MM)
    x = _label_x(
        middle, text_width(label, label_height), baseline + label_height, legs, gap
    )
    drawing.add(Text((x, baseline), label, label_height, TEXT, HAlign.CENTER))
    mark = bar_paper_mark(bar.role is BarRole.CONSTRUCTION, bar.layer_index)
    if mark is not None:
        drawing.add(
            Text(
                (x, baseline - config.paper(_PAPER_MARK_DROP_MM)),
                mark,
                small,
                TEXT,
                HAlign.CENTER,
            )
        )
    return drawing


def _label_x(
    middle: float,
    width: float,
    top: float,
    legs: Sequence[tuple[float, float]],
    gap: float,
) -> float:
    """Return the center of a label, pushed aside from the hook legs it would cross

    Only legs that go down past the label's top can cross it. A label crossing the left leg moves to its right, one crossing the right leg moves to its left, and one crossing both goes past the right leg.

    Args:
        middle: Center of the straight segment (cm).
        width: Estimated label width (cm).
        top: Height of the label's top (cm).
        legs: The x and the lowest y of each hook leg, left to right (cm).
        gap: Distance kept between a leg and the label (cm).
    """

    def crosses(x: float, leg: tuple[float, float]) -> bool:
        return leg[1] < top and x - width / 2 - gap < leg[0] < x + width / 2 + gap

    crossed = [leg for leg in legs if crosses(middle, leg)]
    if not crossed:
        return middle
    if len(crossed) == 2:
        return max(leg[0] for leg in crossed) + gap + width / 2
    leg_x = crossed[0][0]
    if leg_x <= middle:  # the left leg: move right of it
        return leg_x + gap + width / 2
    return leg_x - gap - width / 2


def draw_clamps(clamps: DetailedClamps, y: float, config: DrawingConfig) -> Drawing:
    """Return a clamp set drawn on a row: a U lying down, its leg and width, label and paper mark

    The bend sits at the clamp's position, one leg on the row and the other one width below.
    """
    heights = config.text_heights_mm
    small = config.paper(heights.small)
    label_height = config.paper(heights.label)
    tip = _clamp_tip(clamps)
    lower = y - clamps.width
    middle = (y + lower) / 2
    outward = -1.0 if clamps.left else 1.0  # from the bend, away from the legs
    drawing = Drawing(
        [
            Polyline(
                (
                    (tip, y),
                    (clamps.position, y),
                    (clamps.position, lower),
                    (tip, lower),
                ),
                (0.0,) * 4,
                CLAMP,
                meta=clamp_hover(clamps),
            ),
            Text(
                ((clamps.position + tip) / 2, y + config.paper(DIMENSION_TEXT_GAP_MM)),
                fmt_len(clamps.leg_length),
                small,
                DIMENSION,
                HAlign.CENTER,
            ),
            Text(
                (clamps.position + outward * config.paper(_HOOK_TEXT_GAP_MM), middle),
                fmt_len(clamps.width),
                small,
                DIMENSION,
                HAlign.CENTER,
                VAlign.BASELINE if clamps.left else VAlign.TOP,
                90.0,
            ),
        ]
    )
    label_x = tip - outward * config.paper(_CLAMP_TEXT_GAP_MM)
    align = HAlign.LEFT if clamps.left else HAlign.RIGHT
    line_gap = config.paper(_CLAMP_LINE_GAP_MM)
    drawing.add(
        Text(
            (label_x, middle + line_gap),
            piece_label(
                clamps.quantity,
                str(clamps.mark),
                clamps.diameter_mm,
                clamps.total_length,
            ),
            label_height,
            TEXT,
            align,
        ),
        Text((label_x, middle - line_gap), CLAMP_MARK, small, TEXT, align, VAlign.TOP),
    )
    return drawing


def item_boxes(drawing: Drawing, config: DrawingConfig) -> tuple[Box, ...]:
    """Return one box per segment, arc, circle and text of a drawing (cm)

    Finer than one box for the whole item, so a long hook leg only blocks the strip it runs down.
    """
    boxes: list[Box] = []
    for item in drawing.items:
        match item:
            case Line():
                boxes.append(_box((item.start, item.end)))
            case Polyline():
                for start, end, bulge in item.segments():
                    boxes.append(
                        _box(arc_points(start, end, bulge, config.arc_segments))
                    )
            case Circle():
                x, y = item.center
                boxes.append(
                    (x - item.radius, y - item.radius, x + item.radius, y + item.radius)
                )
            case Text():
                boxes.append(_box(item.corners()))
    return tuple(boxes)


def _box(points: Iterable[tuple[float, float]]) -> Box:
    """Return the bounding box of some points"""
    xs, ys = zip(*points, strict=True)
    return min(xs), min(ys), max(xs), max(ys)


def _expanded(box: Box, margin: float) -> Box:
    """Return a box grown by a margin on every side"""
    return box[0] - margin, box[1] - margin, box[2] + margin, box[3] + margin


def boxes_overlap(a: Box, b: Box) -> bool:
    """Return whether two boxes share some area; touching edges do not count"""
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def pack_face(
    beam: DetailingBeam, is_bottom: bool, top_y: float, config: DrawingConfig
) -> list[PlacedItem]:
    """Place the items of one face on rows, first free row first

    Each group opens a new row under the face's last row. An item goes on the first row of its group where its boxes, grown by the row clearance, cross no box already placed on the face, from any group; if none is free, the group opens rows until one is.

    Args:
        top_y: Height of the face's first row (cm).
    """
    pitch = config.paper(config.row_pitch_mm)
    clearance = config.paper(config.row_clearance_mm)
    placed: list[PlacedItem] = []
    opened = 0
    group: int | None = None
    first_row = 0
    for item in row_items(beam, is_bottom):
        if item.group != group:
            group, first_row = item.group, opened
        row = first_row
        while True:
            opened = max(opened, row + 1)
            y = top_y - row * pitch
            drawing = draw_item(beam, item, y, config)
            boxes = item_boxes(drawing, config)
            grown = [_expanded(box, clearance) for box in boxes]
            if not any(
                boxes_overlap(new, old)
                for new in grown
                for other in placed
                for old in other.boxes
            ):
                placed.append(PlacedItem(item, row, y, drawing, boxes))
                break
            row += 1
    return placed


def _lowest(placed: Sequence[PlacedItem], default: float) -> float:
    """Return the lowest height of some placed items, or a default when there are none"""
    return min((box[1] for item in placed for box in item.boxes), default=default)


def _highest(placed: Sequence[PlacedItem], default: float) -> float:
    """Return the highest height of some placed items, or a default when there are none"""
    return max((box[3] for item in placed for box in item.boxes), default=default)


def bar_rows(beam: DetailingBeam, y_bot: float, config: DrawingConfig) -> BarRows:
    """Return the bar rows of a beam: the top face, a separator, then the bottom face

    Args:
        y_bot: Height where the pillars end below the beam (cm).
    """
    paper = config.paper
    top_y = y_bot - paper(_TOP_BLOCK_DROP_MM)
    top = pack_face(beam, False, top_y, config)
    last_top_row = min((item.y for item in top), default=top_y)
    separator_y = min(
        last_top_row - paper(_SEPARATOR_GAP_MM),
        _lowest(top, top_y) - paper(_SEPARATOR_CLEARANCE_MM),
    )
    bottom_y = separator_y - paper(_SEPARATOR_GAP_MM)
    bottom = pack_face(beam, True, bottom_y, config)
    excess = _highest(bottom, bottom_y) - (separator_y - paper(_SEPARATOR_CLEARANCE_MM))
    if excess > 0:  # a hook leg of the first bottom row reaches the separator
        bottom = pack_face(beam, True, bottom_y - excess, config)
    drawing = Drawing()
    for item in (*top, *bottom):
        drawing.extend(item.drawing)
    overrun = paper(_SEPARATOR_OVERRUN_MM)
    drawing.add(
        Line(
            (beam.start - overrun, separator_y), (beam.end + overrun, separator_y), AXIS
        )
    )
    for placed, name in ((top, "SUPERIOR"), (bottom, "INFERIOR")):
        if placed:
            drawing.add(_face_legend(beam, placed, name, config))
    for is_bottom, placed in ((False, top), (True, bottom)):
        drawing.extend(lap_marks(beam, is_bottom, placed, config))
    lowest = min(_lowest(bottom, bottom_y), bottom_y, drawing.bounds()[1])
    return BarRows(drawing, tuple(top), tuple(bottom), separator_y, lowest)


def _face_legend(
    beam: DetailingBeam,
    placed: Sequence[PlacedItem],
    name: str,
    config: DrawingConfig,
) -> Text:
    """Return the name of a face, turned 90°, left of its rows and centered on them"""
    rows = [item.y for item in placed]
    return Text(
        (
            beam.start - config.paper(_FACE_LEGEND_SHIFT_MM),
            (max(rows) + min(rows)) / 2,
        ),
        name,
        config.paper(config.text_heights_mm.label),
        TEXT,
        HAlign.CENTER,
        VAlign.MIDDLE,
        90.0,
    )


def lap_marks(
    beam: DetailingBeam,
    is_bottom: bool,
    placed: Sequence[PlacedItem],
    config: DrawingConfig,
) -> Drawing:
    """Return the lap dimensions between the rows of a face (spec §6.6)

    For each end-to-end overlap of two placed runs: a dashed line at each end of the lap, between the two rows, and a dimension with the lap length. The dimension starts halfway between the rows with its text over the line; if that text would cross a label or another lap's dimension, it tries other heights between the rows and the text beside the lap, keeping the first free spot.
    """
    rows = {id(item.item.bar): item.y for item in placed if item.item.bar is not None}
    obstacles = [box for item in placed for box in item.boxes]
    drawing = Drawing()
    for left, right, start, end in overlap_pairs(beam, is_bottom):
        if id(left) not in rows or id(right) not in rows:
            continue
        upper, lower = sorted((rows[id(left)], rows[id(right)]), reverse=True)
        drawing.add(
            Line((start, upper), (start, lower), LAP),
            Line((end, upper), (end, lower), LAP),
        )
        mark = _free_lap_dimension(start, end, upper, lower, obstacles, config)
        obstacles += item_boxes(mark, config)
        drawing.extend(mark)
    return drawing


def _free_lap_dimension(
    start: float,
    end: float,
    upper: float,
    lower: float,
    obstacles: Sequence[Box],
    config: DrawingConfig,
) -> Drawing:
    """Return the first lap dimension, over the candidate spots, that crosses no obstacle

    Falls back to the first candidate: halfway between the rows, text centered over the line.

    Args:
        upper, lower: Heights of the two runs' rows (cm).
    """
    text = fmt_len(end - start)
    step = config.paper(_LAP_SEARCH_STEP_MM)
    clearance = config.paper(_LAP_CLEARANCE_MM)
    middle = (upper + lower) / 2
    heights = [middle]
    offset = step
    while middle + offset < upper - step:
        heights += [middle - offset, middle + offset]
        offset += step
    candidates = [
        _lap_dimension(start, end, y, text, side, config)
        for y in heights
        for side in (HAlign.CENTER, HAlign.LEFT, HAlign.RIGHT)
    ]
    for candidate in candidates:
        grown = [_expanded(box, clearance) for box in item_boxes(candidate, config)]
        if not any(boxes_overlap(new, old) for new in grown for old in obstacles):
            return candidate
    return candidates[0]


def _lap_dimension(
    start: float, end: float, y: float, text: str, side: HAlign, config: DrawingConfig
) -> Drawing:
    """Return a lap dimension at height y, its text over the line or beside the lap

    Args:
        side: CENTER puts the text over the line; LEFT puts it after the lap's end, RIGHT before its start.
    """
    if side is HAlign.CENTER:
        return dimension(start, end, y, DIMENSION, config, text)
    drawing = dimension(start, end, y, DIMENSION, config)
    gap = config.paper(_LAP_TEXT_SIDE_GAP_MM)
    x = end + gap if side is HAlign.LEFT else start - gap
    drawing.add(
        Text(
            (x, y),
            text,
            config.paper(config.text_heights_mm.small),
            DIMENSION,
            side,
            VAlign.MIDDLE,
        )
    )
    return drawing
