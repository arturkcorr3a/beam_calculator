"""Reinforcement notation: "2Φ16 + 1Φ12,5", "Φ5 c/15 cm", "1Φ12,5 (l = 74,3 cm)"."""

from collections.abc import Callable, Sequence

from pavement_ui.core.results.beam_design import SkinDesign
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


def fmt_hook(length_cm: float) -> str:
    """Format one side's hook length, e.g. "11,5 cm" """
    return s.HOOK.format(length=fmt_length_cm(length_cm))


def _fmt_sides(left: str | None, right: str | None) -> str | None:
    """Join a layer's per-side items, e.g. "esq. … · dir. …"; None when both are None"""
    sides: list[str] = []
    if left is not None:
        sides.append(s.SIDE_LEFT.format(value=left))
    if right is not None:
        sides.append(s.SIDE_RIGHT.format(value=right))
    return s.SIDE_JOIN.join(sides) if sides else None


def _fmt_clamp_sides(layer: BarLayer) -> str | None:
    """Format a layer's clamps by side; None without clamps"""
    return _fmt_sides(
        None if layer.left_clamps is None else fmt_clamp(layer.left_clamps),
        None if layer.right_clamps is None else fmt_clamp(layer.right_clamps),
    )


def _fmt_hook_sides(layer: BarLayer) -> str | None:
    """Format a layer's hooks by side; None without hooks"""
    return _fmt_sides(
        None if layer.left_hook_cm is None else fmt_hook(layer.left_hook_cm),
        None if layer.right_hook_cm is None else fmt_hook(layer.right_hook_cm),
    )


def _fmt_sides_cell(
    tension: Sequence[BarLayer],
    compression: Sequence[BarLayer],
    fmt_layer_sides: Callable[[BarLayer], str | None],
) -> str:
    """Format every layer's per-side items for a table cell

    Compressed layers are prefixed so their numbers don't mix with the
    tensioned ones.
    """
    items: list[str] = []
    for layers, template in (
        (tension, s.SIDES_LAYER_ITEM),
        (compression, s.SIDES_COMPRESSION_ITEM),
    ):
        for layer in layers:
            sides = fmt_layer_sides(layer)
            if sides is not None:
                items.append(template.format(index=layer.index, sides=sides))
    return s.LAYER_JOIN.join(items) if items else s.NONE


def fmt_clamps_cell(
    tension: Sequence[BarLayer], compression: Sequence[BarLayer]
) -> str:
    """Format every layer's clamps for a table cell, e.g. "Camada 1: esq. 1Φ12,5 (l = 74,3 cm)" """
    return _fmt_sides_cell(tension, compression, _fmt_clamp_sides)


def fmt_hooks_cell(tension: Sequence[BarLayer], compression: Sequence[BarLayer]) -> str:
    """Format every layer's hooks for a table cell, e.g. "Camada 1: esq. 11,5 cm · dir. 11,5 cm" """
    return _fmt_sides_cell(tension, compression, _fmt_hook_sides)


def fmt_skin(skin: SkinDesign | None) -> str:
    """Format a span's skin bars on each face, e.g. "6Φ6,3 c/8,8 cm (PELE)"; "—" when not required"""
    if skin is None:
        return s.NONE
    return s.SKIN.format(
        count=skin.bars_per_face,
        phi=s.PHI,
        diameter=fmt_bar_diameter(skin.diameter_mm),
        spacing=fmt_length_cm(skin.spacing_cm),
    )


def fmt_stirrup(stirrup: StirrupSpec, prefixed: bool = False) -> str:
    """Format stirrups, e.g. "Φ5 c/15 cm"; with prefixed, "Estribo: Φ5 c/15 cm"

    Scaled stirrups list each zone along the beam, e.g.
    "Φ8: c/13 cm (0,00–0,56 m) · c/30 cm (0,56–2,44 m) · c/13 cm (2,44–3,00 m)".
    """
    diameter = fmt_bar_diameter(stirrup.diameter_mm)
    if stirrup.is_scaled:
        zones = s.STIRRUP_ZONE_JOIN.join(
            s.STIRRUP_ZONE.format(
                spacing=fmt_length_cm(zone.spacing_cm),
                start=fmt_number(zone.start_m, 2),
                end=fmt_number(zone.end_m, 2),
            )
            for zone in stirrup.zones
        )
        text = s.STIRRUP_SCALED.format(phi=s.PHI, diameter=diameter, zones=zones)
    else:
        text = s.STIRRUP.format(
            phi=s.PHI, diameter=diameter, spacing=fmt_length_cm(stirrup.spacing_cm)
        )
    return s.STIRRUP_PREFIXED.format(stirrup=text) if prefixed else text
