"""Tests for src/pavement_elements/pillar.py."""

import pytest

from src.config import APP_CONFIG
from src.pavement_elements.geometry_utils import Axis
from src.pavement_elements.pillar import Pillar
from src.properties.concrete import Concrete
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


class TestExplicitId:
    """An explicit id replaces the counter-generated one."""

    def test_explicit_id_is_kept(self) -> None:
        p = Pillar(0, 0, 20, 30, id="P1")
        assert p.id == "P1", "an explicit id should be kept"

    def test_explicit_id_does_not_advance_counter(self) -> None:
        before = Pillar(0, 0, 20, 30)
        Pillar(0, 0, 20, 30, id="P_explicit")
        after = Pillar(0, 0, 20, 30)
        assert int(after.id[1:]) == int(before.id[1:]) + 1, (
            "an explicit id should not consume a counter number"
        )


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


# ---------------------------------------------------------------------------
# TestExtents
# ---------------------------------------------------------------------------


@pytest.fixture
def pillar() -> Pillar:
    """Return a 20 (x) × 30 (y) cm pillar."""
    return Pillar(x=0, y=0, width=20, depth=30)


class TestExtents:
    """Extents along and across a beam axis."""

    def test_parallel_extent_x_beam(self, pillar: Pillar) -> None:
        assert pillar.get_parallel_extent(Axis.X) == 20, (
            "Along an X beam the parallel extent is the width (cm)"
        )

    def test_parallel_extent_y_beam(self, pillar: Pillar) -> None:
        assert pillar.get_parallel_extent(Axis.Y) == 30, (
            "Along a Y beam the parallel extent is the depth (cm)"
        )

    def test_perpendicular_extent_x_beam(self, pillar: Pillar) -> None:
        assert pillar.get_perpendicular_extent(Axis.X) == 30, (
            "Across an X beam the perpendicular extent is the depth (cm)"
        )

    def test_perpendicular_extent_y_beam(self, pillar: Pillar) -> None:
        assert pillar.get_perpendicular_extent(Axis.Y) == 20, (
            "Across a Y beam the perpendicular extent is the width (cm)"
        )


# ---------------------------------------------------------------------------
# TestCalculateStiffness
# ---------------------------------------------------------------------------


def _expected_stiffness(
    inertia_cm4: float, concrete: Concrete, height_m: float
) -> float:
    """Return 2·3·Ecs·Ic/(l/2) in kN.m/rad from Ic (cm⁴), Ecs (MPa) and l (m)."""
    return 2 * 3 * concrete.ecs * 1e3 * inertia_cm4 * 1e-8 / (height_m / 2)


@pytest.fixture(autouse=True)
def pinned_concrete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the project concrete to C25 for every test in this module"""
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C25)


class TestCalculateStiffness:
    """Rotational stiffness k = 2·3·Ec·Ic/(l/2) given to a beam by a pillar."""

    def test_x_beam_cubes_width(
        self, pillar: Pillar, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """X beam: Ic = depth·width³/12 = 30·20³/12 = 20 000 cm⁴ (kN.m/rad)."""
        monkeypatch.setattr(APP_CONFIG, "ceiling_height", 2.5)
        expected = _expected_stiffness(30 * 20**3 / 12, Concrete.C25, 2.5)
        assert_approx(
            pillar.calculate_stiffness_for_beam_supporting(Axis.X),
            expected,
            "X-beam stiffness should cube the width (kN.m/rad)",
        )

    def test_y_beam_cubes_depth(
        self, pillar: Pillar, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Y beam: Ic = width·depth³/12 = 20·30³/12 = 45 000 cm⁴ (kN.m/rad)."""
        monkeypatch.setattr(APP_CONFIG, "ceiling_height", 2.5)
        expected = _expected_stiffness(20 * 30**3 / 12, Concrete.C25, 2.5)
        assert_approx(
            pillar.calculate_stiffness_for_beam_supporting(Axis.Y),
            expected,
            "Y-beam stiffness should cube the depth (kN.m/rad)",
        )

    def test_doubling_ceiling_height_halves_stiffness(
        self, pillar: Pillar, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """k is inversely proportional to the ceiling height (kN.m/rad)."""
        monkeypatch.setattr(APP_CONFIG, "ceiling_height", 2.5)
        reference = pillar.calculate_stiffness_for_beam_supporting(Axis.X)
        monkeypatch.setattr(APP_CONFIG, "ceiling_height", 5.0)
        assert_approx(
            pillar.calculate_stiffness_for_beam_supporting(Axis.X),
            reference / 2,
            "Doubling the ceiling height should halve the stiffness (kN.m/rad)",
        )

    def test_stiffness_follows_concrete_modulus(
        self, pillar: Pillar, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """k scales with the project concrete's secant modulus Ecs (kN.m/rad)."""
        monkeypatch.setattr(APP_CONFIG, "ceiling_height", 2.5)
        c25 = pillar.calculate_stiffness_for_beam_supporting(Axis.X)
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C40)
        c40 = pillar.calculate_stiffness_for_beam_supporting(Axis.X)
        assert_approx(
            c40 / c25,
            Concrete.C40.ecs / Concrete.C25.ecs,
            "Stiffness ratio should equal the Ecs ratio",
        )


class TestIsRigidInnerSupport:
    """NBR 6118:2026 14.6.6.1-b — interior support rigid when b_int > e/4, e = ceiling height."""

    def test_wide_pillar_is_rigid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """b_int = 70 cm > e/4 = 62.5 cm (H = 2.5 m)."""
        monkeypatch.setattr(APP_CONFIG, "ceiling_height", 2.5)
        pillar = Pillar(x=0, y=0, width=70, depth=20)
        assert pillar.is_rigid_inner_support(Axis.X), "70 cm > 62.5 cm is rigid"

    def test_width_equal_to_limit_is_elastic(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """b_int = e/4 = 62.5 cm is not "greater than" a quarter of the height."""
        monkeypatch.setattr(APP_CONFIG, "ceiling_height", 2.5)
        pillar = Pillar(x=0, y=0, width=62.5, depth=20)
        assert not pillar.is_rigid_inner_support(Axis.X), "b_int = e/4 is elastic"

    def test_uses_extent_along_the_beam(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A 70×20 pillar is rigid for an X beam (b_int = 70) but not a Y beam (b_int = 20)."""
        monkeypatch.setattr(APP_CONFIG, "ceiling_height", 2.5)
        pillar = Pillar(x=0, y=0, width=70, depth=20)
        assert pillar.is_rigid_inner_support(Axis.X), "X beam reads the width"
        assert not pillar.is_rigid_inner_support(Axis.Y), "Y beam reads the depth"

    def test_follows_ceiling_height(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """b_int = 70 cm is rigid with H = 2.5 m (e/4 = 62.5) but not H = 3.0 m (e/4 = 75)."""
        pillar = Pillar(x=0, y=0, width=70, depth=20)
        monkeypatch.setattr(APP_CONFIG, "ceiling_height", 2.5)
        assert pillar.is_rigid_inner_support(Axis.X), "rigid with H = 2.5 m"
        monkeypatch.setattr(APP_CONFIG, "ceiling_height", 3.0)
        assert not pillar.is_rigid_inner_support(Axis.X), "elastic with H = 3.0 m"
