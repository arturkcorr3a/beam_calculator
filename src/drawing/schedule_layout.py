"""Tables and texts of the sheet: bar schedule, materials summary, notes, line legend and title block

Every block is drawn with its top left corner at the origin; the layout moves it into
place. See docs/especificacao_desenho.md, §6.9 to §6.11.
"""

from collections.abc import Sequence

from src.detailing.bar_schedule import ScheduleRow
from src.detailing.quantities import SteelQuantity
from src.drawing.config import DrawingConfig
from src.drawing.formatting import (
    PHI,
    fmt_dec,
    fmt_diam,
    fmt_len,
    text_width,
)
from src.drawing.layers import (
    AXIS,
    CLAMP,
    CONSTRUCTION_BAR,
    DIMENSION,
    LAP,
    MAIN_BAR,
    STIRRUP,
    TABLE,
    layer_style,
)
from src.drawing.primitives import Drawing, HAlign, Line, Polyline, Text, VAlign

SCHEDULE_COLUMNS_MM: tuple[tuple[str, float], ...] = (
    ("POS", 13.0),
    (f"{PHI} (mm)", 13.0),
    ("QUANT", 15.0),
    ("C. UNIT (cm)", 24.0),
    ("C. TOTAL (cm)", 26.0),
)
SUMMARY_COLUMNS_MM: tuple[tuple[str, float], ...] = (
    (PHI, 10.0),
    ("COMPR. (m)", 15.0),
    ("MASSA (kg)", 15.0),
)
LEGEND_LAYERS = (MAIN_BAR, CONSTRUCTION_BAR, STIRRUP, CLAMP, AXIS, DIMENSION, LAP)

_HEADER_MM = 5.0
_CELL_PADDING_MM = 1.0  # least room on each side of a cell's text
_ROW_MM = 4.0
_CELL_BASELINE_MM = 1.2  # from a cell's bottom to its text's baseline
_TITLE_GAP_MM = 2.0  # from a title's baseline to its table's top
_LINE_PITCH = 1.6  # between text lines, in text heights
_BLOCK_GAP_MM = 4.0  # from a table to the texts under it
_SAMPLE_MM = 12.0  # length of a line sample in the legend
_SAMPLE_GAP_MM = 3.0
_LEGEND_GAP_MM = 15.0  # from the notes to the legend
_TITLE_BLOCK_WIDTH_MM = 44.0
_TITLE_BAND_MM = 7.0
_FIELD_BAND_MM = 7.0
_FOOTER_BAND_MM = 5.0
_BLOCK_MARGIN_MM = 1.5
_FIELD_LABEL_MM = 2.6  # from a band's top to its label's baseline
_FIELD_VALUE_MM = 5.6  # from a band's top to its value's baseline


def _rectangle(left: float, top: float, right: float, bottom: float) -> Polyline:
    """Return a closed rectangle on the table layer"""
    return Polyline(
        ((left, top), (right, top), (right, bottom), (left, bottom)),
        (0.0,) * 4,
        TABLE,
        closed=True,
    )


