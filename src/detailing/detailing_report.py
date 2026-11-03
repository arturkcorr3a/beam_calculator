from __future__ import annotations

from typing import TYPE_CHECKING

from src.text_table import format_table

if TYPE_CHECKING:
    from src.detailing.detailed_bar import DetailedBar
    from src.detailing.detailing_beam import DetailingBeam
    from src.structural_elements.rebar import HookGeometry


def build_report(beam: DetailingBeam) -> str:
    """Describe a detailing beam as plain text

    Lists the section, the longitudinal bars of each face (by layer, left to right), the clamps and the stirrups of each span. Positions (x) follow the beam's analysis axis; heights (y) are measured from the bottom face.

    Returns:
        Multi-line plain-text report.
    """
    title = f" Beam {beam.beam_id} — detailing"
    rule = "═" * max(72, len(title) + 1)
    lines = [rule, title, rule, "", "Section"]
    lines += _section(beam)
    for is_bottom in (True, False):
        face = "bottom" if is_bottom else "top"
        lines += ["", f"Longitudinal bars — {face}"]
        lines += _bars(beam.bars_on_face(is_bottom))
    lines += ["", "Clamps"]
    lines += _clamps(beam)
    lines += ["", "Stirrups"]
    lines += _stirrups(beam)
    return "\n".join(lines)


def _section(beam: DetailingBeam) -> list[str]:
    """Describe the section, steel, cover and extent of the beam"""
    items = [
        ("b_w x h", f"{beam.width:g} x {beam.height:g} cm"),
        ("Steel", beam.steel.name),
        ("Nominal cover", f"{beam.nominal_covering:.1f} cm"),
        ("Extent", f"{beam.start:.1f} – {beam.end:.1f} cm"),
        ("Layer y", "bar axis, from bottom edge"),
    ]
    width = max(len(key) for key, _ in items)
    return [f"  {key:<{width}}    {value}" for key, value in items]


def _bars(bars: list[DetailedBar]) -> list[str]:
    """Tabulate bar runs: layer, height, bars, extent, hooks, cut length, role and source"""
    if not bars:
        return ["  none"]
    rows = [
        [
            str(bar.layer_index),
            f"{bar.y:.2f}",
            f"{bar.quantity}φ{bar.diameter_mm:g}",
            f"{bar.start:.1f}",
            f"{bar.end:.1f}",
            _hook(bar.left_hook, bar.left_hook_length),
            _hook(bar.right_hook, bar.right_hook_length),
            f"{bar.total_length:.1f}",
            bar.role.value,
            "—" if bar.source_position is None else f"{bar.source_position:.2f}",
        ]
        for bar in bars
    ]
    headers = [
        "Layer",
        "y (cm)",
        "Bars",
        "From (cm)",
        "To (cm)",
        "Hook L (cm)",
        "Hook R (cm)",
        "Length (cm)",
        "Role",
        "Source x (cm)",
    ]
    return format_table(headers, rows, "  ")


def _hook(hook: HookGeometry | None, length: float) -> str:
    """Summarize a hook as its extra cut length (cm), or 'no' if there is none"""
    return "no" if hook is None else f"{length:.1f}"


def _clamps(beam: DetailingBeam) -> list[str]:
    """Tabulate the clamps: face, side, bars, bend position, leg, width and cut length"""
    if not beam.clamps:
        return ["  none"]
    rows = [
        [
            "bottom" if clamps.is_bottom else "top",
            "left" if clamps.left else "right",
            f"{clamps.quantity}φ{clamps.diameter_mm:g}",
            f"{clamps.position:.1f}",
            f"{clamps.leg_length:.1f}",
            f"{clamps.width:.1f}",
            f"{clamps.total_length:.1f}",
            f"{clamps.source_position:.2f}",
        ]
        for clamps in beam.clamps
    ]
    headers = [
        "Face",
        "Side",
        "Bars",
        "Bend x (cm)",
        "Leg (cm)",
        "Width (cm)",
        "Length (cm)",
        "Source x (cm)",
    ]
    return format_table(headers, rows, "  ")


def _stirrups(beam: DetailingBeam) -> list[str]:
    """Tabulate each span's stirrup zones, one row per zone, left to right"""
    rows = [
        [
            f"{stirrups.start_pillar_id}–{stirrups.end_pillar_id}",
            f"{zone.start:.1f}",
            f"{zone.end:.1f}",
            f"φ{stirrups.diameter_mm:g} c/{zone.spacing:.1f}",
        ]
        for stirrups in beam.stirrups
        for zone in stirrups.zones
    ]
    return format_table(["Span", "From (cm)", "To (cm)", "Stirrups"], rows, "  ")
