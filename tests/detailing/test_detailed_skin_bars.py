"""Tests for src/detailing/detailed_skin_bars.py."""

import pytest

from src.detailing.detailed_skin_bars import DetailedSkinBars
from src.properties.steel import Steel
from tests.helpers import assert_approx


def _skin(
    heights: tuple[float, ...] = (15.0, 25.0, 35.0),
    start: float = 10.0,
    end: float = 235.0,
) -> DetailedSkinBars:
    """Build the φ8 skin bars of span P1–P2"""
    return DetailedSkinBars(
        start_pillar_id="P1",
        end_pillar_id="P2",
        diameter_mm=8,
        steel=Steel.CA50,
        heights=heights,
        start=start,
        end=end,
    )


class TestDetailedSkinBars:
    """One straight bar on each side face per row."""

    def test_quantity_is_two_per_row(self) -> None:
        assert _skin().quantity == 6, "3 rows x 2 side faces"

    def test_lengths(self) -> None:
        skin = _skin()
        assert_approx(skin.straight_length, 225.0, "clear span (cm)")
        assert_approx(skin.total_length, 225.0, "straight bars, no hooks (cm)")

    def test_span_name(self) -> None:
        assert _skin().span_name == "P1–P2", "named after its pillars"

    def test_no_rows_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one row"):
            _skin(heights=())

    def test_reversed_extent_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot end before"):
            _skin(start=235.0, end=10.0)
