"""Unit tests for src/reinforcement/staggering.py — moment bands and nearest positions."""

import pytest

from src.reinforcement.staggering import layer_moment_bands, nearest_distance
from tests.helpers import assert_approx


class TestLayerMomentBands:
    """Tests for the split of the section moment among the layers (kN.m)."""

    def test_bands_follow_the_area_shares(self) -> None:
        """Areas 3, 2 and 1 cm² split 60 kN.m into 30, 20 and 10 kN.m"""
        bands = layer_moment_bands([3.0, 2.0, 1.0], 60.0)
        expected = [(0.0, 30.0), (30.0, 50.0), (50.0, 60.0)]
        for index, (band, (lower, upper)) in enumerate(
            zip(bands, expected, strict=True)
        ):
            assert_approx(band[0], lower, f"layer {index} band bottom (kN.m)")
            assert_approx(band[1], upper, f"layer {index} band top (kN.m)")

    def test_first_band_starts_at_zero(self) -> None:
        bands = layer_moment_bands([1.6, 0.8], 45.7)
        assert bands[0][0] == 0.0, "the first layer's band starts at zero moment"

    def test_last_band_ends_at_the_section_moment(self) -> None:
        bands = layer_moment_bands([1.6, 0.8, 0.31], 45.7)
        assert bands[-1][1] == 45.7, "the innermost band ends exactly at M"

    def test_single_layer_takes_the_whole_moment(self) -> None:
        assert layer_moment_bands([2.0], 30.0) == [(0.0, 30.0)], (
            "one layer resists the whole moment"
        )

    def test_negative_moment_keeps_its_sign(self) -> None:
        """Areas 1 and 3 cm² split -40 kN.m into -10 and -30 kN.m"""
        bands = layer_moment_bands([1.0, 3.0], -40.0)
        assert_approx(bands[0][1], -10.0, "first band top (kN.m)")
        assert_approx(bands[1][0], -10.0, "second band bottom (kN.m)")
        assert_approx(bands[1][1], -40.0, "second band top (kN.m)")

    def test_no_area_raises(self) -> None:
        with pytest.raises(ValueError, match="positive total area"):
            layer_moment_bands([], 10.0)


class TestNearestDistance:
    """Tests for the distance to the nearest position on one side (cm)."""

    def test_left(self) -> None:
        distance = nearest_distance(250.0, [50.0, 180.0, 320.0], left=True)
        assert distance is not None, "a position lies on the left"
        assert_approx(distance, 70.0, "nearest on the left is 180 cm (cm)")

    def test_right(self) -> None:
        distance = nearest_distance(250.0, [50.0, 180.0, 320.0, 400.0], left=False)
        assert distance is not None, "a position lies on the right"
        assert_approx(distance, 70.0, "nearest on the right is 320 cm (cm)")

    def test_none_on_the_side(self) -> None:
        assert nearest_distance(250.0, [300.0], left=True) is None, (
            "no position on the left"
        )

    def test_section_itself_is_skipped(self) -> None:
        assert nearest_distance(250.0, [250.0], left=False) is None, (
            "the section's own position is not on either side"
        )

    def test_limit_drops_farther_positions(self) -> None:
        assert nearest_distance(250.0, [100.0], left=True, limit=120.0) is None, (
            "a position past the limit is ignored"
        )

    def test_limit_keeps_a_position_on_it(self) -> None:
        distance = nearest_distance(250.0, [130.0], left=True, limit=120.0)
        assert distance is not None, "a position on the limit counts"
        assert_approx(distance, 120.0, "distance up to the limit (cm)")
