"""Tables and texts of the sheet: materials summary and line legend

Every block is drawn with its top left corner at the origin; the layout moves it into
place. See docs/especificacao_desenho.md, §6.9 and §6.10.
"""

from collections.abc import Sequence

from src.detailing.quantities import SteelQuantity
from src.drawing.config import DrawingConfig
from src.drawing.formatting import (
    PHI,
    fmt_dec,
    fmt_diam,
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


def legend_block(layers_in_use: Sequence[str], config: DrawingConfig) -> Drawing:
    """Return the legend of the line types in use

    Args:
        layers_in_use: The drawing's layers; the legend shows the ones in ``LEGEND_LAYERS``.
    """
    paper = config.paper
    label = paper(config.text_heights_mm.label)
    pitch = _LINE_PITCH * label
    drawing = Drawing([Text((0.0, 0.0), "LEGENDA", label, TABLE)])
    x = 0.0
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
