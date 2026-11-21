"""Read the detailed longitudinal and skin bars of a beam, in mark order."""

import re

from pavement_ui.core.engine.keys import m_from_cm
from pavement_ui.core.results.beam_design import BarEntry
from src.detailing.detailed_bar import BarRole, DetailedBar
from src.detailing.detailed_skin_bars import DetailedSkinBars
from src.detailing.detailing_beam import DetailingBeam


def _mark_key(bar: DetailedBar | DetailedSkinBars) -> tuple[int, str, float]:
    """Sort key: the mark's number (N2 before N10), then the run's start."""
    mark = bar.mark or ""
    digits = re.findall(r"\d+", mark)
    return (int(digits[0]) if digits else 0, mark, bar.start)


def _entry(bar: DetailedBar) -> BarEntry:
    center = (
        bar.source_positions[0] if bar.source_positions else (bar.start + bar.end) / 2
    )
    return BarEntry(
        mark=bar.mark or "",
        quantity=bar.quantity,
        diameter_mm=bar.diameter_mm,
        bottom=bar.is_bottom,
        layer=bar.layer_index + 1,
        construction=bar.role is BarRole.CONSTRUCTION,
        skin=False,
        center_m=m_from_cm(center),
        start_m=m_from_cm(bar.start),
        end_m=m_from_cm(bar.end),
        left_hook_cm=bar.left_hook_length,
        right_hook_cm=bar.right_hook_length,
        total_length_cm=bar.total_length,
    )


def _skin_entry(skin: DetailedSkinBars) -> BarEntry:
    return BarEntry(
        mark=skin.mark or "",
        quantity=skin.quantity,
        diameter_mm=skin.diameter_mm,
        bottom=False,
        layer=0,
        construction=False,
        skin=True,
        center_m=m_from_cm((skin.start + skin.end) / 2),
        start_m=m_from_cm(skin.start),
        end_m=m_from_cm(skin.end),
        left_hook_cm=0.0,
        right_hook_cm=0.0,
        total_length_cm=skin.total_length,
    )


def read_bars(detailing: DetailingBeam) -> tuple[BarEntry, ...]:
    """Return every bar run and skin bar set of the detailed beam, sorted by mark and position"""
    items = sorted([*detailing.bars, *detailing.skin_bars], key=_mark_key)
    return tuple(
        _skin_entry(item) if isinstance(item, DetailedSkinBars) else _entry(item)
        for item in items
    )
