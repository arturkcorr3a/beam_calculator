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
        kind: "bar", "clamp" or "stirrup".
        diameter_mm: Bar diameter φ (mm).
        quantity: Number of pieces, None for stirrups (not counted yet).
        unit_length: Cut length of one piece (cm), None for stirrups (not calculated yet).
    """

    mark: str
    kind: str
    diameter_mm: float
    quantity: int | None
    unit_length: float | None  # cm

    @property
    def total_length(self) -> float | None:
        """Return the cut length of all the pieces (cm), None for stirrups"""
        if self.quantity is None or self.unit_length is None:
            return None
        return self.quantity * self.unit_length


def build_schedule(beams: Iterable[DetailingBeam]) -> list[ScheduleRow]:
    """Add up the marked bars, clamps and stirrups of some beams, one row per mark

    Items without a mark are left out.

    Returns:
        The rows in mark order (N1, N2, …).
    """
    rows: dict[str, ScheduleRow] = {}
    for beam in beams:
        for row in _beam_rows(beam):
            existing = rows.get(row.mark)
            if existing is None or existing.quantity is None or row.quantity is None:
                rows[row.mark] = row
            else:
                rows[row.mark] = replace(
                    existing, quantity=existing.quantity + row.quantity
                )
    return sorted(rows.values(), key=lambda row: int(row.mark[1:]))


def _beam_rows(beam: DetailingBeam) -> list[ScheduleRow]:
    """List one row for each marked bar run, clamp set and stirrup set of a beam"""
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
                    quantity=None,
                    unit_length=None,
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
            "—" if row.quantity is None else str(row.quantity),
            _length(row.unit_length),
            _length(row.total_length),
        ]
        for row in rows
    ]
    headers = ["Mark", "Kind", "φ (mm)", "Quantity", "Unit (cm)", "Total (cm)"]
    return format_table(headers, cells, "  ")


def _length(length: float | None) -> str:
    """Show a length in whole centimeters, or a dash when it is not known"""
    return "—" if length is None else f"{length:.0f}"
