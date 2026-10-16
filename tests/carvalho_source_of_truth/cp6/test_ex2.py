"""Carvalho, chapter 6, Example 2 — shear design with Model I, C30.

FROZEN: inputs and expected values come from docs/carvalho-examples/cp6/ex2.md.
Do not change them; see the "Source-of-truth tests" section of AGENTS.md.
"""

import pytest

from src.calculators.stirrup_calculator import StirrupCalculator
from src.config import APP_CONFIG
from src.loading.forces import design_effort_elu
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.structural_elements.rectangular_beam import RectangularBeam
from tests.carvalho_source_of_truth.book_tolerance import assert_book_value


@pytest.fixture(autouse=True)
def book_concrete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the concrete of the example (C30)"""
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C30)


@pytest.fixture
def calculator() -> StirrupCalculator:
    """Calculator for V = 203.9 kN, b_w = 18 cm, d = 86 cm, CA-50

    The book gives only b_w and d; the length and height are placeholders.
    """
    beam = RectangularBeam(length=500, width=18, height=95, steel=Steel.CA50)
    calculator = StirrupCalculator(beam, design_effort_elu(203.9))
    calculator.effective_depth = 86
    return calculator


class TestCarvalhoCp6Example2:
    """Expected results of Example 2"""

    def test_design_shear_force(self, calculator: StirrupCalculator) -> None:
        assert_book_value(
            calculator.design_shear_force, 285.5, "V_sd should be 285.5 kN", decimals=1
        )

    def test_alpha_v2(self) -> None:
        # The book prints 0.92 (the C20 value); 1 - 30/250 = 0.88 is the
        # corrected value for C30
        assert_book_value(
            Concrete.C30.alpha_v2, 0.88, "alpha_v2 should be 0.88", decimals=2
        )

    def test_compressed_strut_resistance(self, calculator: StirrupCalculator) -> None:
        # The book prints 824.0 kN, using alpha_v2 = 0.92; 788.15 kN is the
        # corrected value with alpha_v2 = 0.88
        assert_book_value(
            calculator.compressed_strut_resistance,
            788.15,
            "V_Rd2 should be 788.15 kN",
            decimals=2,
        )

    def test_compressed_strut_verification(self, calculator: StirrupCalculator) -> None:
        calculator.verify_compressed_strut_resistance()  # raises when V_sd > V_Rd2

    def test_concrete_contribution(self, calculator: StirrupCalculator) -> None:
        assert_book_value(
            calculator.concrete_contribution,
            134.5,
            "V_c should be 134.5 kN",
            decimals=1,
        )

    def test_fctd(self) -> None:
        fctd = Concrete.C30.fctd * 1e4  # kN/m²
        assert_book_value(fctd, 1448, "f_ctd should be 1448 kN/m²", decimals=0)

    def test_required_stirrup_contribution(self, calculator: StirrupCalculator) -> None:
        assert_book_value(
            calculator.required_contribution,
            151.0,
            "V_sw should be 151.0 kN",
            decimals=1,
        )
