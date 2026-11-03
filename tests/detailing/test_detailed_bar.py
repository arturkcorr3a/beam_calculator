"""Tests for src/detailing/detailed_bar.py."""

import pytest

from src.detailing.detailed_bar import BarRole, DetailedBar
from src.properties.steel import Steel
from src.structural_elements.rebar import HookGeometry
from tests.helpers import assert_approx


def _bar(start: float = 20.0, end: float = 320.0, quantity: int = 2) -> DetailedBar:
    """Build a bottom φ12.5 run, without hooks unless set afterwards"""
    return DetailedBar(
        diameter_mm=12.5,
        steel=Steel.CA50,
        quantity=quantity,
        is_bottom=True,
        is_tensioned=True,
        layer_index=0,
        y=4.0,
        start=start,
        end=end,
    )


class TestDefaults:
    """A bar run is a main bar without hooks or mark unless told otherwise."""

    def test_defaults(self) -> None:
        bar = _bar()
        assert bar.role == BarRole.MAIN, "Default role is main"
        assert bar.left_hook is None and bar.right_hook is None, "No hooks by default"
        assert bar.mark is None, "No mark until marks are assigned"


class TestLengths:
    """The straight length runs between the ends; hooks add their extra length."""

    def test_straight_length(self) -> None:
        assert_approx(_bar().straight_length, 300.0, "320 − 20 cm")

    def test_total_length_adds_hooks(self) -> None:
        bar = _bar()
        bar.left_hook = HookGeometry(pin_diameter=6.25, tip_length=10.0)
        bar.left_hook_length = 11.4
        bar.right_hook_length = 0.0
        assert_approx(bar.total_length, 311.4, "300 cm straight + 11.4 cm hook")


class TestValidation:
    """Runs need at least one bar and a non-negative extent."""

    def test_zero_quantity_raises(self) -> None:
        with pytest.raises(ValueError, match="at least 1 bar"):
            _bar(quantity=0)

    def test_end_before_start_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot end before it starts"):
            _bar(start=100.0, end=99.0)

    def test_zero_length_allowed(self) -> None:
        bar = _bar(start=0.0, end=0.0)
        assert bar.straight_length == 0.0, "A hook-only bar has no straight length"
