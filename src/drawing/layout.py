"""Layout of the detailing sheets: turns a DetailingBeam or a Pavement into drawing primitives

Model space is in cm, with the elevation on the analysis axis: x along the beam, y up
from the beam's bottom face. Paper lengths (mm) go through ``DrawingConfig.paper``.
"""

import logging

from src.detailing.detailing_beam import DetailingBeam
from src.detailing.quantities import build_quantities
from src.drawing.annotations import (
    bar_hover,
    bar_layer,
    clamp_hover,
    dimension,
)
from src.drawing.bar_rows import bar_rows
from src.drawing.config import DEFAULT_CONFIG, DrawingConfig
from src.drawing.formatting import (
    fmt_date,
    fmt_len,
    fmt_steel,
    spacing_label,
    text_width,
    zone_quantity_label,
)
from src.drawing.geometry import (
    bar_path,
    clamp_rows_y,
    lowest_hook_point,
    pillar_ids,
)
from src.drawing.layers import (
    AXIS,
    BEAM_OUTLINE,
    CLAMP,
    CUT,
    DIMENSION,
    PILLAR,
    STIRRUP,
    TEXT,
)
from src.drawing.primitives import (
    Drawing,
    Line,
    Polyline,
    Text,
)
from src.drawing.schedule_layout import (
    legend_block,
    summary_table,
)
from src.drawing.sections import section_cuts, sections_block
from src.drawing.sheet import (
    FORMATS,
    BlockContent,
    SheetPlacement,
    build_sheet,
    check_materials,
    general_notes,
    sheet_number,
    sheet_title,
)
from src.drawing.sheet_info import SheetInfo, read_sheet_info
from src.errors import SheetFitError

logger = logging.getLogger(__name__)

# Heights above the beam's top face of the dimension rows (mm of paper)
ZONE_ROW_MM = 9.0
CLEAR_SPAN_ROW_MM = 14.0
AXIS_ROW_MM = 19.0
TITLE_MM = 27.0
_EXTENSION_GAP_MM = 1.0
_EXTENSION_TOP_MM = 15.5
AXIS_OVERRUN_MM = 3.0
PILLAR_NAME_DROP_MM = 5.0
_PILLAR_NAME_SHIFT_MM = 1.0
_BREAK_ZIGZAG_MM = 1.0
_BREAK_STOPS = (
    0.35,
    0.45,
    0.55,
    0.65,
)  # zigzag of a break line, as fractions of the width
_TITLE_GAP_MM = 2.0
# Cut marks on the elevation (mm of paper)
_CUT_START_MM = 0.7
_CUT_END_MM = 4.0
_CUT_ARROW_MM = 2.5
_CUT_HEAD_MM = 0.9
_CUT_LETTER_SHIFT_MM = 1.0
_CUT_LETTER_ABOVE_MM = 1.2
_CUT_LETTER_BELOW_MM = 3.5
_LEGEND_BELOW_MM = 20.0  # from the bar rows to the legend
_COLUMN_GAP_MM = 12.0  # between the blocks of the right column


def build_beam_drawing(
    detailing: DetailingBeam,
    config: DrawingConfig = DEFAULT_CONFIG,
    *,
    sheet: SheetInfo | None = None,
) -> Drawing:
    """Return the sheet of one beam: its drawing on a paper with frame, notes and title block

    The paper comes from ``config.sheet_format``.

    Args:
        sheet: Data for the notes and the title block; None reads it from APP_CONFIG.

    Raises:
        SheetFitError: If a fixed format does not hold the drawing.
    """
    info = sheet or read_sheet_info()
    block = _block_content(detailing, info)
    summary = beam_summary(detailing, config)
    sheets: list[tuple[Drawing, SheetPlacement]] = []
    error: SheetFitError | None = None
    for below in (False, True):
        try:
            sheets.append(
                build_sheet(
                    beam_content(detailing, config, below=below), block, config, summary
                )
            )
        except SheetFitError as caught:
            error = error or caught
    if not sheets:
        raise error or SheetFitError("O desenho não cabe na folha.")
    # The smallest paper wins; on a tie the first layout, with the sections on the right
    best = min(
        sheets,
        key=lambda item: (item[1].overflow, FORMATS.index(item[1].format)),
    )
    return best[0]


