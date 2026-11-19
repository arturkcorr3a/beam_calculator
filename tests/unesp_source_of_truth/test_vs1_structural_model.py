"""Bastos (UNESP), item 19 — structural model of beam VS1 with elastic end supports.

FROZEN: inputs and expected values come from Bastos (UNESP),
Vigas de Concreto Armado, item 19 (p. 74–97) and Annex IV (p. 172–173).
The example follows ABNT NBR 6118:2014; the book solves the model with FTOOL.
"""

import pytest

from src.analysis.beam_analysis import BeamAnalysis
from src.analysis.model import BeamSupport, DistributedLoad
from src.analysis.solver import analyse_beam
from src.config import APP_CONFIG
from src.config_options import Aggregate
from src.pavement_elements.geometry_utils import Axis
from src.pavement_elements.pillar import Pillar
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.structural_elements.rectangular_beam import RectangularBeam
from tests.helpers import assert_approx

SPAN_1 = 719.0  # cm, effective span
SPAN_2 = 713.5  # cm, effective span
LENGTH = SPAN_1 + SPAN_2  # cm
LOAD = 22.62  # kN/m
SPRING_P1 = 699_601 / 100  # kN.m/rad, book gives kN.cm/rad
SPRING_P3 = 2_753_955 / 100  # kN.m/rad
SIDE_OFFSET = 1e-3  # cm, to read the shear just beside a support
KN_CM_PER_KN_M = 100
RELATIVE_TOLERANCE = 0.005  # 0.5 %, absorbs the book's rounded intermediates
PILLAR_LANCE = 3.0  # m, column lance above and below the floor


@pytest.fixture(autouse=True)
def book_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the materials of the example (C30, basalt aggregate)"""
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C30)
    monkeypatch.setattr(APP_CONFIG, "aggregate", Aggregate.BASALT)


@pytest.fixture
def analysis() -> BeamAnalysis:
    """Solve VS1: pinned P2 and rotational springs at P1 and P3"""
    beam = RectangularBeam(length=LENGTH, width=19, height=60, steel=Steel.CA50)
    supports = [
        BeamSupport(0, SPRING_P1),
        BeamSupport(SPAN_1),
        BeamSupport(LENGTH, SPRING_P3),
    ]
    return analyse_beam(beam, supports, [DistributedLoad(0, LENGTH, LOAD)])


def _assert_book_moment(actual_kn_m: float, expected_kn_cm: float, name: str) -> None:
    """Compare a moment in kN.m against the book's value in kN.cm"""
    assert_approx(
        actual_kn_m * KN_CM_PER_KN_M,
        expected_kn_cm,
        f"{name} should be {expected_kn_cm} kN.cm",
        abs_tol=RELATIVE_TOLERANCE * abs(expected_kn_cm),
    )


class TestElasticSupportMoments:
    """Figure 80 — characteristic moments with spring supports at P1 and P3"""

    def test_negative_moment_at_inner_support(self, analysis: BeamAnalysis) -> None:
        _assert_book_moment(analysis.bending_moment(SPAN_1), -13_538, "M(P2)")

    def test_negative_moment_at_stiffer_end_support(
        self, analysis: BeamAnalysis
    ) -> None:
        _assert_book_moment(analysis.bending_moment(LENGTH), -2_843, "M(P3)")

    def test_maximum_positive_moment_in_second_span(
        self, analysis: BeamAnalysis
    ) -> None:
        positive_moments = [
            moment
            for position, moment in analysis.moment_extremes_per_segment()
            if position > SPAN_1 and moment > 0
        ]
        moment = max(positive_moments)
        _assert_book_moment(moment, 6_700, "M+ of span 2")

    def test_stiffer_spring_attracts_more_moment(self, analysis: BeamAnalysis) -> None:
        """Footnote 105 — P3 is stiffer than P1, so its moment is larger"""
        assert abs(analysis.bending_moment(LENGTH)) > abs(analysis.bending_moment(0))


class TestInnerSupportClassification:
    """Item 19 — P2 (b_int = 30 cm) is not wider than e/4 = 300/4 = 75 cm.

    The book then models P2 as a simple support; the engine keeps the pillar's spring
    there by design choice (Bastos, note 102), so only the classification is compared.
    """

    def test_p2_is_not_rigid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(APP_CONFIG, "ceiling_height", PILLAR_LANCE)
        p2 = Pillar(x=SPAN_1, y=0, width=30, depth=19)
        assert not p2.is_rigid_inner_support(Axis.X), "b_int = 30 cm <= e/4 = 75 cm"
