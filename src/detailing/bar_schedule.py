from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from src.text_table import format_table

if TYPE_CHECKING:
    from src.detailing.detailing_beam import DetailingBeam


@dataclass(frozen=True, kw_only=True)
class ScheduleRow:
    """One mark of a bar schedule

    Attributes:
        kind: "bar", "skin", "clamp" or "stirrup".
        diameter_mm: Bar diameter φ (mm).
        quantity: Number of pieces.
        unit_length: Cut length of one piece (cm).
    """

    mark: str
    kind: str
    diameter_mm: float
    quantity: int
    unit_length: float  # cm

    @property
    def total_length(self) -> float:
        """Return the cut length of all the pieces (cm)"""
        return self.quantity * self.unit_length


def build_schedule(beams: Iterable[DetailingBeam]) -> list[ScheduleRow]:
    """Add up the marked bars, skin bars, clamps and stirrups of some beams, one row per mark

    Items without a mark are left out.

    Returns:
        The rows in mark order (N1, N2, …).
    """
    rows: dict[str, ScheduleRow] = {}
    for beam in beams:
        for row in _beam_rows(beam):
            existing = rows.get(row.mark)
            rows[row.mark] = (
                row
                if existing is None
                else replace(existing, quantity=existing.quantity + row.quantity)
            )
    return sorted(rows.values(), key=lambda row: int(row.mark[1:]))


def _beam_rows(beam: DetailingBeam) -> list[ScheduleRow]:
    """List one row for each marked bar run, skin bar set, clamp set and stirrup set of a beam"""
    rows: list[ScheduleRow] = []
    for bar in beam.bars:
        if bar.mark is not None:
            rows.append(
                ScheduleRow(
                    mark=bar.mark,
                    kind="bar",
                    diameter_mm=bar.diameter_mm,
                    quantity=bar.quantity,
                    unit_length=bar.total_length,
                )
            )
    for skin in beam.skin_bars:
        if skin.mark is not None:
            rows.append(
                ScheduleRow(
                    mark=skin.mark,
                    kind="skin",
                    diameter_mm=skin.diameter_mm,
                    quantity=skin.quantity,
                    unit_length=skin.total_length,
                )
            )
    for clamps in beam.clamps:
        if clamps.mark is not None:
            rows.append(
                ScheduleRow(
                    mark=clamps.mark,
                    kind="clamp",
                    diameter_mm=clamps.diameter_mm,
                    quantity=clamps.quantity,
                    unit_length=clamps.total_length,
                )
            )
    for stirrups in beam.stirrups:
        if stirrups.mark is not None:
            rows.append(
                ScheduleRow(
                    mark=stirrups.mark,
                    kind="stirrup",
                    diameter_mm=stirrups.diameter_mm,
                    quantity=stirrups.quantity,
                    unit_length=stirrups.cut_length,
                )
            )
    return rows


def schedule_table(rows: list[ScheduleRow]) -> list[str]:
    """Tabulate a bar schedule: mark, kind, diameter, quantity, unit and total lengths"""
    if not rows:
        return ["  none"]
    cells = [
        [
            row.mark,
            row.kind,
            f"φ{row.diameter_mm:g}",
            str(row.quantity),
            f"{row.unit_length:.0f}",
            f"{row.total_length:.0f}",
        ]
        for row in rows
    ]
    headers = ["Mark", "Kind", "φ (mm)", "Quantity", "Unit (cm)", "Total (cm)"]
    return format_table(headers, cells, "  ")
