"""Paper sheet of a beam: standard format, frame, and the block of notes and title block

The sheet's lower left corner is the
origin of model space; paper lengths (mm) go through ``DrawingConfig.paper``. The block
is built in paper mm with y growing downward, as the spec draws it, and converted to
model space (y up) by ``_pt``.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from src.drawing.bar_rows import Box, item_boxes
from src.drawing.config import DEFAULT_CONFIG, DrawingConfig
from src.drawing.formatting import fmt_dec, fmt_len
from src.drawing.layers import (
    BLOCK_HEAVY,
    BLOCK_LIGHT,
    BLOCK_LOGO,
    SHEET_FRAME,
    SHEET_FRAME_HEAVY,
    TABLE,
)
from src.drawing.primitives import (
    Drawing,
    HAlign,
    Image,
    Line,
    Point,
    Polyline,
    Text,
    VAlign,
)
from src.errors import SheetFitError

logger = logging.getLogger(__name__)

AUTO = "auto"
LANDSCAPE = "paisagem"
PORTRAIT = "retrato"

BLOCK_WIDTH_MM = 180.0
BLOCK_HEIGHT_MM = 82.0
MARGIN_LEFT_MM = 20.0
MARGIN_OTHER_MM = 10.0
DRAWING_GAP_MM = 10.0  # between the drawing and the frame, and between it and the block
SUMMARY_GAP_MM = 5.0  # between the summary and the block under it
SUMMARY_INSET_MM = 5.0  # between the summary and the frame's right line
MAX_NOTE_LINES = 6

AUTHOR = "Artur Kalil Corrêa - Trabalho de Conclusão de Curso"
SCALES_TEXT = "1:50 / 1:25"
REVISION = "R00"
UNITS_TEXT = "Cotas em cm"
WARNING = "DOCUMENTO ACADÊMICO — NÃO VÁLIDO PARA EXECUÇÃO"
LOGO_PATH = (
    Path(__file__).resolve().parents[2]
    / "resources/logo/png/vertical/beam-vertical-color@4x.png"
)

FYK_MPA = {"CA-25": 250, "CA-50": 500, "CA-60": 600}
# Least concrete class (fck, MPa) and nominal cover of a beam (cm), by exposure class
CAA_MINIMUMS: dict[str, tuple[int, float]] = {
    "I": (20, 2.5),
    "II": (25, 3.0),
    "III": (30, 4.0),
    "IV": (40, 5.0),
}

# Text sizes (cap heights, mm), the biggest first; a text takes the first that fits
_PROJECT_CAPS = (2.5, 2.2, 2.0)
_AUTHOR_CAPS = (2.5, 2.2, 2.0)
_TITLE_CAPS = (3.5, 3.0, 2.5)
_NOTE_CAPS = (2.0, 1.8, 1.6)
_PAPER_CAPS = (2.5, 2.2, 2.0)
_LABEL_CAP = 1.8
_VALUE_CAP = 2.5
_HEADING_CAP = 2.5
_WARNING_CAP = 2.0
_CONDENSED_RATIO = (
    0.8  # character width over cap height, for the condensed font of the block
)

_CELL_INDENT = 2.5
_NOTES_INDENT = 3.0
_NOTES_TOP = 2.5
_NOTES_TEXT_INDENT = 7.5
_NOTE_PITCH_FACTOR = 1.75  # line pitch over the notes' cap height
_NOTES_HEIGHT = 32.0
_STAMP_BOTTOM = 75.0
_LOGO_BOX = (2.0, 34.0, 36.0, 39.0)  # x, y of the top left corner, width, height (mm)


@dataclass(frozen=True)
class SheetFormat:
    """A paper format and its orientation

    Attributes:
        name: A4, A3, A2, A1 or A0.
        orientation: "paisagem" or "retrato".
        width_mm: Width of the sheet.
        height_mm: Height of the sheet.
        frame_mm: Line weight of the frame.
    """

    name: str
    orientation: str
    width_mm: float
    height_mm: float
    frame_mm: float

    def free_regions(
        self, summary_mm: tuple[float, float] = (0.0, 0.0)
    ) -> dict[str, tuple[float, float]]:
        """Return the width and height (mm) of the rectangles free for the drawing

        Region A is above the block, across the whole frame; region B is left of the block, over the frame's whole height. Both start at the frame's top left corner, plus the gap. A region too small to hold anything is left out.

        Args:
            summary_mm: Width and height of the summary above the block, which takes room from region A; zero for none. Region B is as wide as the block, so the summary, never wider, does not touch it.
        """
        gap = DRAWING_GAP_MM
        inner_w = self.width_mm - MARGIN_LEFT_MM - MARGIN_OTHER_MM
        inner_h = self.height_mm - 2 * MARGIN_OTHER_MM
        regions = {
            "A": (
                inner_w - 2 * gap,
                inner_h - BLOCK_HEIGHT_MM - 2 * gap - _stack_mm(summary_mm),
            ),
            "B": (inner_w - BLOCK_WIDTH_MM - 2 * gap, inner_h - 2 * gap),
        }
        return {name: size for name, size in regions.items() if min(size) > 0}


def _stack_mm(summary_mm: tuple[float, float]) -> float:
    """Return the height the summary takes above the block, with its gap to the block (mm)"""
    return SUMMARY_GAP_MM + summary_mm[1] if summary_mm[1] > 0 else 0.0


# Smallest first; the portrait A4 is only tried when asked for
FORMATS = (
    SheetFormat("A4", PORTRAIT, 210, 297, 0.7),
    SheetFormat("A4", LANDSCAPE, 297, 210, 0.7),
    SheetFormat("A3", LANDSCAPE, 420, 297, 0.7),
    SheetFormat("A2", LANDSCAPE, 594, 420, 0.7),
    SheetFormat("A1", LANDSCAPE, 841, 594, 1.0),
    SheetFormat("A0", LANDSCAPE, 1189, 841, 1.0),
)
_FIT_TOLERANCE_MM = 1e-6


@dataclass(frozen=True)
class SheetPlacement:
    """The sheet chosen for a drawing

    Attributes:
        format: The paper format.
        region: Free region the drawing goes in: "A" (above the block), "B" (left of it) or "L" (the whole frame but the block).
        overflow: Whether the drawing fits no sheet and the biggest one was taken.
    """

    format: SheetFormat
    region: str
    overflow: bool = False


def _region_fitting(
    fmt: SheetFormat,
    width_mm: float,
    height_mm: float,
    boxes: Sequence[Box] = (),
    summary_mm: tuple[float, float] = (0.0, 0.0),
) -> str | None:
    """Return where a drawing of that size fits the sheet, or None

    The first free region (A, then B) that holds its bounding box wins. Failing that, when the boxes of its items are given, the drawing may use the whole area inside the frame as long as no box reaches the block or its gap ("L"): its bounding box is mostly empty at the bottom right, where the block goes.

    Args:
        boxes: x min, y min, x max, y max of each item of the drawing (mm), from the drawing's top left corner, y down.
        summary_mm: Width and height of the summary above the block; zero for none.
    """
    for name, (width, height) in fmt.free_regions(summary_mm).items():
        if (
            width_mm <= width + _FIT_TOLERANCE_MM
            and height_mm <= height + _FIT_TOLERANCE_MM
        ):
            return name
    if not boxes:
        return None
    gap = DRAWING_GAP_MM
    inner_width = fmt.width_mm - MARGIN_LEFT_MM - MARGIN_OTHER_MM - 2 * gap
    inner_height = fmt.height_mm - 2 * MARGIN_OTHER_MM - 2 * gap
    if (
        width_mm > inner_width + _FIT_TOLERANCE_MM
        or height_mm > inner_height + _FIT_TOLERANCE_MM
    ):
        return None
    # The block and its gap, from the drawing's top left corner
    keep_x = inner_width - BLOCK_WIDTH_MM - gap
    keep_y = inner_height - BLOCK_HEIGHT_MM - gap
    summary_x = inner_width - summary_mm[0] - gap
    summary_y = keep_y - _stack_mm(summary_mm)
    if any(
        (x_max > keep_x + _FIT_TOLERANCE_MM and y_max > keep_y + _FIT_TOLERANCE_MM)
        or (
            summary_mm[1] > 0
            and x_max > summary_x + _FIT_TOLERANCE_MM
            and y_max > summary_y + _FIT_TOLERANCE_MM
        )
        for _, _, x_max, y_max in boxes
    ):
        return None
    return "L"


def choose_sheet(
    width_mm: float,
    height_mm: float,
    requested: str = AUTO,
    orientation: str = LANDSCAPE,
    boxes: Sequence[Box] = (),
    summary_mm: tuple[float, float] = (0.0, 0.0),
) -> SheetPlacement:
    """Return the sheet for a drawing: the smallest that fits it, or the one asked for

    The formats are tried from A4 to A0, and the drawing may go above the block or to its left. When nothing fits in ``auto``, the A0 is taken with ``overflow`` set; a fixed format that is too small raises.

    Args:
        width_mm: Width of the drawing on paper.
        height_mm: Height of the drawing on paper.
        requested: "auto" or the format's name.
        orientation: "paisagem" or "retrato"; the portrait exists only for the A4.
        boxes: Boxes of the drawing's items (mm, from its top left corner, y down); with them the drawing may also take the empty corner left of and above the block.
        summary_mm: Width and height of the summary placed above the block; zero for none.

    Raises:
        ValueError: If the format or orientation is unknown, or the portrait is asked for another format than A4.
        SheetFitError: If a fixed format does not hold the drawing.
    """
    if orientation not in (LANDSCAPE, PORTRAIT):
        raise ValueError(f"Unknown sheet orientation '{orientation}'.")
    if requested == AUTO:
        for fmt in FORMATS:
            if fmt.orientation == PORTRAIT and orientation != PORTRAIT:
                continue
            region = _region_fitting(fmt, width_mm, height_mm, boxes, summary_mm)
            if region is not None:
                return SheetPlacement(fmt, region)
        return SheetPlacement(FORMATS[-1], "A", overflow=True)
    matches = [fmt for fmt in FORMATS if fmt.name == requested]
    if not matches:
        raise ValueError(f"Unknown sheet format '{requested}'.")
    chosen = [fmt for fmt in matches if fmt.orientation == orientation]
    if not chosen:
        raise ValueError(f"The {requested} has no {orientation} orientation.")
    fmt = chosen[0]
    region = _region_fitting(fmt, width_mm, height_mm, boxes, summary_mm)
    if region is None:
        raise SheetFitError(
            f"O desenho ({width_mm:.0f} × {height_mm:.0f} mm) não cabe na folha "
            f"{fmt.name} {fmt.orientation}."
        )
    return SheetPlacement(fmt, region)


@dataclass(frozen=True)
class BlockContent:
    """What the block of notes and title block says

    Attributes:
        project: Project name; empty shows a dash.
        title: Title of the sheet, such as VIGA V3 (15×40) — DETALHAMENTO — PAV. TIPO.
        date: Date as written, dd/mm/yyyy.
        sheet: Sheet number and total as written, such as 03/08.
        notes: General notes, without their numbers.
        logo: Image of the vertical logo, which holds the app's name, or None.
        paper: Format of the sheet as written, such as A3; ``build_sheet`` sets it.
    """

    project: str
    title: str
    date: str
    sheet: str
    notes: tuple[str, ...]
    logo: Path | None = LOGO_PATH
    paper: str = ""


def sheet_title(beam_id: str, width_cm: float, height_cm: float) -> str:
    """Return the title of a beam's sheet, in capitals

    Args:
        width_cm: Beam width bw (cm).
        height_cm: Beam height h (cm).
    """
    return (
        f"VIGA {beam_id} ({fmt_len(width_cm)}×{fmt_len(height_cm)}) — "
        "DETALHAMENTO — PAV. TIPO"
    ).upper()


def sheet_number(number: int, total: int) -> str:
    """Return the sheet number as written, with two digits each: 03/08"""
    return f"{number:02d}/{total:02d}"


def general_notes(
    fck_mpa: int,
    steel_longitudinal: str,
    steel_stirrup: str,
    exposure_class: str,
    cover_cm: float,
) -> tuple[str, ...]:
    """Return the five general notes of the sheet, in order

    Args:
        fck_mpa: Characteristic compressive strength of the concrete (MPa).
        steel_longitudinal: Steel of the longitudinal bars as written on the sheet (CA-50).
        steel_stirrup: Steel of the stirrups as written on the sheet.
        exposure_class: Environmental aggressiveness class in Roman numerals.
        cover_cm: Nominal cover (cm).

    Raises:
        ValueError: If a steel is not CA-25, CA-50 or CA-60.
    """
    for steel in (steel_longitudinal, steel_stirrup):
        if steel not in FYK_MPA:
            raise ValueError(f"Unknown steel '{steel}' for the sheet's notes.")
    if steel_longitudinal == steel_stirrup:
        steel_note = (
            f"Aço: {steel_longitudinal} (fyk = {FYK_MPA[steel_longitudinal]} MPa)."
        )
    else:
        steel_note = (
            f"Aço: {steel_longitudinal} nas barras longitudinais "
            f"(fyk = {FYK_MPA[steel_longitudinal]} MPa); {steel_stirrup} nos estribos "
            f"(fyk = {FYK_MPA[steel_stirrup]} MPa)."
        )
    return (
        f"Concreto: C{fck_mpa} (fck = {fck_mpa} MPa).",
        steel_note,
        f"Classe de agressividade ambiental {exposure_class} — "
        f"cobrimento nominal c = {fmt_dec(cover_cm)} cm.",
        "Estribos retangulares fechados, com 2 ramos verticais e ganchos de "
        "fechamento a 135° no canto superior esquerdo.",
        "Projeto conforme ABNT NBR 6118:2026. Cotas em cm, salvo indicação.",
    )


def check_materials(fck_mpa: int, exposure_class: str, cover_cm: float) -> list[str]:
    """Return the warnings for a concrete or a cover below the minimum of the exposure class

    Args:
        fck_mpa: Characteristic compressive strength of the concrete (MPa).
        exposure_class: Environmental aggressiveness class in Roman numerals.
        cover_cm: Nominal cover (cm).

    References:
        ABNT NBR 6118:2026 — Tables 7.1 and 7.2
    """
    if exposure_class not in CAA_MINIMUMS:
        return []
    least_fck, least_cover = CAA_MINIMUMS[exposure_class]
    warnings: list[str] = []
    if fck_mpa < least_fck:
        warnings.append(
            f"fck = {fck_mpa} MPa abaixo do mínimo da CAA {exposure_class} "
            f"(C{least_fck})."
        )
    if cover_cm < least_cover - 1e-9:
        warnings.append(
            f"Cobrimento de {fmt_dec(cover_cm)} cm abaixo do mínimo da CAA "
            f"{exposure_class} ({fmt_dec(least_cover)} cm)."
        )
    return warnings


def _width(text: str, cap_mm: float) -> float:
    """Return the estimated width (mm) of a text in the block's condensed font"""
    return len(text) * _CONDENSED_RATIO * cap_mm


