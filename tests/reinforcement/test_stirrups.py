"""Unit tests for the Stirrups reinforcement selector."""

import types
from itertools import pairwise
from typing import cast

import pytest

from src.analysis.beam_analysis import BeamAnalysis
from src.calculators.stirrup_calculator import MIN_SPACING, StirrupCalculator
from src.config import APP_CONFIG
from src.errors import StirrupBendUndefinedError
from src.loading.forces import LOAD_FACTOR
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.reinforcement.stirrups import Stirrups, StirrupZone
from src.structural_elements.rectangular_beam import RectangularBeam
from tests.helpers import assert_approx


@pytest.fixture
def stirrups() -> Stirrups:
    """Build a Stirrups over a light beam double (CA50, 20 cm wide).

    The beam and calculator are ``SimpleNamespace`` doubles: ``max_diameter``
    only reads ``beam.width`` and ``pick_diameter_for_spacing`` reads
    ``beam.steel.available_sizes`` plus ``self.required_ratio`` (set per test),
    while ``choose`` reads ``calculator.max_spacing``. None of the heavy
    ``StirrupCalculator`` machinery is exercised.
    """
    beam = types.SimpleNamespace(steel=Steel.CA50, width=20.0)
    calculator = types.SimpleNamespace(max_spacing=20.0)
    return Stirrups(
        cast(RectangularBeam, beam),
        cast(StirrupCalculator, calculator),
        id="ST",
    )


class TestCalculateRatio:
    """Tests for the two-legged reinforcement ratio A_sw/s."""

    def test_area_over_spacing(self) -> None:
        expected_ratio = 0.039269908169872414  # cm²/cm (2 * pi * 0.25² / 10)
        assert_approx(
            Stirrups.calculate_ratio(0.5, 10.0),
            expected_ratio,
            "Ratio should be two leg areas divided by the spacing",
        )

    def test_zero_spacing_raises(self) -> None:
        with pytest.raises(ZeroDivisionError):
            Stirrups.calculate_ratio(0.5, 0.0)


class TestClosedLengthFor:
    """Cut length of a closed stirrup with 135° hooks, along the bar's axis."""

    def test_short_tip_uses_five_centimeters(self) -> None:
        # D = 1.89, r = 1.26: 140 − 12.6 + 5.94 + 5.94 + 2 × 5 cm
        assert_approx(
            Stirrups.closed_length_for(15.0, 55.0, 6.3, Steel.CA50),
            149.27522023056943,
            "φ6.3 in a 15 x 55 cm stirrup: 5φ = 3.15 < 5 cm (cm)",
        )

    def test_long_tip_uses_five_diameters(self) -> None:
        # D = 6.25, r = 3.75: 140 − 35 + 17.67 + 17.67 + 2 × 6.25 cm
        assert_approx(
            Stirrups.closed_length_for(15.0, 55.0, 12.5, Steel.CA50),
            152.84291735288517,
            "φ12.5 in a 15 x 55 cm stirrup: 5φ = 6.25 > 5 cm (cm)",
        )

    def test_bar_without_bend_diameter_raises(self) -> None:
        with pytest.raises(StirrupBendUndefinedError, match="No stirrup bend diameter"):
            Stirrups.closed_length_for(15.0, 55.0, 12.5, Steel.CA60)


class TestPickBestOption:
    """Tests for selecting the option with the lowest reinforcement ratio."""

    def test_lowest_ratio_wins(self) -> None:
        best = Stirrups._pick_best_option([(10.0, 0.5), (12.0, 0.8)])  # pyright: ignore[reportPrivateUsage]
        assert best == (10.0, 0.5), (
            "The widest spacing with the thinnest bar has the lowest ratio"
        )


class TestMaxDiameter:
    """Tests for the maximum stirrup diameter (width / 10)."""

    def test_width_over_ten(self, stirrups: Stirrups) -> None:
        assert stirrups.max_diameter == 2.0, (
            "A 20 cm wide beam allows a 2.0 cm maximum stirrup diameter"
        )


class TestPickDiameterForSpacing:
    """Tests for picking the first diameter meeting the required ratio."""

    def test_returns_first_meeting_ratio(self, stirrups: Stirrups) -> None:
        stirrups.required_ratio = 0.01
        assert stirrups.pick_diameter_for_spacing(10.0) == 0.63, (
            "The smallest valid diameter (6.3 mm) already meets a low ratio"
        )

    def test_none_when_unmet(self, stirrups: Stirrups) -> None:
        stirrups.required_ratio = 999.0
        assert stirrups.pick_diameter_for_spacing(10.0) is None, (
            "No available diameter can meet an unreachable ratio"
        )


