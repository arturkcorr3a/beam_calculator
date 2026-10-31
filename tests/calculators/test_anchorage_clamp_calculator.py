"""Unit tests for src/calculators/anchorage_clamp_calculator.py — AnchorageClampCalculator."""

from collections.abc import Callable

import pytest

from src.calculators.anchorage_clamp_calculator import (
    AnchorageClampCalculator,
    AnchorageClampCalculatorLabel,
)
from src.config import APP_CONFIG
from src.properties.steel import Steel
from src.reinforcement.clamps import Clamps
from tests.helpers import assert_approx


def _always_fits(diameter_mm: float, quantity: int) -> bool:
    """Let every clamp arrangement fit in the section"""
    return True


def _make_calculator(
    clamps_fit: Callable[[float, int], bool] = _always_fits,
    existing_clamps: Clamps | None = None,
) -> AnchorageClampCalculator:
    """Build a calculator with f_bd = 0.25 kN/cm² and 20 cm available

    R_sd = (30 / 40) · 100 = 75 kN and R_sc = 75 · (1 - 20 / 50) = 45 kN, so
    A_sc = 45 / 43.48 = 1.035 cm² with CA50.
    """
    return AnchorageClampCalculator(
        moment_shift=30.0,
        effective_depth=40.0,
        design_shear=100.0,
        label_info=AnchorageClampCalculatorLabel(beam_label="V1", is_left=True),
        available_length=20.0,
        necessary_length=50.0,
        design_bond_strength=0.25,
        stirrup_inner_width=15.0,
        clamps_fit=clamps_fit,
        existing_clamps=existing_clamps,
    )


@pytest.fixture(autouse=True)
def pinned_steel(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the project steel to CA50 for every test in this module"""
    monkeypatch.setattr(APP_CONFIG, "pavement_steel", Steel.CA50)


@pytest.fixture
def calculator() -> AnchorageClampCalculator:
    """Build a calculator where every clamp arrangement fits"""
    return _make_calculator()


class TestRequiredClampLength:
    def test_converts_diameter_from_mm_to_cm(
        self, calculator: AnchorageClampCalculator
    ) -> None:
        """Compute l_c = (1.25 / 4) · (50 / 1.15) / 0.25 + 20 for a 12.5 mm clamp"""
        length = calculator._calculate_required_clamp_length(12.5)  # pyright: ignore[reportPrivateUsage]
        assert_approx(length, 74.34783, "l_c for a 12.5 mm clamp (cm)")


class TestChooseClamps:
    """Tests for the clamp diameter and quantity chosen for a required area."""

    def test_closest_area_wins(self, calculator: AnchorageClampCalculator) -> None:
        """1.0 cm²: one 8 mm clamp (1.005 cm²) beats 2φ6.3 (1.247) and 1φ10 (1.571)"""
        choice = calculator._choose_clamps(1.0)  # pyright: ignore[reportPrivateUsage]
        assert choice == (8, 1), "One 8 mm clamp"

    def test_fewer_clamps_win_within_band(
        self, calculator: AnchorageClampCalculator
    ) -> None:
        """2.4 cm²: 1φ12.5 (2.454) and 4φ6.3 (2.494) are within 5%; fewer clamps win"""
        choice = calculator._choose_clamps(2.4)  # pyright: ignore[reportPrivateUsage]
        assert choice == (12.5, 1), "One 12.5 mm clamp"

    def test_smaller_diameter_breaks_tie(
        self, calculator: AnchorageClampCalculator
    ) -> None:
        """0.1 cm²: every diameter needs one clamp; the band keeps only 1φ6.3 (0.623)"""
        choice = calculator._choose_clamps(0.1)  # pyright: ignore[reportPrivateUsage]
        assert choice == (6.3, 1), "One 6.3 mm clamp"

    def test_skips_options_that_do_not_fit(self) -> None:
        """2.4 cm² without room for 12.5 mm clamps: 4φ6.3 (2.494) is chosen"""
        calculator = _make_calculator(clamps_fit=lambda d, n: d != 12.5)
        choice = calculator._choose_clamps(2.4)  # pyright: ignore[reportPrivateUsage]
        assert choice == (6.3, 4), "Four 6.3 mm clamps"

    def test_raises_when_nothing_fits(self) -> None:
        calculator = _make_calculator(clamps_fit=lambda d, n: False)
        with pytest.raises(ValueError, match="No clamp arrangement fits"):
            calculator._choose_clamps(1.0)  # pyright: ignore[reportPrivateUsage]


class TestRun:
    """Tests for run(), with and without the side's existing clamps."""

    def test_chooses_clamps(self, calculator: AnchorageClampCalculator) -> None:
        """A_sc = 1.035 cm²: 2φ6.3 (1.247) beats 1φ10 (1.571), outside the 5% band"""
        clamps = calculator.run()
        assert (clamps.diameter, clamps.quantity) == (6.3, 2), "Two 6.3 mm clamps"
        assert_approx(clamps.width, 15.0, "Clamp width = stirrup inner width (cm)")

    def test_reuses_existing_clamps_with_enough_area(self) -> None:
        existing = Clamps(diameter=12.5, quantity=1, width=15.0, length=60.0)
        clamps = _make_calculator(existing_clamps=existing).run()
        assert clamps is existing, "2.45 cm² covers 1.035 cm², so it is reused"

    def test_chooses_again_when_existing_clamps_fall_short(self) -> None:
        existing = Clamps(diameter=8, quantity=1, width=15.0, length=60.0)
        clamps = _make_calculator(existing_clamps=existing).run()
        assert clamps is not existing, "1.005 cm² is short of 1.035 cm²"
        assert (clamps.diameter, clamps.quantity) == (6.3, 2), "Two 6.3 mm clamps"
