"""Carvalho, chapter 4, Example 1 — beam V101 from loads to steel.

Chains the engine steps the book goes through: loads into the analysis, the
analysis extremes into the area calculation, and the book's support layout
into the effective depth check.

FROZEN: inputs and expected values come from the book's worked example
(Carvalho & Figueiredo Filho, 2014, p. 244–257).
Do not change them; see the "Source-of-truth tests" section of AGENTS.md.
"""

import pytest

from src.analysis.beam_analysis import BeamAnalysis
from src.analysis.model import BeamSupport, DistributedLoad
from src.analysis.solver import analyse_beam
from src.calculators.rebar_calculator import RebarCalculator
from src.config import APP_CONFIG
from src.config_options import ExposureClass
from src.loading.linear_loads import LinearLoads
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.structural_elements.rebar import Rebar
from src.structural_elements.rectangular_beam import RectangularBeam
from tests.carvalho_source_of_truth.book_tolerance import assert_book_value

LENGTH = 1600  # cm
CENTRAL_SUPPORT = 800  # cm
WIDTH = 18  # cm
HEIGHT = 95  # cm
SLAB_LOAD = 36.500  # kN/m
ADOPTED_D = 85  # cm
STIRRUP_DIAMETER = 0.63  # cm
FIRST_SPAN_SEGMENT = 0  # moment segments: first span, central support, second span
SUPPORT_SEGMENT = 1


@pytest.fixture(autouse=True)
def book_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the materials, environment and aggregate of the example

    C20, CAA I, brita 2 (d_max = 2.5 cm), and room for the book's 4 layers.
    """
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C20)
    monkeypatch.setattr(APP_CONFIG, "exposure_class", ExposureClass.WEAK)
    monkeypatch.setattr(APP_CONFIG, "max_aggregate_size", 2.5)
    monkeypatch.setattr(APP_CONFIG, "max_layers", 4)


@pytest.fixture
def beam() -> RectangularBeam:
    """V101 section, 18 x 95 cm, CA50, two 8.00 m spans"""
    return RectangularBeam(length=LENGTH, width=WIDTH, height=HEIGHT, steel=Steel.CA50)


@pytest.fixture
def analysis(beam: RectangularBeam) -> BeamAnalysis:
    """Two-span analysis under the slab reaction and the beam's own weight"""
    own_weight = LinearLoads.get_concrete_element_own_weight(WIDTH / 100 * HEIGHT / 100)
    loads = [
        DistributedLoad(0, LENGTH, SLAB_LOAD),
        DistributedLoad(0, LENGTH, own_weight),
    ]
    supports = [BeamSupport(0), BeamSupport(CENTRAL_SUPPORT), BeamSupport(LENGTH)]
    return analyse_beam(beam, supports, loads)


def _calculator_at(
    beam: RectangularBeam, analysis: BeamAnalysis, segment: int
) -> RebarCalculator:
    """Calculator at the extreme moment of a segment, with the adopted d"""
    position, moment = analysis.moment_extremes_per_segment()[segment]
    return RebarCalculator(
        beam=beam,
        bending_moment=moment,
        bending_moment_position=position,
        d=ADOPTED_D,
    )


class TestLoadsToMoments:
    """Items c) and f) into figure 4.16"""

    def test_support_moment(self, analysis: BeamAnalysis) -> None:
        moment = analysis.bending_moment(CENTRAL_SUPPORT)
        assert_book_value(-moment, 326.2, "M- should be 326.2 kN·m", decimals=1)

    def test_span_moment(self, analysis: BeamAnalysis) -> None:
        _, moment = analysis.moment_extremes_per_segment()[FIRST_SPAN_SEGMENT]
        assert_book_value(moment, 183.5, "M+ should be 183.5 kN·m", decimals=1)


class TestMomentsToArea:
    """Figure 4.16 into item g)"""

    def test_support_area(self, beam: RectangularBeam, analysis: BeamAnalysis) -> None:
        calculator = _calculator_at(beam, analysis, SUPPORT_SEGMENT)
        assert not calculator.tensioned_reinforcement.is_bottom_reinforcement, (
            "support steel should be on top"
        )
        assert_book_value(calculator.as1, 14.97, "As should be 14.97 cm²", decimals=2)

    def test_span_area(self, beam: RectangularBeam, analysis: BeamAnalysis) -> None:
        calculator = _calculator_at(beam, analysis, FIRST_SPAN_SEGMENT)
        assert calculator.tensioned_reinforcement.is_bottom_reinforcement, (
            "span steel should be at the bottom"
        )
        assert_book_value(calculator.as1, 7.64, "As should be 7.64 cm²", decimals=2)


class TestAreaToEffectiveDepth:
    """Item g) into item i.3) — the support layout keeps the adopted d valid"""

    def test_support_layout_verifies_adopted_depth(
        self, beam: RectangularBeam, analysis: BeamAnalysis
    ) -> None:
        position, moment = analysis.moment_extremes_per_segment()[SUPPORT_SEGMENT]
        calculator = RebarCalculator(
            beam=beam, bending_moment=moment, bending_moment_position=position
        )
        layout = calculator.tensioned_reinforcement
        layout.stirrup_diameter = STIRRUP_DIAMETER
        layout.distribute_bars_in_layers([Rebar(12.5, Steel.CA50) for _ in range(12)])
        layout.is_chosen = True
        calculator.stirrup_diameter = STIRRUP_DIAMETER

        assert_book_value(calculator.d, 85.97, "d should be 85.97 cm", decimals=2)
        assert calculator.as1 <= 14.97, (
            "As at d_real should not exceed As at the adopted d (14.97 cm²)"
        )
