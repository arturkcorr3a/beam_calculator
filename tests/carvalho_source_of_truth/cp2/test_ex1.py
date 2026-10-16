"""Carvalho, chapter 2, Example 1 — singly reinforced rectangular section, C20.

FROZEN: inputs and expected values come from docs/carvalho-examples/cp2/ex1.md.
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
    """Set the concrete of the example (fck = 20 MPa)"""
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C20)


@pytest.fixture
def calculator() -> RebarCalculator:
    """Calculator for bw = 0.18 m, h = 0.40 m, d = 0.36 m, M = 14.40 kN·m, CA50"""
    beam = RectangularBeam(length=500, width=18, height=40, steel=Steel.CA50)
    return RebarCalculator(
        beam=beam, bending_moment=14.40, bending_moment_position=0, d=36
    )


class TestCarvalhoCp2Example1:
    """Expected results of Example 1"""

    def test_neutral_axis_depth(self, calculator: RebarCalculator) -> None:
        x = calculator.actual_y / APP_CONFIG.pavement_concrete.lambda_c / 100  # m
        assert_book_value(x, 0.033, "x should be 0.033 m", decimals=3)

    def test_x_over_d_within_limit(self, calculator: RebarCalculator) -> None:
        assert calculator.is_singly_reinforced, "section should be singly reinforced"
        assert calculator.actual_y <= calculator.max_y, "x/d should be within limit"

    def test_tensioned_rebar_area(self, calculator: RebarCalculator) -> None:
        assert_book_value(calculator.as1, 1.337, "As should be 1.337 cm²", decimals=3)