def beam_content(
    detailing: DetailingBeam,
    config: DrawingConfig = DEFAULT_CONFIG,
    *,
    tables: bool = True,
    below: bool = False,
) -> Drawing:
    """Return the drawing of one beam, off the sheet: elevation, bar rows, sections and legend

    The consumption summary is not part of it: see ``beam_summary``.

    Args:
        tables: Whether to add the legend.
        below: Whether the sections go under the bar rows, beside the legend, instead of to the right of the elevation; narrower and taller.
    """
    drawing = Drawing()
    y_bot = pillar_bottom(detailing, config)
    rows = bar_rows(detailing, y_bot, config)
    axis_bottom = rows.lowest - config.paper(AXIS_OVERRUN_MM)
    drawing.extend(pillars(detailing, config, y_bot, axis_bottom))
    drawing.extend(beam_faces(detailing))
    drawing.extend(bars(detailing))
    drawing.extend(clamps(detailing))
    drawing.extend(cut_marks(detailing, config))
    drawing.extend(dimension_rows(detailing, config))
    drawing.extend(title(detailing, config))
    drawing.extend(rows.drawing)
    block = sections_block(detailing, config)
    if not tables:
        drawing.extend(block.drawing)
        return drawing
    legend = legend_block([*drawing.layers(), *block.drawing.layers()], config)
    legend_top = axis_bottom - config.paper(_LEGEND_BELOW_MM)
    drawing.extend(legend.translated(detailing.start, legend_top))
    gap = config.paper(_COLUMN_GAP_MM)
    if below:
        drawing.extend(
            block.drawing.translated(
                detailing.start + legend.bounds()[2] + gap - block.drawing.bounds()[0],
                legend_top - block.drawing.bounds()[3],
            )
        )
    else:
        drawing.extend(block.drawing)
    return drawing


def beam_summary(
    detailing: DetailingBeam, config: DrawingConfig = DEFAULT_CONFIG
) -> Drawing:
    """Return the consumption summary of one beam: steel by diameter, concrete, formwork and steel ratio

    The sheet puts it on the right, above the title block.
    """
    quantities = build_quantities([detailing])
    return summary_table(
        fmt_steel(detailing.steel.name),
        quantities.steel,
        quantities.concrete_m3,
        quantities.formwork_m2,
        config,
    )


def _block_content(detailing: DetailingBeam, info: SheetInfo) -> BlockContent:
    """Return what the block of notes and title block says for a beam"""
    stirrup_steel = (
        detailing.stirrups[0].steel if detailing.stirrups else detailing.steel
    )
    fck = int(info.concrete.removeprefix("C"))
    for warning in check_materials(
        fck, info.exposure_class, detailing.nominal_covering
    ):
        logger.warning("%s: %s", detailing.beam_id, warning)
    return BlockContent(
        project=info.pavement_name or "",
        title=sheet_title(detailing.beam_id, detailing.width, detailing.height),
        date=fmt_date(info.date),
        sheet=sheet_number(info.sheet_number, info.sheet_total),
        notes=general_notes(
            fck,
            fmt_steel(detailing.steel.name),
            fmt_steel(stirrup_steel.name),
            info.exposure_class,
            detailing.nominal_covering,
        ),
    )


def pillar_bottom(beam: DetailingBeam, config: DrawingConfig) -> float:
    """Return how far down the pillars are drawn, the same for every pillar of the beam (cm)

    At least the minimum stretch, and far enough to show the lowest hook leg with a margin.
    """
    return -max(
        config.pillar_below_min, -lowest_hook_point(beam) + config.pillar_below_margin
    )


def _break_line(left: float, right: float, y: float, config: DrawingConfig) -> Polyline:
    """Return the break line across a pillar, a zigzag in the middle"""
    width = right - left
    zigzag = config.paper(_BREAK_ZIGZAG_MM)
    offsets = (0.0, zigzag, -zigzag, 0.0)
    points = (
        (left, y),
        *(
            (left + stop * width, y + offset)
            for stop, offset in zip(_BREAK_STOPS, offsets, strict=True)
        ),
        (right, y),
    )
    return Polyline(points, (0.0,) * len(points), PILLAR)


def pillars(
    beam: DetailingBeam, config: DrawingConfig, y_bot: float, axis_bottom: float
) -> Drawing:
    """Return the pillars on the elevation: faces, break lines, axes and names

    Args:
        y_bot: Height where the pillars end below the beam (cm).
        axis_bottom: Height where the pillar axes end, under the bar rows (cm).
    """
    drawing = Drawing()
    y_top = beam.height + config.pillar_above
    axis_top = beam.height + config.paper(AXIS_ROW_MM + AXIS_OVERRUN_MM)
    name_height = config.paper(config.text_heights_mm.pillar)
    for support, name in zip(beam.supports, pillar_ids(beam), strict=True):
        drawing.add(
            Line((support.left, y_bot), (support.left, y_top), PILLAR),
            Line((support.right, y_bot), (support.right, y_top), PILLAR),
            _break_line(support.left, support.right, y_top, config),
            _break_line(support.left, support.right, y_bot, config),
            Line((support.center, axis_bottom), (support.center, axis_top), AXIS),
            Text(
                (
                    support.center + config.paper(_PILLAR_NAME_SHIFT_MM),
                    y_bot - config.paper(PILLAR_NAME_DROP_MM),
                ),
                name,
                name_height,
                TEXT,
            ),
        )
    return drawing


def beam_faces(beam: DetailingBeam) -> Drawing:
    """Return the beam's bottom and top faces along each clear span"""
    drawing = Drawing()
    for left, right in zip(beam.supports[:-1], beam.supports[1:], strict=True):
        for y in (0.0, beam.height):
            drawing.add(Line((left.right, y), (right.left, y), BEAM_OUTLINE))
    return drawing


