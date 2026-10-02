"""Tests for src/pavement_elements/geometry_utils.py."""

import pytest

from src.pavement_elements.geometry_utils import (
    TOLERANCE,
    Alignment,
    Axis,
    Point,
    between,
    calculate_polygon_area,
    effective_span,
    get_pillar_parallel_extent,
    get_pillar_perpendicular_range,
    round_up_to_multiple_of_5,
)
from src.pavement_elements.pillar import Pillar
from tests.helpers import assert_approx

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def pillar() -> Pillar:
    """A 20×30 cm pillar centred at (100, 200)."""
    return Pillar(x=100, y=200, width=20, depth=30)


# ---------------------------------------------------------------------------
# TestAlignmentValidate
# ---------------------------------------------------------------------------


class TestAlignmentValidate:
    """Alignment.validate accepts the correct axes and rejects the wrong ones."""

    def test_bottom_valid_on_x_axis(self) -> None:
        Alignment.BOTTOM.validate(Axis.X)  # must not raise

    def test_top_valid_on_x_axis(self) -> None:
        Alignment.TOP.validate(Axis.X)  # must not raise

    def test_left_valid_on_y_axis(self) -> None:
        Alignment.LEFT.validate(Axis.Y)  # must not raise

    def test_right_valid_on_y_axis(self) -> None:
        Alignment.RIGHT.validate(Axis.Y)  # must not raise

    def test_center_valid_on_x_axis(self) -> None:
        Alignment.CENTER.validate(Axis.X)  # must not raise

    def test_center_valid_on_y_axis(self) -> None:
        Alignment.CENTER.validate(Axis.Y)  # must not raise

    def test_left_invalid_on_x_axis(self) -> None:
        with pytest.raises(ValueError, match="not valid for horizontal"):
            Alignment.LEFT.validate(Axis.X)

    def test_bottom_invalid_on_y_axis(self) -> None:
        with pytest.raises(ValueError, match="not valid for vertical"):
            Alignment.BOTTOM.validate(Axis.Y)


# ---------------------------------------------------------------------------
# TestAxisGrouping
# ---------------------------------------------------------------------------


class TestAxisGrouping:
    """Axis.get_horizontal and get_vertical return the correct alignment sets."""

    def test_get_horizontal_contains_x_values(self) -> None:
        horizontal = Alignment.get_horizontal()
        assert horizontal == {Alignment.TOP, Alignment.BOTTOM, Alignment.CENTER}, (
            "get_horizontal() should return TOP, BOTTOM, CENTER"
        )

    def test_get_vertical_contains_y_values(self) -> None:
        vertical = Alignment.get_vertical()
        assert vertical == {Alignment.LEFT, Alignment.RIGHT, Alignment.CENTER}, (
            "get_vertical() should return LEFT, RIGHT, CENTER"
        )


# ---------------------------------------------------------------------------
# TestBetween
# ---------------------------------------------------------------------------


class TestBetween:
    """between() is inclusive at the TOLERANCE boundary."""

    def test_interior_value_is_true(self) -> None:
        assert between(0.5, 0.0, 1.0), "interior value should be in range"

    def test_exactly_at_low_minus_tolerance_is_true(self) -> None:
        assert between(0.0 - TOLERANCE, 0.0, 1.0), "low - TOLERANCE should be in range"

    def test_just_inside_low_tolerance_is_true(self) -> None:
        assert between(0.0 - TOLERANCE + 1e-9, 0.0, 1.0), (
            "just inside low boundary should be in range"
        )

    def test_just_outside_low_tolerance_is_false(self) -> None:
        assert not between(0.0 - TOLERANCE - 1e-9, 0.0, 1.0), (
            "just outside low boundary should be out of range"
        )

    def test_exactly_at_high_plus_tolerance_is_true(self) -> None:
        assert between(1.0 + TOLERANCE, 0.0, 1.0), "high + TOLERANCE should be in range"

    def test_just_inside_high_tolerance_is_true(self) -> None:
        assert between(1.0 + TOLERANCE - 1e-9, 0.0, 1.0), (
            "just inside high boundary should be in range"
        )

    def test_just_outside_high_tolerance_is_false(self) -> None:
        assert not between(1.0 + TOLERANCE + 1e-9, 0.0, 1.0), (
            "just outside high boundary should be out of range"
        )


# ---------------------------------------------------------------------------
# TestRoundUpToMultipleOf5
# ---------------------------------------------------------------------------


