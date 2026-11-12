"""Unit tests for src/calculators/outer_support_bars.py."""

import types
from typing import cast

import pytest

from src.calculators.outer_support_bars import (
    OuterSupport,
    anchor_outer_supports,
    outer_support_force,
)
from src.calculators.support_bars import SpanRange
from src.config import APP_CONFIG
from src.loading.forces import LOAD_FACTOR
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.reinforcement.reinforcement import Reinforcement
from src.structural_elements.rectangular_beam import RectangularBeam
from src.structural_elements.support import Support
from tests.helpers import assert_approx

_FIRST_SPAN = SpanRange(0.0, 500.0, 0, 1)
_SECOND_SPAN = SpanRange(500.0, 1000.0, 1, 2)
_MOMENT_SHIFT = 28.0  # cm
_EFFECTIVE_DEPTH = 55.0  # cm
_STRESS_BLOCK_DEPTH = 8.0  # cm


@pytest.fixture(autouse=True)
def pinned_concrete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the project concrete to C30 for every test in this module"""
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C30)


@pytest.fixture
def beam() -> RectangularBeam:
    """Build a 20x60 cm, 1000 cm beam double over three 20 cm-wide pillars"""
    double = types.SimpleNamespace(
        steel=Steel.CA50,
        width=20.0,
        height=60.0,
        length=1000.0,
        label="V1",
        supports=[
            Support(0.0, -10.0, 10.0),
            Support(500.0, 490.0, 510.0),
            Support(1000.0, 990.0, 1010.0),
        ],
    )
    return cast(RectangularBeam, double)


@pytest.fixture
def span_bars(beam: RectangularBeam) -> Reinforcement:
    """Choose 2φ16 (4.02 cm²) at the middle of the first span"""
    reinforcement = Reinforcement(
        beam,
        is_bottom_reinforcement=True,
        center_position=250.0,
        id="R",
        support_moments=(0.0, -40.0, 0.0),
        span_moment=50.0,
    )
    reinforcement.moment_shift = _MOMENT_SHIFT
    reinforcement.effective_depth = _EFFECTIVE_DEPTH
    reinforcement.design_shear = 100.0  # kN
    reinforcement.set_required_area(4.02)
    return reinforcement


def _support(
    support_index: int, design_shear: float, span: SpanRange = _FIRST_SPAN
) -> OuterSupport:
    return OuterSupport(
        support_index=support_index,
        span=span,
        support_moment=0.0,
        design_shear=design_shear,
        effective_depth=_EFFECTIVE_DEPTH,
        stress_block_depth=_STRESS_BLOCK_DEPTH,
        moment_shift=_MOMENT_SHIFT,
        stirrup_diameter=0.63,
    )


def _required_area(design_shear: float) -> float:
    """F_sd / f_yd with M_Sd = 0 (cm²)"""
    return (_MOMENT_SHIFT / _EFFECTIVE_DEPTH) * design_shear / Steel.CA50.fyd


class TestOuterSupportForce:
    """F_sd = M_Sd / z + (a_l / d) V_Sd >= (a_l / d) V_Sd (kN), NBR 6118 - 18.3.2.4-b."""

    def test_negative_moment_keeps_only_shear_term(self) -> None:
        """(28 / 40) · 100 = 70 kN"""
        force = outer_support_force(-30.0, 40.0, 8.0, 28.0, 100.0)
        assert_approx(force, 70.0, "negative moment does not tension the bars (kN)")

    def test_null_moment(self) -> None:
        force = outer_support_force(0.0, 40.0, 8.0, 28.0, 100.0)
        assert_approx(force, 70.0, "only the shear term (kN)")

    def test_positive_moment_adds_to_force(self) -> None:
        """M_Sd = 10 · 100 · γ_f kN.cm over z = 40 - 8/2 = 36 cm adds to 70 kN"""
        force = outer_support_force(10.0, 40.0, 8.0, 28.0, 100.0)
        expected = 10.0 * 100 * LOAD_FACTOR / 36.0 + 70.0  # kN
        assert_approx(force, expected, "M_Sd / z + (a_l / d) V_Sd (kN)")


class TestAnchorOuterSupports:
    """The end supports get the bars they lack for F_sd / f_yd."""

    def test_enough_area_adds_nothing(
        self, beam: RectangularBeam, span_bars: Reinforcement
    ) -> None:
        """2φ16 anchored in the support: 4.02 cm² ≥ F_sd / f_yd for V_Sd = 100 kN"""
        span_bars.extend_layer_to_support(0, 0, left=True)
        before = [bar.left_length for bar in span_bars.chosen_bars[0].bars]
        added = anchor_outer_supports(beam, [span_bars], [_support(0, 100.0)])
        assert added == [], "no bars are added"
        after = [bar.left_length for bar in span_bars.chosen_bars[0].bars]
        assert after == before, "the span bars are left as they were"

    def test_missing_area_in_a_new_layer(
        self, beam: RectangularBeam, span_bars: Reinforcement
    ) -> None:
        """V_Sd = 400 kN needs more than the 4.02 cm² anchored in the support"""
        span_bars.extend_layer_to_support(0, 0, left=True)
        carried = span_bars.area  # cm²
        (added,) = anchor_outer_supports(beam, [span_bars], [_support(0, 400.0)])
        assert added.first_layer_index == 1, "stacked after the span's layer 0"
        assert_approx(
            cast(float, added.required_area),
            _required_area(400.0) - carried,
            "only the missing area is sized (cm²)",
        )
        assert added.area >= cast(float, added.required_area), "the bars cover it"
        assert_approx(added.center_position, 10.0, "on the support's inner face (cm)")

    def test_no_bars_reaching_sizes_a_new_point(
        self, beam: RectangularBeam, span_bars: Reinforcement
    ) -> None:
        """The span bars stop short of the support: the whole area is sized"""
        (added,) = anchor_outer_supports(beam, [span_bars], [_support(0, 100.0)])
        assert added.first_layer_index == 0, "a new point starts at layer 0"
        assert_approx(
            cast(float, added.required_area),
            _required_area(100.0),
            "the whole F_sd / f_yd is sized (cm²)",
        )
        assert added.layer_reaches_support(0, 0, left=True), (
            "the new bars are anchored inside the support"
        )

    def test_span_without_positive_bars(self, beam: RectangularBeam) -> None:
        """The right end support of a span with no positive bars"""
        (added,) = anchor_outer_supports(
            beam, [], [_support(2, 100.0, span=_SECOND_SPAN)]
        )
        assert added.first_layer_index == 0, "a new point starts at layer 0"
        assert_approx(added.center_position, 990.0, "on the support's inner face (cm)")
        assert added.layer_reaches_support(0, 2, left=False), (
            "the new bars are anchored inside the right support"
        )

    def test_new_bars_are_bottom_and_tensioned(
        self, beam: RectangularBeam, span_bars: Reinforcement
    ) -> None:
        (added,) = anchor_outer_supports(beam, [span_bars], [_support(0, 100.0)])
        assert added.is_bottom_reinforcement, "bottom bars"
        assert added.is_tensioned, "tensioned bars"
        assert added.span_moment is None, "ignored by the span checks"