def bars(beam: DetailingBeam) -> Drawing:
    """Return every bar run on the elevation, hooks included; overlapping runs share their height"""
    drawing = Drawing()
    for bar in beam.bars_on_face(False) + beam.bars_on_face(True):
        points, bulges = bar_path(bar)
        drawing.add(Polyline(points, bulges, bar_layer(bar), meta=bar_hover(beam, bar)))
    return drawing


def clamps(beam: DetailingBeam) -> Drawing:
    """Return one line per clamp row on the elevation, from the bend along the legs"""
    drawing = Drawing()
    for item in beam.clamps:
        tip = item.position + (item.leg_length if item.left else -item.leg_length)
        meta = clamp_hover(item)
        for y in clamp_rows_y(beam, item):
            drawing.add(Line((item.position, y), (tip, y), CLAMP, meta))
    return drawing


def cut_marks(beam: DetailingBeam, config: DrawingConfig) -> Drawing:
    """Return the cut marks on the elevation: a tick with an arrow and the letter, above and below"""
    drawing = Drawing()
    height = config.paper(config.text_heights_mm.pillar)
    arrow = config.paper(_CUT_ARROW_MM)
    head = config.paper(_CUT_HEAD_MM)
    for letter, x in section_cuts(beam, config):
        for side in (1.0, -1.0):
            base = beam.height if side > 0 else 0.0
            near = base + side * config.paper(_CUT_START_MM)
            far = base + side * config.paper(_CUT_END_MM)
            tip = x - arrow
            drawing.add(
                Line((x, near), (x, far), CUT),
                Line((x, far), (tip, far), CUT),
                Line((tip, far), (tip + head, far + head / 2), CUT),
                Line((tip, far), (tip + head, far - head / 2), CUT),
            )
        drawing.add(
            Text(
                (
                    x + config.paper(_CUT_LETTER_SHIFT_MM),
                    beam.height + config.paper(_CUT_LETTER_ABOVE_MM),
                ),
                letter,
                height,
                CUT,
            ),
            Text(
                (
                    x + config.paper(_CUT_LETTER_SHIFT_MM),
                    -config.paper(_CUT_LETTER_BELOW_MM),
                ),
                letter,
                height,
                CUT,
            ),
        )
    return drawing


def dimension_rows(beam: DetailingBeam, config: DrawingConfig) -> Drawing:
    """Return the three dimension rows over the beam: stirrup zones, clear spans and axes

    Also the extension lines from the pillars' inner faces up to the clear-span row.
    """
    drawing = stirrup_zone_row(beam, config)
    drawing.extend(geometry_dimension_rows(beam, config))
    return drawing


def stirrup_zone_row(beam: DetailingBeam, config: DrawingConfig) -> Drawing:
    """Return the dimension row of the stirrup zones, with their spacing and quantity"""
    drawing = Drawing()
    zone_y = beam.height + config.paper(ZONE_ROW_MM)
    for stirrups in beam.stirrups:
        for zone, quantity in zip(
            stirrups.zones, stirrups.zone_quantities, strict=True
        ):
            drawing.extend(
                dimension(
                    zone.start,
                    zone.end,
                    zone_y,
                    STIRRUP,
                    config,
                    spacing_label(str(stirrups.mark), zone.spacing),
                    zone_quantity_label(quantity, stirrups.diameter_mm),
                )
            )
    return drawing


def geometry_dimension_rows(beam: DetailingBeam, config: DrawingConfig) -> Drawing:
    """Return the clear-span and axis dimension rows over the beam

    Also the extension lines from the pillars' inner faces up to the clear-span row.
    """
    drawing = Drawing()
    span_y = beam.height + config.paper(CLEAR_SPAN_ROW_MM)
    extension_bottom = (
        beam.height + config.pillar_above + config.paper(_EXTENSION_GAP_MM)
    )
    extension_top = beam.height + config.paper(_EXTENSION_TOP_MM)
    for span in beam.clear_spans:
        drawing.extend(
            dimension(
                span.start, span.end, span_y, DIMENSION, config, fmt_len(span.length)
            )
        )
        for x in (span.start, span.end):
            drawing.add(Line((x, extension_bottom), (x, extension_top), DIMENSION))
    axis_y = beam.height + config.paper(AXIS_ROW_MM)
    for left, right in zip(beam.supports[:-1], beam.supports[1:], strict=True):
        drawing.extend(
            dimension(
                left.center,
                right.center,
                axis_y,
                DIMENSION,
                config,
                fmt_len(right.center - left.center),
            )
        )
    return drawing


def title(beam: DetailingBeam, config: DrawingConfig) -> Drawing:
    """Return the beam's name over the dimensions, with b/h on its right"""
    heights = config.text_heights_mm
    name_height = config.paper(heights.beam_name)
    y = beam.height + config.paper(TITLE_MM)
    section_x = (
        beam.start + text_width(beam.beam_id, name_height) + config.paper(_TITLE_GAP_MM)
    )
    return Drawing(
        [
            Text((beam.start, y), beam.beam_id, name_height, TEXT),
            Text(
                (section_x, y),
                f"{fmt_len(beam.width)}/{fmt_len(beam.height)}",
                config.paper(heights.beam_section),
                TEXT,
            ),
        ]
    )
