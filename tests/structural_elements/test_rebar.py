"""Unit tests for the Rebar reinforcement bar dataclass."""

import pytest

from src.errors import InputError
from src.properties.steel import Steel
from src.structural_elements.rebar import HookGeometry, Rebar
from tests.helpers import assert_approx


@pytest.fixture
def rebar_ca50_10mm() -> Rebar:
    """Build a CA50 10 mm rebar for reuse across tests."""
    return Rebar(diameter_mm=10, steel=Steel.CA50)


class TestPostInit:
    """Tests for the diameter-availability validation in __post_init__."""

    def test_valid_diameter_constructs(self) -> None:
        rebar = Rebar(diameter_mm=10, steel=Steel.CA50)
        assert rebar.diameter_mm == 10, "A 10 mm bar is available for CA50"

    def test_invalid_diameter_raises(self) -> None:
        with pytest.raises(InputError, match="not available"):
            Rebar(diameter_mm=7.5, steel=Steel.CA50)


class TestEffectiveCovering:
    """Tests for the effective covering (max of bar diameter in cm and nominal)."""

    def test_diameter_governs(self, rebar_ca50_10mm: Rebar) -> None:
        expected_covering = 1.0  # cm (max(10/10, 0.5) -> bar diameter wins)
        assert rebar_ca50_10mm.effective_covering(0.5) == expected_covering, (
            "A 10 mm bar (1.0 cm) should govern over a 0.5 cm nominal cover"
        )

    def test_nominal_governs(self, rebar_ca50_10mm: Rebar) -> None:
        expected_covering = 2.0  # cm (max(10/10, 2.0) -> nominal cover wins)
        assert rebar_ca50_10mm.effective_covering(2.0) == expected_covering, (
            "A 2.0 cm nominal cover should govern over a 10 mm bar (1.0 cm)"
        )


class TestAreaCm2:
    """Tests for the rebar cross-sectional area."""

    def test_10mm_bar(self, rebar_ca50_10mm: Rebar) -> None:
        expected_area = 0.7853981633974483  # cm² (pi * 1.0² / 4)
        assert_approx(
            rebar_ca50_10mm.area_cm2,
            expected_area,
            "A 10 mm (1.0 cm) bar should have area pi/4 cm²",
        )


class TestStartEndPosition:
    """Tests for the start/end position derived from center and lengths."""

    def test_start_position(self, rebar_ca50_10mm: Rebar) -> None:
        rebar_ca50_10mm.center = 100.0
        rebar_ca50_10mm.left_length = 20.0
        expected_start = 80.0  # cm (100 - 20)
        assert rebar_ca50_10mm.start_position == expected_start, (
            "Start position should be center minus left length"
        )

    def test_end_position(self, rebar_ca50_10mm: Rebar) -> None:
        rebar_ca50_10mm.center = 100.0
        rebar_ca50_10mm.right_length = 30.0
        expected_end = 130.0  # cm (100 + 30)
        assert rebar_ca50_10mm.end_position == expected_end, (
            "End position should be center plus right length"
        )


class TestHookLength:
    """Tests for the 90° hook cut length, π(D + φ)/4 + 8φ − (D/2 + φ)."""

    def test_ca50_16mm(self) -> None:
        rebar = Rebar(diameter_mm=16, steel=Steel.CA50)
        expected_length = 14.739822368615503  # cm (D = 8: π·9.6/4 + 12.8 − 5.6)
        assert_approx(
            rebar.hook_length, expected_length, "CA-50 φ16 hook with a 5φ pin"
        )

    def test_ca50_20mm(self) -> None:
        rebar = Rebar(diameter_mm=20, steel=Steel.CA50)
        expected_length = 20.137166941154067  # cm (D = 16: π·18/4 + 16 − 10)
        assert_approx(
            rebar.hook_length, expected_length, "CA-50 φ20 hook with an 8φ pin"
        )

    def test_ca25_10mm(self) -> None:
        rebar = Rebar(diameter_mm=10, steel=Steel.CA25)
        expected_length = 8.926990816987241  # cm (D = 4: π·5/4 + 8 − 3)
        assert_approx(
            rebar.hook_length, expected_length, "CA-25 φ10 hook with a 4φ pin"
        )


class TestHookHeight:
    """Tests for the 90° hook height, D/2 + φ/2 + 8φ."""

    def test_ca50_16mm(self) -> None:
        rebar = Rebar(diameter_mm=16, steel=Steel.CA50)
        expected_height = 17.6  # cm (4 + 0.8 + 12.8)
        assert_approx(rebar.hook_height, expected_height, "CA-50 φ16 hook height")

    def test_ca50_20mm(self) -> None:
        rebar = Rebar(diameter_mm=20, steel=Steel.CA50)
        expected_height = 25.0  # cm (8 + 1 + 16)
        assert_approx(rebar.hook_height, expected_height, "CA-50 φ20 hook height")


