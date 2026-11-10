"""Read the bar schedule and the net quantities of a detailed pavement or beam."""

from pavement_ui.core.results.quantities import (
    BeamQuantity,
    QuantitiesResult,
    ScheduleEntry,
    SteelByDiameter,
)
from src.detailing.detailing_beam import DetailingBeam
from src.detailing.quantities import BeamQuantities, build_quantities
from src.pavement_elements.pavement import Pavement


def _beam(beam: BeamQuantities) -> BeamQuantity:
    return BeamQuantity(
        beam.beam_id, beam.steel_mass_kg, beam.concrete_m3, beam.formwork_m2
    )


def read_beam_quantity(detailing: DetailingBeam) -> BeamQuantity:
    """Read the net quantities of one detailed beam"""
    return _beam(build_quantities([detailing]).beams[0])


def read_quantities(pavement: Pavement) -> QuantitiesResult:
    """Read the pavement's quantities and bar schedule"""
    quantities = pavement.quantities()
    return QuantitiesResult(
        steel=tuple(
            SteelByDiameter(item.diameter_mm, item.length_m, item.mass_kg)
            for item in quantities.steel
        ),
        beams=tuple(_beam(beam) for beam in quantities.beams),
        schedule=tuple(
            ScheduleEntry(
                row.mark,
                row.kind,
                row.diameter_mm,
                row.quantity,
                row.unit_length,
                row.total_length,
            )
            for row in pavement.bar_schedule()
        ),
        steel_length_m=sum(item.length_m for item in quantities.steel),
        steel_kg=quantities.steel_mass_kg,
        concrete_m3=quantities.concrete_m3,
        formwork_m2=quantities.formwork_m2,
    )
