"""Carvalho, chapter 2, Example 7 — doubly reinforced rectangular section, C20.

FROZEN: inputs and expected values come from docs/carvalho-examples/cp2/ex7.md.
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
    """Calculator for bw = 0.18 m, h = 0.40 m, d = 0.36 m, d' = 0.04 m, M = 80 kN·m"""
    beam = RectangularBeam(length=500, width=18, height=40, steel=Steel.CA50)
    return RebarCalculator(
        beam=beam,
        bending_moment=80.00,
        bending_moment_position=0,
        d=36,
        d_compressed=4,
    )


class TestCarvalhoCp2Example7:
    """Expected results of Example 7"""

    def test_limit_moment(self, calculator: RebarCalculator) -> None:
        m_lim = calculator.max_bending_moment / 100  # kN·m
        assert_book_value(m_lim, 83.61, "M_lim should be 83.61 kN·m", decimals=2)

    def test_delta_moment(self, calculator: RebarCalculator) -> None:
        m_delta = calculator.calculate_delta_bending_moment() / 100  # kN·m
        assert_book_value(m_delta, 28.39, "M_delta should be 28.39 kN·m", decimals=2)

    def test_tensioned_rebar_area(self, calculator: RebarCalculator) -> None:
        assert_book_value(
            calculator.tensioned_rebar_area, 8.55, "As1 should be 8.55 cm²", decimals=2
        )

    def test_compressed_rebar_strain(self, calculator: RebarCalculator) -> None:
        assert_book_value(
            calculator.calculate_epsilon_s2(),
            0.0026,
            "epsilon'_s should be 0.0026",
            decimals=4,
        )

    # ASK I am correcting it, but the book is not.
    @pytest.mark.xfail(
        strict=True,
        reason="engine subtracts concrete stress from sigma'_s "
        "(corrected_sigma_s2); book uses sigma'_s = fyd",
    )
    def test_compressed_rebar_area(self, calculator: RebarCalculator) -> None:
        assert_book_value(
            calculator.compressed_rebar_area, 2.04, "A's should be 2.04 cm²", decimals=2
        )