def _fit(text: str, width_mm: float, caps: tuple[float, ...]) -> tuple[str, float]:
    """Return the text and the biggest cap height (mm) at which it fits the width

    Past the smallest size, the text is cut and ends with an ellipsis.
    """
    for cap in caps:
        if _width(text, cap) <= width_mm:
            return text, cap
    cap = caps[-1]
    while text and _width(text + "…", cap) > width_mm:
        text = text[:-1]
    return text.rstrip() + "…", cap


def _wrap(text: str, width_mm: float, cap_mm: float) -> list[str]:
    """Break a text into lines no wider than the width, at spaces"""
    lines: list[str] = []
    line = ""
    for word in text.split():
        candidate = f"{line} {word}" if line else word
        if line and _width(candidate, cap_mm) > width_mm:
            lines.append(line)
            line = word
        else:
            line = candidate
    return [*lines, line]


def _wrapped_notes(
    notes: tuple[str, ...], width_mm: float
) -> tuple[list[list[str]], float]:
    """Return each note's lines and the cap height (mm), the biggest that fits 6 lines in all"""
    for cap in _NOTE_CAPS[:-1]:
        wrapped = [_wrap(note, width_mm, cap) for note in notes]
        if sum(len(lines) for lines in wrapped) <= MAX_NOTE_LINES:
            return wrapped, cap
    cap = _NOTE_CAPS[-1]
    return [_wrap(note, width_mm, cap) for note in notes], cap