class TestSideHookLength:
    """Tests for the per-side hook lengths, zero when the hook is disabled."""

    def test_disabled_hooks_are_zero(self, rebar_ca50_10mm: Rebar) -> None:
        assert rebar_ca50_10mm.left_hook_length == 0.0, "No left hook, no length"
        assert rebar_ca50_10mm.right_hook_length == 0.0, "No right hook, no length"

    def test_enabled_hook_uses_hook_length(self, rebar_ca50_10mm: Rebar) -> None:
        rebar_ca50_10mm.left_hook_enabled = True
        assert_approx(
            rebar_ca50_10mm.left_hook_length,
            rebar_ca50_10mm.hook_length,
            "An enabled left hook adds the hook length",
        )
        assert rebar_ca50_10mm.right_hook_length == 0.0, (
            "The right side stays without a hook"
        )

    def test_side_geometry_replaces_standard_hook(self) -> None:
        rebar = Rebar(diameter_mm=16, steel=Steel.CA50)
        rebar.left_hook_enabled = True
        rebar.left_hook_geometry = HookGeometry(pin_diameter=24.0, tip_length=40.0)
        expected_length = 46.506192982974675  # cm (π·25.6/4 + 40 − 13.6)
        assert_approx(
            rebar.left_hook_length,
            expected_length,
            "The left hook uses its own D = 15φ and 40 cm tip",
        )
        assert_approx(
            rebar.hook_length,
            14.739822368615503,
            "The standard hook length does not change",
        )

    def test_side_geometry_ignored_when_disabled(self) -> None:
        rebar = Rebar(diameter_mm=16, steel=Steel.CA50)
        rebar.right_hook_geometry = HookGeometry(pin_diameter=24.0, tip_length=40.0)
        assert rebar.right_hook_length == 0.0, "No right hook, no length"


class TestHookGeometry:
    """Tests for the per-side hook geometry, None when the hook is disabled."""

    def test_disabled_hook_is_none(self, rebar_ca50_10mm: Rebar) -> None:
        assert rebar_ca50_10mm.hook_geometry(left=True) is None, "No left hook"

    def test_enabled_hook_without_geometry_is_standard(
        self, rebar_ca50_10mm: Rebar
    ) -> None:
        rebar_ca50_10mm.right_hook_enabled = True
        expected = HookGeometry(pin_diameter=5.0, tip_length=8.0)  # cm (5φ, 8φ)
        assert rebar_ca50_10mm.hook_geometry(left=False) == expected, (
            "A plain hook is the standard CA-50 φ10 hook"
        )

    def test_enabled_hook_keeps_side_geometry(self) -> None:
        rebar = Rebar(diameter_mm=16, steel=Steel.CA50)
        geometry = HookGeometry(pin_diameter=24.0, tip_length=40.0)
        rebar.left_hook_enabled = True
        rebar.left_hook_geometry = geometry
        assert rebar.hook_geometry(left=True) == geometry, (
            "The left side keeps its own frame-joint geometry"
        )

    def test_disabled_hook_ignores_side_geometry(self) -> None:
        rebar = Rebar(diameter_mm=16, steel=Steel.CA50)
        rebar.left_hook_geometry = HookGeometry(pin_diameter=24.0, tip_length=40.0)
        assert rebar.hook_geometry(left=True) is None, (
            "Geometry without an enabled hook is not a hook"
        )


class TestTotalLength:
    """Tests for the bar's cut length: straight lengths plus enabled hooks."""

    def test_without_hooks(self, rebar_ca50_10mm: Rebar) -> None:
        rebar_ca50_10mm.left_length = 40.0
        rebar_ca50_10mm.right_length = 60.0
        expected_length = 100.0  # cm (40 + 60)
        assert_approx(
            rebar_ca50_10mm.total_length, expected_length, "Straight lengths only"
        )

    def test_with_right_hook(self, rebar_ca50_10mm: Rebar) -> None:
        rebar_ca50_10mm.left_length = 40.0
        rebar_ca50_10mm.right_length = 60.0
        rebar_ca50_10mm.right_hook_enabled = True
        expected_length = 109.21238898038469  # cm (100 + π·6/4 + 8 − 3.5)
        assert_approx(
            rebar_ca50_10mm.total_length,
            expected_length,
            "Straight lengths plus the right hook",
        )

    def test_with_right_side_geometry(self, rebar_ca50_10mm: Rebar) -> None:
        rebar_ca50_10mm.left_length = 40.0
        rebar_ca50_10mm.right_length = 60.0
        rebar_ca50_10mm.right_hook_enabled = True
        rebar_ca50_10mm.right_hook_geometry = HookGeometry(
            pin_diameter=15.0, tip_length=30.0
        )
        expected_length = 134.0663706143592  # cm (100 + π·16/4 + 30 − 8.5)
        assert_approx(
            rebar_ca50_10mm.total_length,
            expected_length,
            "Straight lengths plus the right hook with its own geometry",
        )