class TestChoose:
    """Tests for the full spacing/diameter selection loop."""

    def test_selects_best_spacing_and_diameter(self, stirrups: Stirrups) -> None:
        stirrups.required_ratio = 0.05
        assert stirrups.choose() == (20.0, 0.8), (
            "The best option should be the widest spacing meeting the ratio"
        )
        assert stirrups.spacing == 20.0, "choose should store the chosen spacing"
        assert stirrups.diameter == 0.8, "choose should store the chosen diameter"

    def test_unreachable_ratio_raises_value_error(self, stirrups: Stirrups) -> None:
        stirrups.required_ratio = 999.0
        with pytest.raises(ValueError, match="No stirrup meets"):
            stirrups.choose()

    def test_max_spacing_below_minimum_raises_value_error(
        self, stirrups: Stirrups
    ) -> None:
        stirrups.required_ratio = 0.01
        stirrups.calculator = cast(
            StirrupCalculator, types.SimpleNamespace(max_spacing=4.0)
        )  # below MIN_SPACING (5 cm): the spacing loop never runs
        with pytest.raises(ValueError, match="No stirrup meets"):
            stirrups.choose()

    def test_accepts_minimum_spacing(self, stirrups: Stirrups) -> None:
        stirrups.calculator = cast(
            StirrupCalculator, types.SimpleNamespace(max_spacing=MIN_SPACING)
        )
        stirrups.required_ratio = 0.01
        stirrups.choose()
        assert stirrups.spacing == MIN_SPACING, (
            "choose should allow a spacing equal to MIN_SPACING (cm)"
        )


# Real calculator for the scaling tests: C25, CA50, 20 cm wide, d = 56 cm.
_CONCRETE_CONTRIBUTION = 86.18278771250553  # kN, V_c = 0.6 * fctd * bw * d
_CONTRIBUTION_PER_RATIO = 0.9 * 56.0 * Steel.CA50.fywd  # kN per cm²/cm
_REDUCED_SPACING_LIMIT = 0.67 * 486.0  # kN, 0.67 * V_Rd2


def _resistance(diameter: float, spacing: float) -> float:
    """Return V_Rd3 (kN) of a two-legged stirrup of diameter (cm) at spacing (cm)."""
    ratio = Stirrups.calculate_ratio(diameter, spacing)  # cm²/cm
    return _CONCRETE_CONTRIBUTION + ratio * _CONTRIBUTION_PER_RATIO


class _LinearShear:
    """Analysis double with V(x) = start_shear + slope * x (kN, x in cm)."""

    def __init__(self, start_shear: float, slope: float) -> None:
        self.start_shear = start_shear  # kN
        self.slope = slope  # kN/cm

    def shear_force(self, position: float) -> float:
        return self.start_shear + self.slope * position

    def positions_for_shear(self, target_shear: float) -> list[float]:
        return [(target_shear - self.start_shear) / self.slope]


def _analysis(start_shear: float, slope: float) -> BeamAnalysis:
    """Return a linear shear double typed as a BeamAnalysis."""
    return cast(BeamAnalysis, _LinearShear(start_shear, slope))


@pytest.fixture
def scaled_stirrups(monkeypatch: pytest.MonkeyPatch) -> Stirrups:
    """Build Stirrups over a real StirrupCalculator, already chosen as phi 6.3 c/10.

    C25 concrete, CA50 steel, 20 cm wide, d = 56 cm, V_Sd = 200 kN: V_c = 86.18 kN,
    V_Rd2 = 486 kN, A_sw,min/s = 0.02052 cm²/cm and the low-shear s_max is 30 cm.
    """
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C25)
    beam = cast(RectangularBeam, types.SimpleNamespace(steel=Steel.CA50, width=20.0))
    calculator = StirrupCalculator(beam, design_shear_force=200.0, id="ST")
    calculator.effective_depth = 56.0
    stirrups = Stirrups(beam, calculator, id="ST")
    stirrups.diameter = 0.63
    stirrups.spacing = 10.0
    return stirrups


class TestMiddleSpacing:
    """Tests for the largest spacing of the chosen diameter."""

    def test_low_shear_max_spacing(self, scaled_stirrups: Stirrups) -> None:
        # phi 6.3 c/30: A_sw/s = 0.02078 >= 0.02052 cm²/cm
        assert scaled_stirrups._middle_spacing() == 30.0, (  # pyright: ignore[reportPrivateUsage]
            "phi 6.3 already meets the minimum ratio at s_max = 30 cm"
        )

    def test_minimum_ratio_governs(self, scaled_stirrups: Stirrups) -> None:
        # phi 5 c/20: A_sw/s = 0.01963 < 0.02052; c/19: 0.02067 cm²/cm
        scaled_stirrups.diameter = 0.5
        assert scaled_stirrups._middle_spacing() == 19.0, (  # pyright: ignore[reportPrivateUsage]
            "phi 5 must step down from 30 cm to 19 cm to meet the minimum ratio"
        )


