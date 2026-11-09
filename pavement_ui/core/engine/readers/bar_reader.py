"""Read the detailed longitudinal bars of a beam, in mark order."""

import re

from pavement_ui.core.engine.keys import m_from_cm
from pavement_ui.core.results.beam_design import BarEntry
from src.detailing.detailed_bar import BarRole, DetailedBar
from src.detailing.detailing_beam import DetailingBeam


def _mark_key(bar: DetailedBar) -> tuple[int, str, float]:
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
        center_m=m_from_cm(center),
        start_m=m_from_cm(bar.start),
        end_m=m_from_cm(bar.end),
        left_hook_cm=bar.left_hook_length,
        right_hook_cm=bar.right_hook_length,
        total_length_cm=bar.total_length,
    )


def read_bars(detailing: DetailingBeam) -> tuple[BarEntry, ...]:
    """Return every bar run of the detailed beam, sorted by mark and position"""
    return tuple(_entry(bar) for bar in sorted(detailing.bars, key=_mark_key))
