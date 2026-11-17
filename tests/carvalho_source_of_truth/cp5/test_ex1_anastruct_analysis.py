"""Carvalho (2026), p. 319, chapter 5, Example 1 — two-span beam analysed with anaStruct.

C20, CA-50, 18x95 cm section, 16 m long, supported at 0, 8 and 16 m, under a
constant downward load of 40.775 kN/m.

FROZEN: inputs and expected values come from the book's worked example.
Do not change them; see the "Source-of-truth tests" section of AGENTS.md.
"""

import pytest

from src.analysis.anastruct_analysis import AnaStructBeamAnalysis
from src.analysis.model import BeamSupport, DistributedLoad
from src.config import APP_CONFIG
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.structural_elements.rectangular_beam import RectangularBeam
from tests.carvalho_source_of_truth.book_tolerance import assert_book_value

_LENGTH = 1600.0  # cm
_MIDDLE = 800.0  # cm
_JUST_PAST_MIDDLE = 800.01  # cm, reads the shear to the right of the support


@pytest.fixture(autouse=True)
def book_concrete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the concrete of the example (C20)"""
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C20)


@pytest.fixture
def analysis() -> AnaStructBeamAnalysis:
    """Two 8 m spans, pinned at 0, 800 and 1600 cm, 40.775 kN/m downward"""
    beam = RectangularBeam(length=_LENGTH, width=18, height=95, steel=Steel.CA50)
    supports = [BeamSupport(0.0), BeamSupport(_MIDDLE), BeamSupport(_LENGTH)]
    loads = [DistributedLoad(0.0, _LENGTH, 40.775)]
    return AnaStructBeamAnalysis(beam, supports, loads)


class TestCarvalhoCp5Example1:
    """Expected results of Example 1"""

    def test_outer_support_reactions(self, analysis: AnaStructBeamAnalysis) -> None:
        assert_book_value(
            analysis.reaction(0.0), 122.3, "R at x=0 should be 122.3 kN", decimals=1
        )
        assert_book_value(
            analysis.reaction(_LENGTH),
            122.3,
            "R at x=16 m should be 122.3 kN",
            decimals=1,
        )

    def test_middle_support_reaction(self, analysis: AnaStructBeamAnalysis) -> None:
        assert_book_value(
            analysis.reaction(_MIDDLE),
            407.9,
            "R at the middle support should be 407.9 kN",
            decimals=1,
        )

    def test_shear_left_of_middle_support(
        self, analysis: AnaStructBeamAnalysis
    ) -> None:
        assert_book_value(
            analysis.shear_force(_MIDDLE),
            -203.9,
            "V left of the middle support should be -203.9 kN",
            decimals=1,
        )

    def test_shear_right_of_middle_support(
        self, analysis: AnaStructBeamAnalysis
    ) -> None:
        assert_book_value(
            analysis.shear_force(_JUST_PAST_MIDDLE),
            203.9,
            "V right of the middle support should be 203.9 kN",
            decimals=1,
        )

    def test_moment_is_zero_at_the_ends(self, analysis: AnaStructBeamAnalysis) -> None:
        assert_book_value(
            analysis.bending_moment(0.0),
            0.0,
            "M at x=0 should be 0 kN.m",
            decimals=1,
        )
        assert_book_value(
            analysis.bending_moment(_LENGTH),
            0.0,
            "M at x=16 m should be 0 kN.m",
            decimals=1,
        )

    def test_moment_over_middle_support(self, analysis: AnaStructBeamAnalysis) -> None:
        assert_book_value(
            analysis.bending_moment(_MIDDLE),
            -326.2,
            "M over the middle support should be -326.2 kN.m",
            decimals=1,
        )

    def test_max_moment_in_each_span(self, analysis: AnaStructBeamAnalysis) -> None:
        # Ranges stop short of the middle support, whose larger hogging moment
        # would otherwise dominate
        _, first_span = analysis.moment_extreme_in_range(0.0, 600.0)
        _, second_span = analysis.moment_extreme_in_range(1000.0, _LENGTH)
        assert_book_value(
            first_span,
            183.5,
            "Max M in the first span should be 183.5 kN.m",
            decimals=1,
        )
        assert_book_value(
            second_span,
            183.5,
            "Max M in the second span should be 183.5 kN.m",
            decimals=1,
        )