def _pt(config: DrawingConfig, x_mm: float, y_mm: float) -> Point:
    """Return the model point (cm) of a block point (mm from its top left corner, y down)"""
    return config.paper(x_mm), -config.paper(y_mm)


def _line(config: DrawingConfig, start: Point, end: Point, layer: str) -> Line:
    """Return a line between two block points (mm, y down)"""
    return Line(_pt(config, *start), _pt(config, *end), layer)


def _text(
    config: DrawingConfig,
    x_mm: float,
    y_mm: float,
    text: str,
    cap_mm: float,
    halign: HAlign = HAlign.LEFT,
    valign: VAlign = VAlign.BASELINE,
) -> Text:
    """Return a text at a block point (mm, y down), its height a cap height in mm"""
    return Text(
        _pt(config, x_mm, y_mm), text, config.paper(cap_mm), TABLE, halign, valign
    )


def _cell(
    config: DrawingConfig,
    box: tuple[float, float, float, float],
    label: str,
    value: str,
    caps: tuple[float, ...] = (_VALUE_CAP,),
) -> list[Text]:
    """Return the label over the value of a title block cell

    Args:
        box: x, y, width and height of the cell in the block (mm).
        caps: Cap heights (mm) the value may take, the biggest first.
    """
    x, y, width, height = box
    text, cap = _fit(value, width - 2 * _CELL_INDENT, caps)
    return [
        _text(config, x + _CELL_INDENT, y + 1.2 + _LABEL_CAP, label, _LABEL_CAP),
        _text(config, x + _CELL_INDENT, y + height - 2.0, text, cap),
    ]