def table(
    title: str,
    columns: Sequence[tuple[str, float]],
    rows: Sequence[Sequence[str]],
    config: DrawingConfig,
) -> Drawing:
    """Return a titled table, its top left corner at the origin

    A column grows past its given width when a cell would not fit in it.

    Args:
        columns: Header and least width (mm of paper) of each column.
        rows: The cells of each row, one per column.
    """
    paper = config.paper
    small = paper(config.text_heights_mm.small)
    pad = paper(_CELL_PADDING_MM)
    widths = [
        max(
            paper(width),
            max(text_width(cell, small) for cell in [name, *(row[i] for row in rows)])
            + 2 * pad,
        )
        for i, (name, width) in enumerate(columns)
    ]
    right = sum(widths)
    header = paper(_HEADER_MM)
    row_height = paper(_ROW_MM)
    bottom = -header - row_height * len(rows)
    drawing = Drawing(
        [
            Text(
                (0.0, paper(_TITLE_GAP_MM)),
                title,
                paper(config.text_heights_mm.label),
                TABLE,
            ),
            _rectangle(0.0, 0.0, right, bottom),
        ]
    )
    x = 0.0
    for width in widths[:-1]:
        x += width
        drawing.add(Line((x, 0.0), (x, bottom), TABLE))
    tops = [0.0]
    for index in range(len(rows)):
        tops.append(-header - index * row_height)
        drawing.add(Line((0.0, tops[-1]), (right, tops[-1]), TABLE))
    cells: list[Sequence[str]] = [[name for name, _ in columns], *rows]
    heights = [header, *([row_height] * len(rows))]
    for top, height, row in zip(tops, heights, cells, strict=True):
        x = 0.0
        for width, cell in zip(widths, row, strict=True):
            drawing.add(
                Text(
                    (x + width / 2, top - height + paper(_CELL_BASELINE_MM)),
                    cell,
                    small,
                    TABLE,
                    HAlign.CENTER,
                )
            )
            x += width
    return drawing


def schedule_table(rows: Sequence[ScheduleRow], config: DrawingConfig) -> Drawing:
    """Return the bar schedule: mark, diameter, quantity, unit and total cut lengths"""
    cells = [
        [
            row.mark,
            fmt_diam(row.diameter_mm),
            str(row.quantity),
            fmt_len(row.unit_length),
            fmt_len(row.total_length),
        ]
        for row in rows
    ]
    return table("QUADRO DE FERROS", SCHEDULE_COLUMNS_MM, cells, config)


def summary_table(
    steel_name: str,
    steel: Sequence[SteelQuantity],
    concrete_m3: float,
    formwork_m2: float,
    config: DrawingConfig,
) -> Drawing:
    """Return the materials summary: steel by diameter with its total, then concrete, formwork and steel ratio

    Args:
        steel_name: Name of the steel as written on the sheet (CA-50).
        concrete_m3: Concrete volume (m³).
        formwork_m2: Formwork area (m²).
    """
    paper = config.paper
    mass = sum(item.mass_kg for item in steel)
    cells = [
        [fmt_diam(item.diameter_mm), fmt_dec(item.length_m), fmt_dec(item.mass_kg)]
        for item in steel
    ]
    cells.append(
        ["TOTAL", fmt_dec(sum(item.length_m for item in steel)), fmt_dec(mass)]
    )
    drawing = table(f"RESUMO {steel_name}", SUMMARY_COLUMNS_MM, cells, config)
    small = paper(config.text_heights_mm.small)
    y = drawing.bounds()[1] - paper(_BLOCK_GAP_MM)
    texts = [
        f"Concreto: {fmt_dec(concrete_m3, 2)} m³",
        f"Fôrma: {fmt_dec(formwork_m2, 1)} m²",
    ]
    if concrete_m3 > 0:
        texts.append(f"Taxa de aço: {round(mass / concrete_m3)} kg/m³")
    for text in texts:
        drawing.add(Text((0.0, y), text, small, TABLE, valign=VAlign.TOP))
        y -= _LINE_PITCH * small
    return drawing


def note_lines(
    steel_name: str,
    concrete: str | None,
    exposure_class: str | None,
    covers: Sequence[float],
) -> list[str]:
    """Return the sheet's notes, numbered; the parts without data are left out

    Args:
        steel_name: Name of the steel as written on the sheet (CA-50).
        covers: The distinct nominal covers of the beams (cm).
    """
    material = f"Aço {steel_name}"
    if concrete is not None:
        material += f"; concreto {concrete}"
        if exposure_class is not None:
            material += f", classe de agressividade {exposure_class}"
    elif exposure_class is not None:
        material += f"; classe de agressividade {exposure_class}"
    distinct = sorted(set(covers))
    if len(distinct) == 1:
        cover = f"Cobrimento nominal c = {fmt_len(distinct[0])} cm."
    else:
        values = " e ".join(
            [", ".join(fmt_len(c) for c in distinct[:-1]), fmt_len(distinct[-1])]
        )
        cover = f"Cobrimentos nominais c = {values} cm."
    notes = [
        f"Medidas em cm; bitolas ({PHI}) em mm.",
        f"{material}.",
        cover,
        "Comprimentos de corte líquidos, sem perdas.",
        "Estribos fechados de 2 ramos, ganchos a 135°.",
    ]
    return [f"{index}. {note}" for index, note in enumerate(notes, start=1)]


