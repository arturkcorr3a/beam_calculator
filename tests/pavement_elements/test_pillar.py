"""Tests for src/pavement_elements/pillar.py."""

import pytest

from src.pavement_elements.pillar import Pillar
from tests.helpers import assert_approx

# ---------------------------------------------------------------------------
# TestConstruction
# ---------------------------------------------------------------------------


class TestConstruction:
    """Pillar constructs successfully for valid inputs."""

    def test_valid_pillar_constructs(self) -> None:
        p = Pillar(x=0, y=0, width=20, depth=30)
        assert p.x == 0, "x should be stored"
        assert p.y == 0, "y should be stored"
        assert p.width == 20, "width should be stored"
        assert p.depth == 30, "depth should be stored"

    def test_id_starts_with_P(self) -> None:
        p = Pillar(x=0, y=0, width=20, depth=20)
        assert p.id.startswith("P"), "auto-generated id must start with 'P'"


# ---------------------------------------------------------------------------
# TestGetRange
# ---------------------------------------------------------------------------


class TestGetRange:
    """get_x_range and get_y_range return centred half-width intervals."""

    def test_x_range(self) -> None:
        p = Pillar(x=0, y=0, width=20, depth=30)
        lo, hi = p.get_x_range()
        assert_approx(lo, -10.0, "x_range low should be x - width/2")
        assert_approx(hi, 10.0, "x_range high should be x + width/2")

    def test_y_range(self) -> None:
        p = Pillar(x=0, y=0, width=20, depth=30)
        lo, hi = p.get_y_range()
        assert_approx(lo, -15.0, "y_range low should be y - depth/2")
        assert_approx(hi, 15.0, "y_range high should be y + depth/2")

    def test_x_range_non_zero_origin(self) -> None:
        p = Pillar(x=100, y=200, width=20, depth=30)
        lo, hi = p.get_x_range()
        assert_approx(lo, 90.0, "x_range low should be 100 - 10")
        assert_approx(hi, 110.0, "x_range high should be 100 + 10")

    def test_y_range_non_zero_origin(self) -> None:
        p = Pillar(x=100, y=200, width=20, depth=30)
        lo, hi = p.get_y_range()
        assert_approx(lo, 185.0, "y_range low should be 200 - 15")
        assert_approx(hi, 215.0, "y_range high should be 200 + 15")


# ---------------------------------------------------------------------------
# TestValidateDimensions
# ---------------------------------------------------------------------------


class TestValidateDimensions:
    """Pillar raises ValueError for dimensions below the minimum requirements."""

    def test_width_below_14_raises(self) -> None:
        with pytest.raises(ValueError, match="must be at least 14.0 cm"):
            Pillar(x=0, y=0, width=13, depth=20)

    def test_depth_below_14_raises(self) -> None:
        with pytest.raises(ValueError, match="must be at least 14.0 cm"):
            Pillar(x=0, y=0, width=20, depth=13)

    def test_14x14_fails_area_check(self) -> None:
        # 14×14 = 196 cm² < 360 cm² (passes dimension but fails area)
        with pytest.raises(ValueError, match="gross area must be at least"):
            Pillar(x=0, y=0, width=14, depth=14)

    def test_20x20_valid(self) -> None:
        # should not raise
        Pillar(x=0, y=0, width=20, depth=20)

    def test_area_below_minimum_raises(self) -> None:
        # 14×25 = 350 cm² < 360 cm²
        with pytest.raises(ValueError, match="gross area must be at least"):
            Pillar(x=0, y=0, width=14, depth=25)
