"""Read models of the beams' bar schedule and net quantities."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SteelByDiameter:
    """Net steel of one diameter

    Attributes:
        diameter_mm: Bar diameter (mm).
        length_m: Total cut length (m).
        mass_kg: Total nominal mass (kg).
    """

    diameter_mm: float
    length_m: float
    mass_kg: float


@dataclass(frozen=True, slots=True)
class BeamQuantity:
    """Net quantities of one beam

    Attributes:
        steel_kg: Steel mass (kg).
        concrete_m3: Concrete volume (m³).
        formwork_m2: Formwork area (m²).
    """

    beam_id: str
    steel_kg: float
    concrete_m3: float
    formwork_m2: float


@dataclass(frozen=True, slots=True)
class ScheduleEntry:
    """One mark of the bar schedule

    Attributes:
        kind_key: "bar", "clamp" or "stirrup".
        diameter_mm: Bar diameter (mm).
        unit_length_cm: Cut length of one piece (cm).
        total_length_cm: Cut length of all the pieces (cm).
    """

    mark: str
    kind_key: str
    diameter_mm: float
    quantity: int
    unit_length_cm: float
    total_length_cm: float


@dataclass(frozen=True, slots=True)
class QuantitiesResult:
    """Net quantities of the pavement's beams, without slabs and pillars

    Attributes:
        steel: Steel by diameter, thinnest first.
        beams: Quantities of each beam, in registration order.
        schedule: Bar schedule, in mark order.
        steel_length_m: Total cut length (m).
        steel_kg: Total steel mass (kg).
        concrete_m3: Total concrete volume (m³).
        formwork_m2: Total formwork area (m²).
    """

    steel: tuple[SteelByDiameter, ...]
    beams: tuple[BeamQuantity, ...]
    schedule: tuple[ScheduleEntry, ...]
    steel_length_m: float
    steel_kg: float
    concrete_m3: float
    formwork_m2: float
