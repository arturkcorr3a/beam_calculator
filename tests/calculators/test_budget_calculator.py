"""Tests for src/calculators/budget_calculator.py.

CA-50 φ10 costs R$ 7.90/kg (SINAPI 43058, cut and bent) and φ6.3 costs R$ 9.31/kg (SINAPI 34449).
"""

import pytest

from src.calculators.budget_calculator import calculate_budget
from src.detailing.quantities import SteelQuantity
from src.properties.steel import Steel
from tests.helpers import assert_approx


def _steel(diameter_mm: float, mass_kg: float) -> SteelQuantity:
    """Build a steel quantity; the length plays no part in the price"""
    return SteelQuantity(diameter_mm=diameter_mm, length_m=0.0, mass_kg=mass_kg)


class TestCalculateBudget:
    """Steel by SINAPI unit price plus concrete by the given price, without waste."""

    def test_total(self) -> None:
        budget = calculate_budget(
            [_steel(6.3, 5.0), _steel(10.0, 10.0)], 0.63, 500.0, Steel.CA50
        )
        assert_approx(budget.steel_cost, 125.55, "5 × 9.31 + 10 × 7.90 R$")
        assert_approx(budget.concrete_cost, 315.00, "0.63 × 500 R$")
        assert_approx(budget.total, 440.55, "125.55 + 315.00 R$")

    def test_steel_cost_by_diameter(self) -> None:
        budget = calculate_budget([_steel(6.3, 5.0)], 0.0, 0.0, Steel.CA50)
        (item,) = budget.steel
        assert item.sinapi_code == 34449, "CA-50 φ6.3 comes cut and bent"
        assert item.description == "ACO CA-50, 6,3 MM, DOBRADO E CORTADO", (
            "the SINAPI description, verbatim"
        )
        assert item.price_per_kg == 9.31, "SINAPI 34449 costs R$ 9.31/kg"
        assert_approx(item.cost, 46.55, "5 × 9.31 R$")

    def test_without_steel(self) -> None:
        budget = calculate_budget([], 2.0, 450.0, Steel.CA50)
        assert budget.steel == (), "no steel, no steel costs"
        assert_approx(budget.total, 900.0, "2 × 450 R$")

    def test_unpriced_diameter_raises(self) -> None:
        with pytest.raises(ValueError, match="No SINAPI price"):
            calculate_budget([_steel(22.0, 1.0)], 0.0, 0.0, Steel.CA50)

    @pytest.mark.parametrize(
        ("concrete_m3", "concrete_price_per_m3"), [(-0.1, 500.0), (1.0, -1.0)]
    )
    def test_negative_concrete_raises(
        self, concrete_m3: float, concrete_price_per_m3: float
    ) -> None:
        with pytest.raises(ValueError, match="must not be negative"):
            calculate_budget([], concrete_m3, concrete_price_per_m3, Steel.CA50)
