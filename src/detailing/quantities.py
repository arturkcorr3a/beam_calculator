from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.detailing.bar_schedule import build_schedule
from src.text_table import format_table

if TYPE_CHECKING:
    from src.detailing.detailing_beam import DetailingBeam

_CM_PER_M = 100.0


@dataclass(frozen=True, kw_only=True)
class SteelQuantity:
    """The net steel of one diameter

    Attributes:
        diameter_mm: Bar diameter φ (mm).
        length_m: Total cut length (m).
        mass_kg: Total nominal mass (kg).
    """

    diameter_mm: float
    length_m: float
    mass_kg: float


@dataclass(frozen=True, kw_only=True)
class BeamQuantities:
    """The net steel, concrete and formwork of one beam

    Attributes:
        steel: Steel by diameter, thinnest first.
        concrete_m3: Concrete volume between the pillars' faces (m³).
        formwork_m2: Formwork area of the bottom and visible sides (m²).
    """

    beam_id: str
    steel: tuple[SteelQuantity, ...]
    concrete_m3: float
    formwork_m2: float

    @property
    def steel_mass_kg(self) -> float:
        """Return the total steel mass (kg)"""
        return sum(item.mass_kg for item in self.steel)


@dataclass(frozen=True, kw_only=True)
class PavementQuantities:
    """The net quantities of a pavement's beams, without its slabs and pillars

    Attributes:
        beams: Quantities of each beam, in pavement order.
        steel: Steel of all the beams by diameter, thinnest first.
    """

    beams: tuple[BeamQuantities, ...]
    steel: tuple[SteelQuantity, ...]

    @property
    def steel_mass_kg(self) -> float:
        """Return the total steel mass (kg)"""
        return sum(item.mass_kg for item in self.steel)

    @property
    def concrete_m3(self) -> float:
        """Return the total concrete volume (m³)"""
        return sum(beam.concrete_m3 for beam in self.beams)

    @property
    def formwork_m2(self) -> float:
        """Return the total formwork area (m²)"""
        return sum(beam.formwork_m2 for beam in self.beams)


def build_quantities(beams: Iterable[DetailingBeam]) -> PavementQuantities:
    """Measure the net steel, concrete and formwork of some detailed beams

    The steel comes from the bar schedule, so only marked items count: bars, clamps and stirrups. There is no allowance for waste.

    References:
        ABNT NBR 7480:2024 — Section 4.4
    """
    quantities = tuple(_beam_quantities(beam) for beam in beams)
    return PavementQuantities(
        beams=quantities,
        steel=_add_up(item for beam in quantities for item in beam.steel),
    )


def _beam_quantities(beam: DetailingBeam) -> BeamQuantities:
    """Measure one beam

    The concrete and the formwork run between the pillars' faces, so the pillar nodes are left to the pillars and two beams never overlap. The formwork covers the bottom and each side down from the slab on that side.
    """
    steel = _add_up(
        SteelQuantity(
            diameter_mm=row.diameter_mm,
            length_m=row.total_length / _CM_PER_M,
            mass_kg=row.total_length
            / _CM_PER_M
            * beam.steel.linear_mass(row.diameter_mm),
        )
        for row in build_schedule([beam])
    )
    section_area = beam.width * beam.height / _CM_PER_M**2  # m²
    length = sum(span.length for span in beam.clear_spans) / _CM_PER_M  # m
    formwork = sum(
        (beam.width + sum(span.side_heights)) * span.length for span in beam.clear_spans
    )  # cm²
    return BeamQuantities(
        beam_id=beam.beam_id,
        steel=steel,
        concrete_m3=section_area * length,
        formwork_m2=formwork / _CM_PER_M**2,
    )


def _add_up(items: Iterable[SteelQuantity]) -> tuple[SteelQuantity, ...]:
    """Add up steel quantities by diameter, thinnest first"""
    lengths: dict[float, float] = {}
    masses: dict[float, float] = {}
    for item in items:
        lengths[item.diameter_mm] = lengths.get(item.diameter_mm, 0.0) + item.length_m
        masses[item.diameter_mm] = masses.get(item.diameter_mm, 0.0) + item.mass_kg
    return tuple(
        SteelQuantity(
            diameter_mm=diameter_mm,
            length_m=lengths[diameter_mm],
            mass_kg=masses[diameter_mm],
        )
        for diameter_mm in sorted(lengths)
    )


def quantities_table(quantities: PavementQuantities) -> list[str]:
    """Tabulate the steel by diameter and the quantities of each beam, with their totals"""
    steel_rows = [
        [f"φ{item.diameter_mm:g}", f"{item.length_m:.2f}", f"{item.mass_kg:.1f}"]
        for item in quantities.steel
    ]
    total_length = sum(item.length_m for item in quantities.steel)
    steel_rows.append(
        ["Total", f"{total_length:.2f}", f"{quantities.steel_mass_kg:.1f}"]
    )
    beam_rows = [
        [
            beam.beam_id,
            f"{beam.steel_mass_kg:.1f}",
            f"{beam.concrete_m3:.2f}",
            f"{beam.formwork_m2:.2f}",
        ]
        for beam in quantities.beams
    ]
    beam_rows.append(
        [
            "Total",
            f"{quantities.steel_mass_kg:.1f}",
            f"{quantities.concrete_m3:.2f}",
            f"{quantities.formwork_m2:.2f}",
        ]
    )
    return [
        *format_table(["φ (mm)", "Length (m)", "Mass (kg)"], steel_rows, "  "),
        "",
        *format_table(
            ["Beam", "Steel (kg)", "Concrete (m³)", "Formwork (m²)"],
            beam_rows,
            "  ",
        ),
    ]