def build_block(
    content: BlockContent, config: DrawingConfig = DEFAULT_CONFIG
) -> Drawing:
    """Return the block of notes, title block and academic warning, its top left corner at the origin

    The block is 180 × 82 mm of paper whatever the sheet.
    """
    drawing = Drawing()
    width, height = BLOCK_WIDTH_MM, BLOCK_HEIGHT_MM
    drawing.add(
        Polyline(
            tuple(
                _pt(config, x, y)
                for x, y in ((0, 0), (width, 0), (width, height), (0, height))
            ),
            (0.0,) * 4,
            BLOCK_HEAVY,
            closed=True,
        ),
        _line(config, (0, _NOTES_HEIGHT), (width, _NOTES_HEIGHT), BLOCK_HEAVY),
        _line(config, (0, _STAMP_BOTTOM), (width, _STAMP_BOTTOM), BLOCK_HEAVY),
    )
    for start, end in (
        ((40, 32), (40, 75)),
        ((40, 42), (width, 42)),
        ((40, 52), (width, 52)),
        ((40, 65), (width, 65)),
        ((135, 42), (135, 52)),
        ((75, 65), (75, 75)),
        ((100, 65), (100, 75)),
        ((125, 65), (125, 75)),
        ((150, 65), (150, 75)),
    ):
        drawing.add(_line(config, start, end, BLOCK_LIGHT))
    drawing.add(*_notes(content.notes, config))
    drawing.add(*_logo_cell(content, config))
    project, project_cap = _fit(content.project or "—", 135.0, _PROJECT_CAPS)
    title, title_cap = _fit(content.title, 135.0, _TITLE_CAPS)
    drawing.add(
        _text(config, 42.5, 32 + 1.2 + _LABEL_CAP, "NOME DO PROJETO", _LABEL_CAP),
        _text(config, 42.5, 32 + 10 - 2.0, project, project_cap),
        _text(config, 42.5, 52 + 1.2 + _LABEL_CAP, "TÍTULO DA FOLHA", _LABEL_CAP),
        _text(config, 42.5, 52 + 13 - 2.5, title, title_cap),
    )
    drawing.add(*_cell(config, (40, 42, 95, 10), "AUTOR", AUTHOR, _AUTHOR_CAPS))
    drawing.add(*_cell(config, (135, 42, 45, 10), "DATA", content.date))
    drawing.add(*_cell(config, (40, 65, 35, 10), "ESCALAS", SCALES_TEXT))
    drawing.add(*_cell(config, (75, 65, 25, 10), "FORMATO", content.paper, _PAPER_CAPS))
    drawing.add(*_cell(config, (100, 65, 25, 10), "FOLHA", content.sheet))
    drawing.add(*_cell(config, (125, 65, 25, 10), "REV.", REVISION))
    drawing.add(*_cell(config, (150, 65, 30, 10), "UNIDADES", UNITS_TEXT))
    drawing.add(
        _text(
            config,
            width / 2,
            (_STAMP_BOTTOM + height) / 2,
            WARNING,
            _WARNING_CAP,
            HAlign.CENTER,
            VAlign.MIDDLE,
        )
    )
    return drawing


