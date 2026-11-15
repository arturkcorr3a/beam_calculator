"""Carvalho, chapter 5, Example 1 — basic anchorage length of a 12.5 mm bar.

FROZEN: inputs and expected values come from the book's worked example
(Carvalho & Figueiredo Filho, 2014).
Do not change them; see the "Source-of-truth tests" section of AGENTS.md.
"""

import pytest

from src.calculators.anchorage_calculator import AnchorageCalculator
from src.config import APP_CONFIG
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.reinforcement.reinforcement import Reinforcement
from src.structural_elements.rebar import Rebar
from src.structural_elements.rectangular_beam import RectangularBeam
from tests.carvalho_source_of_truth.book_tolerance import assert_book_value


@pytest.fixture(autouse=True)
def book_concrete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the concrete of the example (C20)"""
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C20)


@pytest.fixture
def calculator() -> AnchorageCalculator:
    """Calculator for one 12.5 mm CA-50 bar in a good-adherence zone

    The book gives no beam; a 40 cm high one keeps the bar in the good zone.
    """
    beam = RectangularBeam(length=500, width=18, height=40, steel=Steel.CA50)
    reinforcement = Reinforcement(
        beam, is_bottom_reinforcement=True, center_position=250
    )
    layer = reinforcement.chosen_bars[0]
    layer.bars = [Rebar(12.5, Steel.CA50)]
    layer.y_centroid_position = 4.0  # cm from the bottom face
    reinforcement.required_area = reinforcement.area
    calculator = AnchorageCalculator(
        moment_shift=0, steel=Steel.CA50, layer_index=0, reinforcement=reinforcement
    )
    calculator.left = True
    return calculator


class TestCarvalhoCp5Example1:
    """Expected results of Example 1"""

    def test_eta_1(self) -> None:
        assert_book_value(
            Steel.CA50.bond_coefficient, 2.25, "eta_1 should be 2.25", decimals=2
        )

    def test_eta_2(self, calculator: AnchorageCalculator) -> None:
        assert_book_value(
            calculator.adherence_coefficient, 1.00, "eta_2 should be 1.00", decimals=2
        )

    def test_eta_3(self, calculator: AnchorageCalculator) -> None:
        assert_book_value(
            calculator.diameter_coefficient, 1.00, "eta_3 should be 1.00", decimals=2
        )

    def test_fctd(self) -> None:
        fctd = Concrete.C20.fctd * 10  # MPa
        assert_book_value(fctd, 1.105, "f_ctd should be 1.105 MPa", decimals=3)

    def test_fbd(self, calculator: AnchorageCalculator) -> None:
        fbd = calculator.design_bond_strength * 10  # MPa
        assert_book_value(fbd, 2.486, "f_bd should be 2.486 MPa", decimals=3)

    def test_basic_anchorage_length(self, calculator: AnchorageCalculator) -> None:
        l_b = calculator.basic_anchorage_length * 10  # mm
        assert_book_value(l_b, 546.54, "l_b should be 546.54 mm", decimals=2)
