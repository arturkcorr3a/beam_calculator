"""Read models of the beams' material budget."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SteelBudgetLine:
    """Cost of the steel of one diameter

    Attributes:
        diameter_mm: Bar diameter (mm).
        mass_kg: Net mass (kg).
        sinapi_code: SINAPI material code of the unit price.
        description: SINAPI description of that material, verbatim.
        price_per_kg: Unit price (R$/kg).
        cost: Cost (R$).
    """

    diameter_mm: float
    mass_kg: float
    sinapi_code: int
    description: str
    price_per_kg: float
    cost: float


@dataclass(frozen=True, slots=True)
class BudgetResult:
    """Net cost of the beams' steel and concrete, without waste

    Attributes:
        steel_grade: Steel key, such as "CA50".
        steel: Steel cost by diameter, thinnest first.
        steel_cost: Total steel cost (R$).
        steel_reference: Source and date of the steel prices.
        concrete_class: Concrete class key, such as "C30".
        concrete_m3: Concrete volume (m³).
        concrete_price_per_m3: Concrete unit price given by the user (R$/m³).
        concrete_cost: Concrete cost (R$).
        priced_at: When the user gave the concrete price.
        total: Total cost (R$).
    """

    steel_grade: str
    steel: tuple[SteelBudgetLine, ...]
    steel_cost: float
    steel_reference: str
    concrete_class: str
    concrete_m3: float
    concrete_price_per_m3: float
    concrete_cost: float
    priced_at: datetime
    total: float
