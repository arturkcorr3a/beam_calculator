"""Annotations shared by the sheet's blocks: dimensions, bar layers and tooltips"""

from math import sqrt

from src.detailing.detailed_bar import BarRole, DetailedBar
from src.detailing.detailed_clamps import DetailedClamps
from src.detailing.detailed_skin_bars import DetailedSkinBars
from src.detailing.detailing_beam import DetailingBeam
from src.drawing.config import DrawingConfig
from src.drawing.formatting import PHI, fmt_diam, fmt_len, fmt_steel
from src.drawing.geometry import overlap_pairs
from src.drawing.layers import CONSTRUCTION_BAR, MAIN_BAR
from src.drawing.primitives import Drawing, HAlign, HoverInfo, Line, Text, VAlign

DIMENSION_TEXT_GAP_MM = 1.2  # between a dimension line and its text
_TICK_MM = 2.0


def bar_layer(bar: DetailedBar) -> str:
    """Return the layer of a bar run: main or construction bars"""
    return CONSTRUCTION_BAR if bar.role is BarRole.CONSTRUCTION else MAIN_BAR


def _face_name(is_bottom: bool) -> str:
    """Return the name of a face, as written on the sheet"""
    return "inferior" if is_bottom else "superior"


def bar_hover(beam: DetailingBeam, bar: DetailedBar) -> HoverInfo:
    """Return the tooltip of a bar run: mark, cut length, extent and laps"""
    laps: dict[str, list[str]] = {}
    for left, right, start, end in overlap_pairs(beam, bar.is_bottom):
        if bar is left or bar is right:
            other = right if bar is left else left
            laps.setdefault(fmt_len(end - start), []).append(str(other.mark))
    lines = [
        f"C = {fmt_len(bar.total_length)} cm (reta {fmt_len(bar.straight_length)}, "
        f"ganchos {fmt_len(bar.left_hook_length)} + {fmt_len(bar.right_hook_length)})",
        f"x = {fmt_len(bar.start)} → {fmt_len(bar.end)} · "
        f"{_face_name(bar.is_bottom)} · camada {bar.layer_index}",
    ]
    lines += [
        f"traspasse {length} com {' e '.join(marks)}" for length, marks in laps.items()
    ]
    return HoverInfo(
        f"{bar.mark} · {bar.quantity} {PHI}{fmt_diam(bar.diameter_mm)} "
        f"{fmt_steel(bar.steel.name)}",
        tuple(lines),
    )


def skin_hover(skin: DetailedSkinBars) -> HoverInfo:
    """Return the tooltip of a span's skin bars: mark, cut length, extent and row heights"""
    heights = ", ".join(fmt_len(y) for y in skin.heights)
    return HoverInfo(
        f"{skin.mark} · {skin.quantity} {PHI}{fmt_diam(skin.diameter_mm)} "
        f"{fmt_steel(skin.steel.name)} (pele)",
        (
            f"C = {fmt_len(skin.total_length)} cm",
            f"x = {fmt_len(skin.start)} → {fmt_len(skin.end)} · vão {skin.span_name}",
            f"2 faces laterais · y = {heights}",
        ),
    )


def clamp_hover(clamps: DetailedClamps) -> HoverInfo:
    """Return the tooltip of a clamp set: mark, cut length, leg, width and bend"""
    return HoverInfo(
        f"{clamps.mark} · {clamps.quantity} {PHI}{fmt_diam(clamps.diameter_mm)} "
        f"{fmt_steel(clamps.steel.name)} (grampo)",
        (
            f"C = {fmt_len(clamps.total_length)} cm",
            f"perna {fmt_len(clamps.leg_length)} · largura {fmt_len(clamps.width)}",
            f"dobra em x = {fmt_len(clamps.position)} · {_face_name(clamps.is_bottom)}",
        ),
    )


def dimension(
    start: float,
    end: float,
    y: float,
    layer: str,
    config: DrawingConfig,
    above: str | None = None,
    below: str | None = None,
) -> Drawing:
    """Return a horizontal dimension: a line, a 45° tick on each end and centered texts

    Args:
        start: Left end (cm).
        end: Right end (cm).
        y: Height of the line (cm).
        above: Text over the line, its baseline 1.2 mm above it.
        below: Text under the line, its top 1.2 mm below it.
    """
    half = config.paper(_TICK_MM) / 2 / sqrt(2)
    height = config.paper(config.text_heights_mm.small)
    gap = config.paper(DIMENSION_TEXT_GAP_MM)
    middle = (start + end) / 2
    drawing = Drawing(
        [
            Line((start, y), (end, y), layer),
            Line((start - half, y - half), (start + half, y + half), layer),
            Line((end - half, y - half), (end + half, y + half), layer),
        ]
    )
    if above:
        drawing.add(Text((middle, y + gap), above, height, layer, HAlign.CENTER))
    if below:
        drawing.add(
            Text((middle, y - gap), below, height, layer, HAlign.CENTER, VAlign.TOP)
        )
    return drawing


def vertical_dimension(
    x: float,
    bottom: float,
    top: float,
    layer: str,
    config: DrawingConfig,
    text: str,
) -> Drawing:
    """Return a vertical dimension: a line, a 45° tick on each end and a text turned 90° on its left

    Args:
        x: Abscissa of the line (cm).
        bottom: Lower end (cm).
        top: Upper end (cm).
    """
    half = config.paper(_TICK_MM) / 2 / sqrt(2)
    return Drawing(
        [
            Line((x, bottom), (x, top), layer),
            Line((x - half, bottom - half), (x + half, bottom + half), layer),
            Line((x - half, top - half), (x + half, top + half), layer),
            Text(
                (x - config.paper(DIMENSION_TEXT_GAP_MM), (bottom + top) / 2),
                text,
                config.paper(config.text_heights_mm.small),
                layer,
                HAlign.CENTER,
                VAlign.BASELINE,
                90.0,
            ),
        ]
    )