def notes_block(
    notes: Sequence[str], layers_in_use: Sequence[str], config: DrawingConfig
) -> Drawing:
    """Return the notes and, on their right, the legend of the line types in use

    Args:
        notes: The numbered notes.
        layers_in_use: The drawing's layers; the legend shows the ones in ``LEGEND_LAYERS``.
    """
    paper = config.paper
    label = paper(config.text_heights_mm.label)
    pitch = _LINE_PITCH * label
    drawing = Drawing([Text((0.0, 0.0), "NOTAS", label, TABLE)])
    for index, note in enumerate(notes, start=1):
        drawing.add(Text((0.0, -index * pitch), note, label, TABLE))
    widest = max((text_width(note, label) for note in notes), default=0.0)
    x = widest + paper(_LEGEND_GAP_MM)
    drawing.add(Text((x, 0.0), "LEGENDA", label, TABLE))
    sample = paper(_SAMPLE_MM)
    shown = [name for name in LEGEND_LAYERS if name in layers_in_use]
    for index, name in enumerate(shown, start=1):
        y = -index * pitch + label / 2
        drawing.add(
            Line((x, y), (x + sample, y), name),
            Text(
                (x + sample + paper(_SAMPLE_GAP_MM), -index * pitch),
                layer_style(name).description,
                label,
                TABLE,
            ),
        )
    return drawing


def title_block(
    title: str,
    fields: Sequence[tuple[str, str]],
    footer_left: str,
    footer_right: str,
    config: DrawingConfig,
) -> Drawing:
    """Return the title block: a title band, one band per field and a footer, its top left at the origin

    The block is 44 mm of paper wide, or wider when a text needs it.

    Args:
        fields: Label and value of each field band.
        footer_left: Text on the footer's left, such as the date.
        footer_right: Text on the footer's right, such as the sheet number; may be empty.
    """
    paper = config.paper
    heights = config.text_heights_mm
    small = paper(heights.small)
    big = paper(heights.title_block)
    margin = paper(_BLOCK_MARGIN_MM)
    needed = max(
        [text_width(title, big)]
        + [text_width(text, small) for field in fields for text in field]
        + [text_width(f"{footer_left}  {footer_right}", small)]
    )
    width = max(paper(_TITLE_BLOCK_WIDTH_MM), needed + 2 * margin)
    band = paper(_FIELD_BAND_MM)
    title_band = paper(_TITLE_BAND_MM)
    footer = paper(_FOOTER_BAND_MM)
    bottom = -(title_band + band * len(fields) + footer)
    drawing = Drawing(
        [
            _rectangle(0.0, 0.0, width, bottom),
            Text((margin, -title_band / 2), title, big, TABLE, valign=VAlign.MIDDLE),
        ]
    )
    top = -title_band
    for label, value in fields:
        drawing.add(
            Line((0.0, top), (width, top), TABLE),
            Text((margin, top - paper(_FIELD_LABEL_MM)), label, small, TABLE),
            Text((margin, top - paper(_FIELD_VALUE_MM)), value, small, TABLE),
        )
        top -= band
    drawing.add(
        Line((0.0, top), (width, top), TABLE),
        Text(
            (margin, top - footer / 2), footer_left, small, TABLE, valign=VAlign.MIDDLE
        ),
    )
    if footer_right:
        drawing.add(
            Text(
                (width - margin, top - footer / 2),
                footer_right,
                small,
                TABLE,
                HAlign.RIGHT,
                VAlign.MIDDLE,
            )
        )
    return drawing
