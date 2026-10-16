"""Carvalho, chapter 4, Example 1 — structural model of beam V101.

FROZEN: inputs and expected values come from docs/carvalho-examples/cp4/ex1.md.
Do not change them; see the "Source-of-truth tests" section of AGENTS.md.
"""

import pytest

from src.analysis.beam_analysis import BeamAnalysis
from src.analysis.model import BeamSupport, DistributedLoad
from src.analysis.solver import analyse_beam
from src.config import APP_CONFIG
from src.config_options import ExposureClass
from src.loading.linear_loads import LinearLoads
from src.pavement_elements.geometry_utils import effective_span
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.structural_elements.rectangular_beam import RectangularBeam
from tests.carvalho_source_of_truth.book_tolerance import assert_book_value

CENTRAL_SUPPORT = 800  # cm
SIDE_OFFSET = 1e-3  # cm, to read the shear just beside a support
FIRST_SPAN_SEGMENT = 0  # moment segments: first span, central support, second span


@pytest.fixture(autouse=True)
def book_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the materials and environment of the example (C20, CAA I)"""
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C20)
    monkeypatch.setattr(APP_CONFIG, "exposure_class", ExposureClass.WEAK)


def _two_span_analysis(load: float) -> BeamAnalysis:
    """Solve the two 8.00 m spans of V101 under a uniform load (kN/m)"""
    beam = RectangularBeam(length=1600, width=18, height=95, steel=Steel.CA50)
    supports = [BeamSupport(0), BeamSupport(CENTRAL_SUPPORT), BeamSupport(1600)]
    return analyse_beam(beam, supports, [DistributedLoad(0, 1600, load)])


@pytest.fixture
def slab_only_analysis() -> BeamAnalysis:
    """Analysis of figure 4.15: slab reaction only, 36.50 kN/m"""
    return _two_span_analysis(36.50)


@pytest.fixture
def final_analysis() -> BeamAnalysis:
    """Analysis of figure 4.16: slab reaction and own weight, 40.775 kN/m"""
    return _two_span_analysis(40.775)


class TestEffectiveSpan:
    """Item a) — effective span with h = 70 cm and t1 = t2 = 40 cm"""

    def test_effective_span(self) -> None:
        clear_span = 760  # cm
        axis_distance = clear_span + 40 / 2 + 40 / 2  # cm
        l_ef = effective_span(axis_distance, 40, 40, 70)
        assert_book_value(l_ef, 800, "l_ef should be 800 cm", decimals=0)


class TestCovering:
    """Statement — CAA I, cover 2.5 cm"""

    def test_nominal_covering(self) -> None:
        assert_book_value(
            RectangularBeam.nominal_covering, 2.5, "c should be 2.5 cm", decimals=1
        )


class TestOwnWeight:
    """Item f) — own weight of the 18 x 95 cm beam"""

    def test_own_weight(self) -> None:
        g_v = LinearLoads.get_concrete_element_own_weight(0.18 * 0.95)
        assert_book_value(g_v, 4.275, "g_v should be 4.275 kN/m", decimals=3)


class TestSlabOnlyDiagrams:
    """Figure 4.15 — diagrams without the beam's own weight"""

    def test_negative_moment(self, slab_only_analysis: BeamAnalysis) -> None:
        moment = slab_only_analysis.bending_moment(CENTRAL_SUPPORT)
        assert_book_value(-moment, 292.0, "M- should be 292.0 kN·m", decimals=1)

    def test_positive_moment(self, slab_only_analysis: BeamAnalysis) -> None:
        _, moment = slab_only_analysis.moment_extremes_per_segment()[FIRST_SPAN_SEGMENT]
        assert_book_value(moment, 164.2, "M+ should be 164.2 kN·m", decimals=1)

    def test_end_support_shear(self, slab_only_analysis: BeamAnalysis) -> None:
        shear = slab_only_analysis.shear_force(SIDE_OFFSET)
        assert_book_value(abs(shear), 109.5, "V should be 109.5 kN", decimals=1)

    def test_central_support_shear(self, slab_only_analysis: BeamAnalysis) -> None:
        left = slab_only_analysis.shear_force(CENTRAL_SUPPORT - SIDE_OFFSET)
        right = slab_only_analysis.shear_force(CENTRAL_SUPPORT + SIDE_OFFSET)

        assert_book_value(abs(left), 182.5, "V left should be 182.5 kN", decimals=1)
        assert_book_value(abs(right), 182.5, "V right should be 182.5 kN", decimals=1)

        assert left * right < 0, "shear should change sign at the central support"


class TestFinalDiagrams:
    """Figure 4.16 — diagrams with the final height of 95 cm"""

    def test_negative_moment(self, final_analysis: BeamAnalysis) -> None:
        moment = final_analysis.bending_moment(CENTRAL_SUPPORT)
        assert_book_value(-moment, 326.2, "M- should be 326.2 kN·m", decimals=1)

    def test_positive_moment(self, final_analysis: BeamAnalysis) -> None:
        _, moment = final_analysis.moment_extremes_per_segment()[FIRST_SPAN_SEGMENT]
        assert_book_value(moment, 183.5, "M+ should be 183.5 kN·m", decimals=1)

    def test_end_support_shear(self, final_analysis: BeamAnalysis) -> None:
        shear = final_analysis.shear_force(SIDE_OFFSET)
        assert_book_value(abs(shear), 122.3, "V should be 122.3 kN", decimals=1)

    def test_central_support_shear(self, final_analysis: BeamAnalysis) -> None:
        left = final_analysis.shear_force(CENTRAL_SUPPORT - SIDE_OFFSET)
        right = final_analysis.shear_force(CENTRAL_SUPPORT + SIDE_OFFSET)
        assert_book_value(abs(left), 203.9, "V left should be 203.9 kN", decimals=1)
        assert_book_value(abs(right), 203.9, "V right should be 203.9 kN", decimals=1)
        assert left * right < 0, "shear should change sign at the central support"
