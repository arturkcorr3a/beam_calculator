"""Read the bar schedule and the net quantities of a detailed pavement."""

from pavement_ui.core.results.quantities import (
    BeamQuantity,
    QuantitiesResult,
    ScheduleEntry,
    SteelByDiameter,
)
from src.pavement_elements.pavement import Pavement


def read_quantities(pavement: Pavement) -> QuantitiesResult:
    """Read the pavement's quantities and bar schedule"""
    quantities = pavement.quantities()
    return QuantitiesResult(
        steel=tuple(
            SteelByDiameter(item.diameter_mm, item.length_m, item.mass_kg)
            for item in quantities.steel
        ),
        beams=tuple(
            BeamQuantity(
                beam.beam_id, beam.steel_mass_kg, beam.concrete_m3, beam.formwork_m2
            )
            for beam in quantities.beams
        ),
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
