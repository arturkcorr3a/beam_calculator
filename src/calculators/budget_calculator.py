"""Price the net steel and concrete of a structure with SINAPI unit prices."""

from collections.abc import Iterable
from dataclasses import dataclass

from src.data.sinapi_2026_10.steel_prices.data import STEEL_PRICES
from src.detailing.quantities import SteelQuantity
from src.errors import InputError
from src.logger import log_operation, log_property
from src.properties.steel import Steel


@dataclass(frozen=True, kw_only=True)
class SteelCost:
    """The cost of the steel of one diameter

    Attributes:
        diameter_mm: Bar diameter φ (mm).
        mass_kg: Net mass (kg).
        sinapi_code: SINAPI material code of the unit price.
        description: SINAPI description of that material, verbatim.
        price_per_kg: Unit price (R$/kg).
    """

    diameter_mm: float
    mass_kg: float
    sinapi_code: int
    description: str
    price_per_kg: float

    @property
    def cost(self) -> float:
        """Return the cost (R$)"""
        return self.mass_kg * self.price_per_kg


@dataclass(frozen=True, kw_only=True)
class Budget:
    """The cost of the net steel and concrete, without waste

    Attributes:
        steel: Steel cost by diameter, in the order given.
        concrete_m3: Concrete volume (m³).
        concrete_price_per_m3: Concrete unit price (R$/m³).
    """

    steel: tuple[SteelCost, ...]
    concrete_m3: float
    concrete_price_per_m3: float

    @property
    def steel_cost(self) -> float:
        """Return the total steel cost (R$)"""
        return sum(item.cost for item in self.steel)

    @property
    def concrete_cost(self) -> float:
        """Return the concrete cost (R$)"""
        return self.concrete_m3 * self.concrete_price_per_m3

    @property
    def total(self) -> float:
        """Return the total cost (R$)"""
        return self.steel_cost + self.concrete_cost


def calculate_budget(
    steel: Iterable[SteelQuantity],
    concrete_m3: float,
    concrete_price_per_m3: float,
    grade: Steel,
) -> Budget:
    """Price the net steel by diameter and the concrete volume, without waste

    The steel takes SINAPI unit prices: cut and bent bars when SINAPI has them, else straight rebar. The concrete price varies too much to tabulate, so it is given.

    Args:
        steel: Net steel by diameter, as measured by ``build_quantities``.
        concrete_m3: Concrete volume (m³).
        concrete_price_per_m3: Concrete unit price (R$/m³).
        grade: Steel grade of all the bars.

    Raises:
        InputError: If the volume or the concrete price is negative.
        SteelPriceNotFoundError: If SINAPI has no price for a diameter.

    References:
        SINAPI — Insumos, família 43055, 10/2026, média Brasil
    """
    if concrete_m3 < 0:
        raise InputError(f"Concrete volume must not be negative: {concrete_m3} m³.")
    if concrete_price_per_m3 < 0:
        raise InputError(
            f"Concrete price must not be negative: R$ {concrete_price_per_m3}/m³."
        )
    costs: list[SteelCost] = []
    for item in steel:
        price = STEEL_PRICES.price_for(grade, item.diameter_mm)
        costs.append(
            SteelCost(
                diameter_mm=item.diameter_mm,
                mass_kg=item.mass_kg,
                sinapi_code=price.code,
                description=price.description,
                price_per_kg=price.price_per_kg,
            )
        )
    budget = Budget(
        steel=tuple(costs),
        concrete_m3=concrete_m3,
        concrete_price_per_m3=concrete_price_per_m3,
    )
    log_property(f"Steel: R$ {budget.steel_cost:.2f}")
    log_property(
        f"Concrete: {concrete_m3:.2f} m³ × R$ {concrete_price_per_m3:.2f}/m³ = R$ {budget.concrete_cost:.2f}"
    )
    log_operation(f"Budget total (no waste): R$ {budget.total:.2f}")
    return budget
