"""Carvalho, chapter 2, Example 2 — Example 1 with C90 concrete.

FROZEN: inputs and expected values come from the book's worked example
(Carvalho & Figueiredo Filho, 2014).
Do not change them; see the "Source-of-truth tests" section of AGENTS.md.
"""

import pytest

from src.calculators.rebar_calculator import RebarCalculator
from src.config import APP_CONFIG
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.structural_elements.rectangular_beam import RectangularBeam
from tests.carvalho_source_of_truth.book_tolerance import assert_book_value


@pytest.fixture(autouse=True)
def book_concrete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the concrete of the example (fck = 90 MPa)"""
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C90)


@pytest.fixture
def calculator() -> RebarCalculator:
    """Calculator for bw = 0.18 m, h = 0.40 m, d = 0.36 m, M = 14.40 kN·m, CA50"""
    beam = RectangularBeam(length=500, width=18, height=40, steel=Steel.CA50)
    return RebarCalculator(
        beam=beam, bending_moment=14.40, bending_moment_position=0, d=36
    )


class TestCarvalhoCp2Example2:
    """Expected results of Example 2"""

    def test_lambda_c(self) -> None:
        assert_book_value(
            Concrete.C90.lambda_c, 0.7, "lambda_c should be 0.7", decimals=1
        )

    def test_alpha_c(self) -> None:
        assert_book_value(
            Concrete.C90.alpha_c, 0.68, "alpha_c should be 0.68", decimals=2
        )

    def test_eta_c(self) -> None:
        assert_book_value(
            Concrete.C90.eta_c, 0.763, "eta_c should be 0.763", decimals=3
        )

    def test_neutral_axis_depth(self, calculator: RebarCalculator) -> None:
        x = calculator.actual_y / APP_CONFIG.pavement_concrete.lambda_c / 100  # m
        assert_book_value(x, 0.0135, "x should be 0.0135 m", decimals=4)

    def test_x_over_d_within_limit(self, calculator: RebarCalculator) -> None:
        assert calculator.is_singly_reinforced, "section should be singly reinforced"
        assert calculator.actual_y <= calculator.max_y, "x/d should be within limit"

    def test_tensioned_rebar_area(self, calculator: RebarCalculator) -> None:
        assert_book_value(calculator.as1, 1.30, "As should be 1.30 cm²", decimals=2)