def _notes(notes: tuple[str, ...], config: DrawingConfig) -> list[Text]:
    """Return the heading and the numbered notes, wrapped to fit six lines"""
    texts = [
        _text(
            config,
            _NOTES_INDENT,
            _NOTES_TOP + _HEADING_CAP,
            "NOTAS GERAIS",
            _HEADING_CAP,
        )
    ]
    wrapped, cap = _wrapped_notes(
        notes, BLOCK_WIDTH_MM - _NOTES_TEXT_INDENT - _NOTES_INDENT
    )
    pitch = _NOTE_PITCH_FACTOR * cap
    y = _NOTES_TOP + _HEADING_CAP + 2.0 + cap
    for number, lines in enumerate(wrapped, start=1):
        texts.append(_text(config, _NOTES_INDENT, y, f"{number}.", cap))
        for line in lines:
            texts.append(_text(config, _NOTES_TEXT_INDENT, y, line, cap))
            y += pitch
    return texts


def _logo_cell(content: BlockContent, config: DrawingConfig) -> list[Image]:
    """Return the logo, which already carries the app's name, filling the first column"""
    if content.logo is None:
        return []
    x, y, width, height = _LOGO_BOX
    return [
        Image(
            _pt(config, x, y + height),
            config.paper(width),
            config.paper(height),
            str(content.logo),
            BLOCK_LOGO,
        )
    ]