class TestThresholdShearForce:
    """Tests for the design shear resisted at the middle spacing (kN)."""

    def test_resistance_of_middle_spacing(self, scaled_stirrups: Stirrups) -> None:
        scaled_stirrups.middle_spacing = 30.0
        assert_approx(
            scaled_stirrups._threshold_shear_force(),  # pyright: ignore[reportPrivateUsage]
            _resistance(0.63, 30.0),
            "V_lim should be V_Rd3 of phi 6.3 c/30 (kN)",
        )

    def test_capped_at_reduced_spacing_limit(self, scaled_stirrups: Stirrups) -> None:
        # phi 20 c/30 resists about 545 kN, above 0.67 * V_Rd2
        scaled_stirrups.diameter = 2.0
        scaled_stirrups.middle_spacing = 30.0
        assert_approx(
            scaled_stirrups._threshold_shear_force(),  # pyright: ignore[reportPrivateUsage]
            _REDUCED_SPACING_LIMIT,
            "V_lim should be capped at 0.67 * V_Rd2 (kN)",
        )


class TestDistribute:
    """Tests for splitting a span into stirrup zones."""

    def test_no_scaling_when_chosen_spacing_is_largest(
        self, scaled_stirrups: Stirrups
    ) -> None:
        scaled_stirrups.spacing = 30.0
        zones = scaled_stirrups.distribute(_analysis(150.0, -0.6), 0.0, 500.0)
        assert zones == [StirrupZone(0.0, 500.0, 30.0)], (
            "The chosen spacing already at s_max should give a single zone"
        )
        assert scaled_stirrups.threshold_shear_force is None, (
            "Without scaling there is no threshold shear force"
        )

    def test_symmetric_span(self, scaled_stirrups: Stirrups) -> None:
        # V_k from +150 to -150 kN over 500 cm
        zones = scaled_stirrups.distribute(_analysis(150.0, -0.6), 0.0, 500.0)
        crossing = (150.0 - _resistance(0.63, 30.0) / LOAD_FACTOR) / 0.6  # cm
        assert [zone.spacing for zone in zones] == [10.0, 30.0, 10.0], (
            "Edges keep the chosen spacing; the middle uses s_max"
        )
        assert_approx(zones[0].end, crossing, "Left zone end (cm)", abs_tol=1e-6)
        assert_approx(
            zones[2].start, 500.0 - crossing, "Right zone start (cm)", abs_tol=1e-6
        )
        assert scaled_stirrups.zones == zones, "distribute should store the zones"
        assert scaled_stirrups.middle_spacing == 30.0, (
            "distribute should store the middle spacing"
        )

    def test_asymmetric_ends(self, scaled_stirrups: Stirrups) -> None:
        # V_k from +200 to -100 kN over 500 cm: the left edge zone is longer
        zones = scaled_stirrups.distribute(_analysis(200.0, -0.6), 0.0, 500.0)
        threshold = _resistance(0.63, 30.0) / LOAD_FACTOR  # kN, characteristic
        assert [zone.spacing for zone in zones] == [10.0, 30.0, 10.0], (
            "Both ends exceed the threshold shear force"
        )
        assert_approx(
            zones[0].end, (200.0 - threshold) / 0.6, "Left zone end (cm)", abs_tol=1e-6
        )
        assert_approx(
            zones[2].start,
            (200.0 + threshold) / 0.6,
            "Right zone start (cm)",
            abs_tol=1e-6,
        )
        assert zones[0].end - zones[0].start > zones[2].end - zones[2].start, (
            "The end with greater shear needs the longer edge zone"
        )

    def test_end_below_threshold_has_no_edge_zone(
        self, scaled_stirrups: Stirrups
    ) -> None:
        # V_k from +150 to 0 kN over 500 cm: only the left end exceeds the threshold
        zones = scaled_stirrups.distribute(_analysis(150.0, -0.3), 0.0, 500.0)
        assert [zone.spacing for zone in zones] == [10.0, 30.0], (
            "Only the high-shear end gets the chosen spacing"
        )
        assert zones[-1].end == 500.0, "The last zone should end at the span end"

    def test_zones_tile_span_with_offset(self, scaled_stirrups: Stirrups) -> None:
        # Second span of a beam: 500-1000 cm, V_k from +150 to -150 kN
        zones = scaled_stirrups.distribute(_analysis(750.0, -1.2), 500.0, 1000.0)
        assert zones[0].start == 500.0, "The first zone should start at the span start"
        assert zones[-1].end == 1000.0, "The last zone should end at the span end"
        for previous, current in pairwise(zones):
            assert previous.end == current.start, "Zones should leave no gaps"
