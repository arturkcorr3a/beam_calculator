"""Reinforcement notation: "2Φ16 + 1Φ12,5", "Φ5 c/15 cm", "1Φ12,5 (l = 74,3 cm)"."""

from collections.abc import Sequence

from pavement_ui.core.results.reinforcement import (
    BarGroup,
    BarLayer,
    ClampSpec,
    StirrupSpec,
)
from pavement_ui.presentation.formatting.numbers import fmt_length_cm, fmt_number
from pavement_ui.presentation.text.strings import formatting as s


def fmt_bar_diameter(diameter_mm: float) -> str:
    """Format a bar diameter (mm) without needless decimals: 12.5 → "12,5", 16.0 → "16" """
    decimals = 0 if float(diameter_mm).is_integer() else 1
    return fmt_number(diameter_mm, decimals)


def _fmt_group(group: BarGroup) -> str:
    return f"{group.count}{s.PHI}{fmt_bar_diameter(group.diameter_mm)}"


def fmt_bar_layer(layer: BarLayer) -> str:
    """Format the bars of a layer, e.g. "2Φ16 + 1Φ12,5" """
    return s.GROUP_JOIN.join(_fmt_group(group) for group in layer.groups)


def fmt_tension_cell(layers: Sequence[BarLayer]) -> str:
    """Format every layer for a table cell, e.g. "Camada 1: 2Φ12,5 · Camada 2: 2Φ10" """
    if not layers:
        return s.NONE
    return s.LAYER_JOIN.join(
        s.LAYER_ITEM.format(index=layer.index, bars=fmt_bar_layer(layer))
        for layer in layers
    )


def fmt_clamp(clamp: ClampSpec) -> str:
    """Format one side's clamps, e.g. "1Φ12,5 (l = 74,3 cm)" """
    return s.CLAMP.format(
        quantity=clamp.quantity,
        phi=s.PHI,
        diameter=fmt_bar_diameter(clamp.diameter_mm),
        length=fmt_length_cm(clamp.length_cm),
    )


def _fmt_clamp_sides(layer: BarLayer) -> str | None:
    """Format a layer's clamps by side, e.g. "esq. … · dir. …"; None without clamps"""
    sides: list[str] = []
    if layer.left_clamps is not None:
        sides.append(s.CLAMP_LEFT.format(clamp=fmt_clamp(layer.left_clamps)))
    if layer.right_clamps is not None:
        sides.append(s.CLAMP_RIGHT.format(clamp=fmt_clamp(layer.right_clamps)))
    return s.CLAMP_SIDE_JOIN.join(sides) if sides else None


def fmt_clamps_cell(
    tension: Sequence[BarLayer], compression: Sequence[BarLayer]
) -> str:
    """Format every layer's clamps for a table cell, e.g. "Camada 1: esq. 1Φ12,5 (l = 74,3 cm)"

    Compressed layers are prefixed so their numbers don't mix with the
    tensioned ones.
    """
    items: list[str] = []
    for layers, template in (
        (tension, s.CLAMP_LAYER_ITEM),
        (compression, s.CLAMP_COMPRESSION_ITEM),
    ):
        for layer in layers:
            sides = _fmt_clamp_sides(layer)
            if sides is not None:
                items.append(template.format(index=layer.index, sides=sides))
    return s.LAYER_JOIN.join(items) if items else s.NONE


def fmt_stirrup(stirrup: StirrupSpec, prefixed: bool = False) -> str:
    """Format stirrups, e.g. "Φ5 c/15 cm"; with prefixed, "Estribo: Φ5 c/15 cm" """
    text = s.STIRRUP.format(
        phi=s.PHI,
        diameter=fmt_bar_diameter(stirrup.diameter_mm),
        spacing=fmt_length_cm(stirrup.spacing_cm),
    )
    return s.STIRRUP_PREFIXED.format(stirrup=text) if prefixed else text
