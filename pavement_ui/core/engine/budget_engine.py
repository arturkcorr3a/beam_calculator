"""SinapiBudgetCalculator: price a design's quantities with the engine's budget calculator."""

from datetime import datetime

from pavement_ui.core.engine.rule_errors import engine_rules
from pavement_ui.core.results.budget import BudgetResult, SteelBudgetLine
from pavement_ui.core.results.materials import MaterialsInfo
from pavement_ui.core.results.quantities import QuantitiesResult
from src.calculators.budget_calculator import calculate_budget
from src.data.sinapi_2026_10.steel_prices.data import STEEL_PRICES
from src.detailing.quantities import SteelQuantity
from src.properties.steel import Steel


class SinapiBudgetCalculator:
    """Steel with SINAPI unit prices, concrete with the user's price"""

    def budget(
        self,
        quantities: QuantitiesResult,
        materials: MaterialsInfo,
        concrete_price_per_m3: float,
        priced_at: datetime,
    ) -> BudgetResult:
        with engine_rules():
            budget = calculate_budget(
                (
                    SteelQuantity(
                        diameter_mm=item.diameter_mm,
                        length_m=item.length_m,
                        mass_kg=item.mass_kg,
                    )
                    for item in quantities.steel
                ),
                quantities.concrete_m3,
                concrete_price_per_m3,
                Steel[materials.steel],
            )
        return BudgetResult(
            steel_grade=materials.steel,
            steel=tuple(
                SteelBudgetLine(
                    item.diameter_mm,
                    item.mass_kg,
                    item.sinapi_code,
                    item.description,
                    item.price_per_kg,
                    item.cost,
                )
                for item in budget.steel
            ),
            steel_cost=budget.steel_cost,
            steel_reference=STEEL_PRICES.reference,
            concrete_class=materials.concrete,
            concrete_m3=budget.concrete_m3,
            concrete_price_per_m3=budget.concrete_price_per_m3,
            concrete_cost=budget.concrete_cost,
            priced_at=priced_at,
            total=budget.total,
        )
