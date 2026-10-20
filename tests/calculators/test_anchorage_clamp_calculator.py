"""Unit tests for src/calculators/anchorage_clamp_calculator.py — AnchorageClampCalculator."""

import pytest

from src.calculators.anchorage_clamp_calculator import (
    AnchorageClampCalculator,
    AnchorageClampCalculatorLabel,
)
from src.config import APP_CONFIG
from src.properties.steel import Steel
from tests.helpers import assert_approx


@pytest.fixture
def calculator(monkeypatch: pytest.MonkeyPatch) -> AnchorageClampCalculator:
    """Build a calculator with CA50 steel, f_bd = 0.25 kN/cm² and 20 cm available"""
    monkeypatch.setattr(APP_CONFIG, "pavement_steel", Steel.CA50)
    return AnchorageClampCalculator(
        moment_shift=30.0,
        effective_depth=40.0,
        design_shear=100.0,
        label_info=AnchorageClampCalculatorLabel(beam_label="V1", is_left=True),
        available_length=20.0,
        necessary_length=50.0,
        design_bond_strength=0.25,
        stirrup_inner_width=15.0,
    )


class TestRequiredClampLength:
    def test_converts_diameter_from_mm_to_cm(
        self, calculator: AnchorageClampCalculator
    ) -> None:
        """Compute l_c = (1.25 / 4) · (50 / 1.15) / 0.25 + 20 for a 12.5 mm clamp"""
        length = calculator._calculate_required_clamp_length(12.5)  # pyright: ignore[reportPrivateUsage]
        assert_approx(length, 74.34783, "l_c for a 12.5 mm clamp (cm)")
