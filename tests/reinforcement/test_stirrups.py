"""Unit tests for the Stirrups reinforcement selector."""

import types
from typing import cast

import pytest

from src.calculators.stirrup_calculator import StirrupCalculator
from src.properties.steel import Steel
from src.reinforcement.stirrups import Stirrups
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


class TestPickBestOption:
    """Tests for selecting the option with the lowest reinforcement ratio."""

    def test_lowest_ratio_wins(self) -> None:
        best = Stirrups._pick_best_option([(10.0, 0.5), (12.0, 0.8)]) # pyright: ignore[reportPrivateUsage]
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