class TestRoundUpToMultipleOf5:
    """round_up_to_multiple_of_5 rounds upward to the next multiple of 5."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            (0, 0),
            (1, 5),
            (5, 5),
            (6, 10),
            (10, 10),
            (11, 15),
            (24, 25),
            (25, 25),
        ],
        ids=["0", "1", "5", "6", "10", "11", "24", "25"],
    )
    def test_rounding(self, value: int, expected: int) -> None:
        assert round_up_to_multiple_of_5(value) == expected, (
            f"round_up_to_multiple_of_5({value}) should be {expected}"
        )


# ---------------------------------------------------------------------------
# TestCalculatePolygonArea
# ---------------------------------------------------------------------------


class TestCalculatePolygonArea:
    """calculate_polygon_area uses the shoelace formula."""

    def test_unit_square(self) -> None:
        vertices = [Point(0, 0), Point(1, 0), Point(1, 1), Point(0, 1)]
        assert_approx(
            calculate_polygon_area(vertices), 1.0, "unit square area should be 1.0"
        )

    def test_right_triangle(self) -> None:
        # base=2, height=3 -> area=3.0
        vertices = [Point(0, 0), Point(2, 0), Point(0, 3)]
        assert_approx(
            calculate_polygon_area(vertices), 3.0, "right triangle area should be 3.0"
        )

    def test_reversed_winding_gives_same_area(self) -> None:
        cw = [Point(0, 0), Point(1, 0), Point(1, 1), Point(0, 1)]
        ccw = list(reversed(cw))
        assert_approx(
            calculate_polygon_area(cw),
            calculate_polygon_area(ccw),
            "reversed winding should produce the same area",
        )

    @pytest.mark.parametrize(
        "vertices,expected",
        [
            ([Point(0, 0), Point(2, 0), Point(2, 3), Point(0, 3)], 6.0),
            ([Point(0, 0), Point(4, 0), Point(2, 2)], 4.0),
        ],
        ids=["2x3_rect", "triangle_base4_h2"],
    )
    def test_known_shapes(self, vertices: list[Point], expected: float) -> None:
        assert_approx(
            calculate_polygon_area(vertices), expected, f"area should be {expected}"
        )


# ---------------------------------------------------------------------------
# TestGetPillarPerpendicularRange
# ---------------------------------------------------------------------------


class TestGetPillarPerpendicularRange:
    """get_pillar_perpendicular_range returns the axis orthogonal to the given one."""

    def test_x_axis_returns_y_range(self, pillar: Pillar) -> None:
        result = get_pillar_perpendicular_range(pillar, Axis.X)
        assert result == (185.0, 215.0), "X axis should return y_range of pillar"

    def test_y_axis_returns_x_range(self, pillar: Pillar) -> None:
        result = get_pillar_perpendicular_range(pillar, Axis.Y)
        assert result == (90.0, 110.0), "Y axis should return x_range of pillar"


# ---------------------------------------------------------------------------
# TestGetPillarParallelExtent
# ---------------------------------------------------------------------------


class TestGetPillarParallelExtent:
    """get_pillar_parallel_extent returns the pillar size along the given axis."""

    def test_x_axis_returns_width(self, pillar: Pillar) -> None:
        assert get_pillar_parallel_extent(pillar, Axis.X) == 20, (
            "X axis should return the pillar width"
        )

    def test_y_axis_returns_depth(self, pillar: Pillar) -> None:
        assert get_pillar_parallel_extent(pillar, Axis.Y) == 30, (
            "Y axis should return the pillar depth"
        )


# ---------------------------------------------------------------------------
# TestEffectiveSpan
# ---------------------------------------------------------------------------


class TestEffectiveSpan:
    """effective_span = l0 + min(t1/2, 0.3h) + min(t2/2, 0.3h) (NBR 6118 §14.6.2.4)."""

    def test_narrow_supports_equal_centroid_distance(self) -> None:
        # t/2 = 5 < 0.3h = 15 on both sides -> l_ef == axis distance
        result = effective_span(400, 10, 10, 50)
        assert_approx(result, 400, "narrow supports should keep the centroid distance")

    def test_wide_supports_capped_at_0_3h(self) -> None:
        # l0 = 600 - 50 - 50 = 500; a = min(50, 12) = 12 on both sides
        result = effective_span(600, 100, 100, 40)
        assert_approx(result, 524, "wide supports should be capped at 0.3h")

    def test_mixed_supports(self) -> None:
        # l0 = 500 - 10 - 40 = 450; a1 = min(10, 9) = 9; a2 = min(40, 9) = 9
        result = effective_span(500, 20, 80, 30)
        assert_approx(result, 468, "each support should be capped independently")

    def test_half_width_governs_when_smaller(self) -> None:
        # l0 = 500 - 6 - 40 = 454; a1 = min(6, 9) = 6; a2 = min(40, 9) = 9
        result = effective_span(500, 12, 80, 30)
        assert_approx(result, 469, "t/2 should govern when below 0.3h")

    def test_non_positive_height_raises(self) -> None:
        with pytest.raises(ValueError, match="Height must be positive"):
            effective_span(400, 20, 20, 0)

    def test_overlapping_supports_raise(self) -> None:
        with pytest.raises(ValueError, match="no clear span"):
            effective_span(40, 40, 40, 30)