def _frame(fmt: SheetFormat, config: DrawingConfig) -> Polyline:
    """Return the frame of the sheet, 20 mm from the left edge and 10 mm from the others"""
    left, bottom = MARGIN_LEFT_MM, MARGIN_OTHER_MM
    right, top = fmt.width_mm - MARGIN_OTHER_MM, fmt.height_mm - MARGIN_OTHER_MM
    corners = ((left, bottom), (right, bottom), (right, top), (left, top))
    return Polyline(
        tuple((config.paper(x), config.paper(y)) for x, y in corners),
        (0.0,) * 4,
        SHEET_FRAME_HEAVY if fmt.frame_mm > 0.7 else SHEET_FRAME,
        closed=True,
    )


def _paper_text(fmt: SheetFormat) -> str:
    """Return the format as written in the title block: A3, or A4 (retrato) for the portrait"""
    return (
        fmt.name if fmt.orientation == LANDSCAPE else f"{fmt.name} ({fmt.orientation})"
    )


def build_sheet(
    content: Drawing,
    block: BlockContent,
    config: DrawingConfig = DEFAULT_CONFIG,
    summary: Drawing | None = None,
) -> tuple[Drawing, SheetPlacement]:
    """Put a drawing on a sheet: choose the format, place the drawing, and add the frame, the block and the summary

    The drawing's top left corner goes to the top left of the free region, so it never touches the block. The sheet's lower left corner is the origin of the result, whose ``paper_mm`` holds the sheet's size.

    Args:
        content: The beam's drawing, in model space (cm).
        block: What the notes and the title block say.
        summary: The consumption summary, put on the right 5 mm above the block, 5 mm from the frame's right line; it is not part of ``content``.

    Returns:
        The sheet's drawing and the placement chosen.

    Raises:
        SheetFitError: If ``config.sheet_format`` is a fixed format that does not hold the drawing.
    """
    x_min, y_min, x_max, y_max = content.bounds()
    width_mm = config.on_paper(x_max - x_min)
    height_mm = config.on_paper(y_max - y_min)
    boxes = [
        (
            config.on_paper(left - x_min),
            config.on_paper(y_max - top),
            config.on_paper(right - x_min),
            config.on_paper(y_max - bottom),
        )
        for left, bottom, right, top in item_boxes(content, config)
    ]
    summary_mm = (0.0, 0.0)
    if summary is not None:
        s_left, s_bottom, s_right, s_top = summary.bounds()
        summary_mm = (
            config.on_paper(s_right - s_left),
            config.on_paper(s_top - s_bottom),
        )
    placement = choose_sheet(
        width_mm,
        height_mm,
        config.sheet_format,
        config.sheet_orientation,
        boxes,
        summary_mm,
    )
    fmt = placement.format
    if placement.overflow:
        logger.warning(
            "O desenho (%.0f × %.0f mm) não cabe em nenhuma folha; usada a A0.",
            width_mm,
            height_mm,
        )
    left = config.paper(MARGIN_LEFT_MM + DRAWING_GAP_MM)
    top = config.paper(fmt.height_mm - MARGIN_OTHER_MM - DRAWING_GAP_MM)
    sheet = content.translated(left - x_min, top - y_max)
    sheet.add(_frame(fmt, config))
    sheet.extend(
        build_block(replace(block, paper=_paper_text(fmt)), config).translated(
            config.paper(fmt.width_mm - BLOCK_WIDTH_MM - MARGIN_OTHER_MM),
            config.paper(MARGIN_OTHER_MM + BLOCK_HEIGHT_MM),
        )
    )
    if summary is not None:
        s_left, s_bottom, s_right, _ = summary.bounds()
        sheet.extend(
            summary.translated(
                config.paper(fmt.width_mm - MARGIN_OTHER_MM - SUMMARY_INSET_MM)
                - s_right,
                config.paper(MARGIN_OTHER_MM + BLOCK_HEIGHT_MM + SUMMARY_GAP_MM)
                - s_bottom,
            )
        )
    sheet.paper_mm = (fmt.width_mm, fmt.height_mm)
    return sheet, placement
