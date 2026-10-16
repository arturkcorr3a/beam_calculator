"""Carvalho, chapter 4, Example 1 — longitudinal steel area of beam V101.

FROZEN: inputs and expected values come from docs/carvalho-examples/cp4/ex1.md.
Do not change them; see the "Source-of-truth tests" section of AGENTS.md.
"""

import pytest

from src.calculators.rebar_calculator import RebarCalculator
from src.config import APP_CONFIG
from src.config_options import ExposureClass
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.reinforcement.rebar_chooser import RebarChooser
from src.structural_elements.rebar import Rebar
from src.structural_elements.rectangular_beam import RectangularBeam
from tests.carvalho_source_of_truth.book_tolerance import assert_book_value

BAR_DIAMETER = 12.5  # mm, phi 1/2"


@pytest.fixture(autouse=True)
def book_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the materials and environment of the example (C20, CAA I)"""
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C20)
    monkeypatch.setattr(APP_CONFIG, "exposure_class", ExposureClass.WEAK)


@pytest.fixture
def beam() -> RectangularBeam:
    """V101 section, 18 x 95 cm, CA50, two 8.00 m spans"""
    return RectangularBeam(length=1600, width=18, height=95, steel=Steel.CA50)


@pytest.fixture
def support_calculator(beam: RectangularBeam) -> RebarCalculator:
    """Calculator for the central support section, M = -326.20 kN·m, d = 85 cm"""
    return RebarCalculator(
        beam=beam, bending_moment=-326.20, bending_moment_position=800, d=85
    )


@pytest.fixture
def span_calculator(beam: RectangularBeam) -> RebarCalculator:
    """Calculator for the span section, M = 183.50 kN·m, d = 85 cm"""
    return RebarCalculator(
        beam=beam, bending_moment=183.50, bending_moment_position=300, d=85
    )


def _bar_count(required_area: float) -> int:
    """Number of phi 12.5 mm bars the engine chooses for an area (cm²)"""
    chooser = RebarChooser(Steel.CA50, required_area)
    return len(chooser.get_best_solution_for_combo((BAR_DIAMETER,)))


class TestSupportSection:
    """Item g) — negative moment at the central support"""

    def test_singly_reinforced(self, support_calculator: RebarCalculator) -> None:
        assert support_calculator.is_singly_reinforced, (
            "x/d should be within 0.45 (fs = fyd)"
        )

    def test_required_area(self, support_calculator: RebarCalculator) -> None:
        assert_book_value(
            support_calculator.as1, 14.97, "As should be 14.97 cm²", decimals=2
        )

    @pytest.mark.xfail(strict=True, reason="book rounds 12.20 bars down to 12")
    def test_bar_count(self) -> None:
        assert _bar_count(14.97) == 12, "support should use 12 bars of 12.5 mm"


class TestSpanSection:
    """Item g) — positive moment in the span"""

    def test_singly_reinforced(self, span_calculator: RebarCalculator) -> None:
        assert span_calculator.is_singly_reinforced, (
            "x/d should be within 0.45 (fs = fyd)"
        )

    def test_required_area(self, span_calculator: RebarCalculator) -> None:
        assert_book_value(
            span_calculator.as1, 7.64, "As should be 7.64 cm²", decimals=2
        )

    @pytest.mark.xfail(strict=True, reason="book rounds 6.22 bars down to 6")
    def test_bar_count(self) -> None:
        assert _bar_count(7.64) == 6, "span should use 6 bars of 12.5 mm"


class TestBarArea:
    """Item g) — area of one phi 12.5 mm bar"""

    def test_bar_area(self) -> None:
        area = Rebar(BAR_DIAMETER, Steel.CA50).area_cm2
        assert_book_value(area, 1.227, "bar area should be 1.227 cm²", decimals=3)


class TestAreaLimits:
    """Item h) — minimum and maximum longitudinal steel"""

    def test_minimum_area(self, span_calculator: RebarCalculator) -> None:
        assert_book_value(
            span_calculator.min_tension_rebar_area,
            2.56,
            "As,min should be 2.56 cm²",
            decimals=2,
        )

    def test_maximum_area(self, span_calculator: RebarCalculator) -> None:
        assert_book_value(
            span_calculator.max_rebar_area,
            68.40,
            "As,max should be 68.40 cm²",
            decimals=2,
        )
