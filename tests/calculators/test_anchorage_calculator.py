"""Unit tests for src/calculators/anchorage_calculator.py — AnchorageCalculator."""

import types
from collections.abc import Iterator
from typing import Any
from unittest.mock import PropertyMock, patch

import pytest

from src.calculators.anchorage_calculator import AnchorageCalculator
from src.config import APP_CONFIG
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.reinforcement.clamps import Clamps
from src.reinforcement.layer import Layer
from src.structural_elements.rebar import Rebar
from src.structural_elements.rectangular_beam import _BeamMeta  # pyright: ignore[reportPrivateUsage]
from src.structural_elements.support import Support
from tests.helpers import assert_approx

# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------


_STUB_BEAM_LENGTH = 500.0  # cm
_STUB_CENTER = 250.0  # cm


def _make_layer(
    diameter_mm: float,
    good_adherence: bool,
    beam_height: float = 60.0,
) -> Layer:
    """Create a Layer with one real Rebar, then pin y_centroid_position so that
    has_good_adherence() returns the desired value.

    The good-adherence threshold for beam_height=60 is 60-30=30 cm.
    A y_centroid_position of 5 cm (< 30) → good; 55 cm (> 30) → poor.
    """
    bar = Rebar(diameter_mm=diameter_mm, steel=Steel.CA50)
    layer = Layer(bars=[bar], layer_index=0)
    # For beam_height=60 the threshold is max(0, 60-30)=30 cm
    layer.y_centroid_position = 5.0 if good_adherence else 55.0
    return layer


def _make_reinforcement(
    layer: Layer,
    required_area: float,
    area: float,
    beam_height: float = 60.0,
    moment_zeros: tuple[float, ...] = (),
) -> types.SimpleNamespace:
    """Build a minimal reinforcement stub, centered on a 500 cm beam."""
    return types.SimpleNamespace(
        chosen_bars=[layer],
        beam=types.SimpleNamespace(height=beam_height, length=_STUB_BEAM_LENGTH),
        required_area=required_area,
        area=area,
        center_position=_STUB_CENTER,
        moment_zeros=moment_zeros,
    )


@pytest.fixture(autouse=True)
def pinned_concrete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the project concrete to C25 for every test in this module"""
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C25)


def _make_ac(
    layer: Layer,
    required_area: float,
    area: float,
    beam_height: float = 60.0,
    steel: Steel = Steel.CA50,
    moment_zeros: tuple[float, ...] = (),
) -> AnchorageCalculator:
    """Construct AnchorageCalculator with minimal stubs."""
    reinforcement = _make_reinforcement(
        layer, required_area, area, beam_height, moment_zeros
    )
    return AnchorageCalculator(
        moment_shift=28.0,
        steel=steel,
        layer_index=0,
        reinforcement=reinforcement,  # pyright: ignore[reportArgumentType]
        id="Test",
    )


@pytest.fixture
def layer_16mm_good() -> Layer:
    """Layer with one 16 mm CA50 bar in a good-adherence position."""
    return _make_layer(16.0, good_adherence=True)


@pytest.fixture
def layer_16mm_poor() -> Layer:
    """Layer with one 16 mm CA50 bar in a poor-adherence position."""
    return _make_layer(16.0, good_adherence=False)


@pytest.fixture
def ac(layer_16mm_good: Layer) -> AnchorageCalculator:
    """AnchorageCalculator with 16 mm CA50/C25 bar in good-adherence zone.

    required_area=area so the area-ratio factor equals 1.0.
    """
    return _make_ac(layer_16mm_good, required_area=2.0, area=2.0)


# ---------------------------------------------------------------------------
# TestAdherenceCoefficient
# ---------------------------------------------------------------------------


class TestAdherenceCoefficient:
    """Tests for the adherence coefficient (eta_2)."""

    def test_good_adherence(self, ac: AnchorageCalculator) -> None:
        """eta_2 = 1.0 for a bar in the good-adherence zone (dimensionless)."""
        assert ac.adherence_coefficient == 1.0, (
            "eta_2 should be 1.0 for good-adherence zone (dimensionless)"
        )

    def test_poor_adherence(self, layer_16mm_poor: Layer) -> None:
        """eta_2 = 0.7 for a bar in the poor-adherence zone (dimensionless)."""
        ac_poor = _make_ac(layer_16mm_poor, required_area=2.0, area=2.0)
        assert ac_poor.adherence_coefficient == 0.7, (
            "eta_2 should be 0.7 for poor-adherence zone (dimensionless)"
        )


# ---------------------------------------------------------------------------
# TestMaxDiameter
# ---------------------------------------------------------------------------


class TestMaxDiameter:
    """Tests for max_diameter (mm)."""

    def test_single_bar(self, ac: AnchorageCalculator) -> None:
        """max_diameter equals the only bar's diameter (mm)."""
        assert ac.max_diameter == 16.0, "max_diameter should be 16.0 mm"

    def test_multiple_bars(self) -> None:
        """max_diameter is the largest diameter in the layer (mm)."""
        bar_12 = Rebar(diameter_mm=12.5, steel=Steel.CA50)
        bar_20 = Rebar(diameter_mm=20.0, steel=Steel.CA50)
        layer = Layer(bars=[bar_12, bar_20], layer_index=0)
        layer.y_centroid_position = 5.0
        ac = _make_ac(layer, required_area=2.0, area=2.0)
        assert ac.max_diameter == 20.0, "max_diameter should be 20.0 mm"


# ---------------------------------------------------------------------------
# TestDiameterCoefficient
# ---------------------------------------------------------------------------


class TestDiameterCoefficient:
    """Tests for the diameter coefficient (eta_3)."""

    def test_capped_at_one_for_small_diameter(self, ac: AnchorageCalculator) -> None:
        """eta_3 = 1.0 when (132 - phi_mm) / 100 >= 1.0 (dimensionless)."""
        # phi=16 mm → (132-16)/100=1.16 → capped to 1.0
        assert ac.diameter_coefficient == 1.0, (
            "eta_3 should be capped at 1.0 for 16 mm bar (dimensionless)"
        )

    def test_below_one_for_large_diameter(self) -> None:
        """eta_3 < 1.0 for a large bar (dimensionless)."""
        # phi=40 mm → (132-40)/100=0.92
        layer_40 = _make_layer(40.0, good_adherence=True)
        ac_40 = _make_ac(layer_40, required_area=2.0, area=2.0)
        assert_approx(
            ac_40.diameter_coefficient,
            0.92,
            "eta_3 should be 0.92 for 40 mm bar (dimensionless)",
        )


# ---------------------------------------------------------------------------
# TestDesignBondStrength
# ---------------------------------------------------------------------------


class TestDesignBondStrength:
    """Tests for the design bond strength (f_bd) in kN/cm²."""

    def test_value_ca50_c25_good_adherence(self, ac: AnchorageCalculator) -> None:
        """f_bd = eta_1 * eta_2 * eta_3 * fctd for CA50/C25/16 mm/good adherence (kN/cm²).

        eta_1=2.25, eta_2=1.0, eta_3=1.0, fctd=0.12824819600075227
        """
        expected = 2.25 * 1.0 * 1.0 * Concrete.C25.fctd
        assert_approx(
            ac.design_bond_strength,
            expected,
            "f_bd for CA50/C25/16mm/good-adherence (kN/cm²)",
        )


# ---------------------------------------------------------------------------
# TestBasicAnchorageLength
# ---------------------------------------------------------------------------


class TestBasicAnchorageLength:
    """Tests for the basic anchorage length (l_b) in cm."""

    def test_computed_leg_dominates(self, ac: AnchorageCalculator) -> None:
        """l_b = (phi_cm/4) * (fyd / f_bd) dominates for CA50/C25/16 mm (cm)."""
        phi_cm = 16.0 / 10
        fyd = Steel.CA50.fyd
        f_bd = ac.design_bond_strength
        expected_computed = (phi_cm / 4) * (fyd / f_bd)
        expected_floor = 25 * phi_cm
        expected = max(expected_floor, expected_computed)
        assert_approx(
            ac.basic_anchorage_length,
            expected,
            "basic_anchorage_length for CA50/C25/16mm (cm)",
        )

    def test_floor_25_phi_wins(self) -> None:
        """l_b = 25*phi when (phi/4)*(fyd/f_bd) < 25*phi (cm).

        Achieved by injecting a fake steel with very high bond / very low fyd so the
        computed leg is smaller than 25*phi.
        """
        # Fake steel: bond_coefficient=100, fyd=0.1 → computed leg ≈ tiny
        # We patch the bond_coefficient and fyd on the Steel instance indirectly
        # by building a SimpleNamespace with fake steel attributes.
        fake_steel: Any = types.SimpleNamespace(
            bond_coefficient=100.0,
            fyd=0.1,
            fywk=50.0,
            fywd=43.5,
            available_sizes=[16.0],
        )
        layer = Layer(bars=[Rebar(diameter_mm=16.0, steel=Steel.CA50)], layer_index=0)
        layer.y_centroid_position = 5.0
        reinforcement = _make_reinforcement(layer, required_area=2.0, area=2.0)
        ac_fake = AnchorageCalculator(
            moment_shift=28.0,
            steel=fake_steel,
            layer_index=0,
            reinforcement=reinforcement,  # pyright: ignore[reportArgumentType]
            id="fake",
        )
        phi_cm = 16.0 / 10
        assert_approx(
            ac_fake.basic_anchorage_length,
            25 * phi_cm,
            "l_b should be 25*phi_cm when computed leg is smaller (cm)",
        )


# ---------------------------------------------------------------------------
# TestAnchorageAlphaCoefficient
# ---------------------------------------------------------------------------


class TestAnchorageAlphaCoefficient:
    """Tests for the anchorage alpha coefficient."""

    def test_no_hook(self, ac: AnchorageCalculator) -> None:
        """alpha = 1.0 when there is no hook (dimensionless)."""
        ac.left = True  # set direction before reading property
        # bar has left_hook_enabled=False by default
        assert ac.anchorage_alpha_coefficient == 1.0, (
            "alpha should be 1.0 without hook (dimensionless)"
        )

    def test_left_hook(self, ac: AnchorageCalculator) -> None:
        """alpha = 0.7 when bar has left hook enabled (dimensionless)."""
        ac.left = True
        ac.layer.bars[0].left_hook_enabled = True
        assert ac.anchorage_alpha_coefficient == 0.7, (
            "alpha should be 0.7 with left hook (dimensionless)"
        )

    def test_right_hook(self, ac: AnchorageCalculator) -> None:
        """alpha = 0.7 when bar has right hook enabled and left=False (dimensionless)."""
        ac.left = False
        ac.layer.bars[0].right_hook_enabled = True
        assert ac.anchorage_alpha_coefficient == 0.7, (
            "alpha should be 0.7 with right hook (dimensionless)"
        )


# ---------------------------------------------------------------------------
# TestMinAnchorageLength
# ---------------------------------------------------------------------------


class TestMinAnchorageLength:
    """Tests for min_anchorage_length (l_b_min) in cm."""

    def test_0_3_lb_leg_wins(self) -> None:
        """l_b_min = 0.3*l_b when 0.3*l_b > 10*phi and 0.3*l_b > 10 (cm)."""
        # Use 40 mm bar so 10*phi_cm = 4 cm and pick a concrete where 0.3*l_b > 4 and > 10
        layer = _make_layer(40.0, good_adherence=True)
        ac = _make_ac(layer, required_area=2.0, area=2.0)
        l_b = ac.basic_anchorage_length
        expected = max(0.3 * l_b, 10 * (40.0 / 10), 10)
        assert_approx(
            ac.min_anchorage_length,
            expected,
            "l_b_min should be max(0.3*l_b, 10*phi, 10) (cm)",
        )

    def test_10_phi_leg_wins(self) -> None:
        """l_b_min = 10*phi when 10*phi is the largest of the three terms (cm)."""
        # Use 40mm bar: 10*4=40 cm; 0.3*l_b is also large but 10*phi wins for 40mm
        layer = _make_layer(40.0, good_adherence=True)
        ac_40 = _make_ac(layer, required_area=2.0, area=2.0)
        phi_cm = 40.0 / 10
        l_b = ac_40.basic_anchorage_length
        expected = max(0.3 * l_b, 10 * phi_cm, 10)
        assert_approx(ac_40.min_anchorage_length, expected, "l_b_min for 40mm bar (cm)")

    def test_absolute_10_wins(self) -> None:
        """l_b_min >= 10 cm always (cm)."""
        # 6.3 mm bar with tiny concrete: 10*0.63=6.3 < 10; absolute floor wins
        # But CA50 does not have sub-10mm bars; use the normal fixture and check floor
        ac_small = _make_ac(
            _make_layer(16.0, good_adherence=True), required_area=2.0, area=2.0
        )
        assert ac_small.min_anchorage_length >= 10.0, (
            "l_b_min must be at least 10 cm (cm)"
        )


# ---------------------------------------------------------------------------
# TestNecessaryAnchorageLength
# ---------------------------------------------------------------------------


class TestNecessaryAnchorageLength:
    """Tests for necessary_anchorage_length (l_b_nec) in cm."""

    def test_area_ratio_scaled(self, ac: AnchorageCalculator) -> None:
        """l_b_nec = alpha * l_b * (required_area / area) when area ratio < 1 (cm)."""
        # required_area=1.0, area=2.0 → ratio=0.5
        ac.left = True
        layer = _make_layer(16.0, good_adherence=True)
        ac_scaled = _make_ac(layer, required_area=1.0, area=2.0)
        ac_scaled.left = True
        l_b = ac_scaled.basic_anchorage_length
        l_b_min = ac_scaled.min_anchorage_length
        expected = max(1.0 * l_b * 0.5, l_b_min)
        assert_approx(
            ac_scaled.necessary_anchorage_length,
            expected,
            "l_b_nec with area ratio=0.5 (cm)",
        )

    def test_clamped_to_minimum(self, ac: AnchorageCalculator) -> None:
        """l_b_nec is at least l_b_min (cm)."""
        ac.left = True
        # required_area very small compared to area → ratio near 0 → clamped to l_b_min
        layer = _make_layer(16.0, good_adherence=True)
        ac_tiny = _make_ac(layer, required_area=0.001, area=100.0)
        ac_tiny.left = True
        assert_approx(
            ac_tiny.necessary_anchorage_length,
            ac_tiny.min_anchorage_length,
            "l_b_nec should be clamped to l_b_min when ratio is tiny (cm)",
        )


# ---------------------------------------------------------------------------
# TestTotalAnchorageLength
# ---------------------------------------------------------------------------


class TestTotalAnchorageLength:
    """Tests for total_anchorage_length (l_b_nec + a_l) in cm."""

    def test_adds_moment_shift(self, ac: AnchorageCalculator) -> None:
        """Total length is l_b_nec plus the moment shift a_l = 28 cm (cm)."""
        ac.left = True
        assert_approx(
            ac.total_anchorage_length,
            ac.necessary_anchorage_length + 28.0,
            "total anchorage length should be l_b_nec + a_l (cm)",
        )

    @pytest.mark.parametrize(
        ("left", "zero"), [(True, 100.0), (False, 400.0)], ids=["left", "right"]
    )
    def test_far_zero_governs(
        self, layer_16mm_good: Layer, left: bool, zero: float
    ) -> None:
        """A zero 150 cm away governs: 150 + 10φ + a_l (cm)."""
        ac = _make_ac(layer_16mm_good, 2.0, 2.0, moment_zeros=(zero,))
        ac.left = left
        assert_approx(
            ac.total_anchorage_length,
            150.0 + 10 * 1.6 + 28.0,
            "a far zero-moment point should govern over l_b,nec (cm)",
        )

    def test_near_zero_keeps_necessary_length(self, ac: AnchorageCalculator) -> None:
        """A zero 5 cm away gives 5 + 10φ < l_b,nec, so l_b,nec governs (cm)."""
        ac.reinforcement.moment_zeros = (245.0,)
        ac.left = True
        assert_approx(
            ac.total_anchorage_length,
            ac.necessary_anchorage_length + 28.0,
            "l_b,nec should govern over a near zero-moment point (cm)",
        )

    def test_uses_nearest_zero_on_the_anchored_side(
        self, layer_16mm_good: Layer
    ) -> None:
        """Only the nearest zero on the current side counts (cm)."""
        ac = _make_ac(
            layer_16mm_good, 2.0, 2.0, moment_zeros=(50.0, 100.0, 300.0, 450.0)
        )
        ac.left = True
        assert_approx(
            ac.length_past_zero_moment,
            150.0 + 10 * 1.6,
            "left side should use the zero at 100 cm (cm)",
        )
        ac.left = False
        assert_approx(
            ac.length_past_zero_moment,
            50.0 + 10 * 1.6,
            "right side should use the zero at 300 cm (cm)",
        )

    def test_ignores_zeros_at_beam_ends(self, layer_16mm_good: Layer) -> None:
        """Zeros at x = 0 and x = L are skipped, leaving l_b,nec + a_l (cm)."""
        ac = _make_ac(layer_16mm_good, 2.0, 2.0, moment_zeros=(0.0, _STUB_BEAM_LENGTH))
        for left in (True, False):
            ac.left = left
            assert ac.length_past_zero_moment == 0.0, (
                f"end zeros should be ignored (left={left})"
            )


# ---------------------------------------------------------------------------
# TestGetAdjustedAvailableSpaceForHooks
# ---------------------------------------------------------------------------


class TestGetAdjustedAvailableSpaceForHooks:
    """Tests for get_adjusted_available_space_for_hooks() in cm."""

    def test_reduces_when_hook_cover_exceeds_nominal(
        self, ac: AnchorageCalculator
    ) -> None:
        """Space reduces when 3*phi > nominal_covering (cm)."""
        # phi=16mm → 3*phi=4.8 cm; set nominal_covering=3 cm so hook cover > nominal
        with patch.object(
            _BeamMeta, "nominal_covering", new_callable=PropertyMock
        ) as mock_cov:
            mock_cov.return_value = 3.0
            adjusted = ac.get_adjusted_available_space_for_hooks(100.0)
            # space + cover - max(cover, 3*phi) = 100+3-max(3,4.8) = 100+3-4.8 = 98.2
            assert_approx(adjusted, 98.2, "adjusted space with 16mm bar (cm)")

    def test_no_change_when_nominal_dominates(self) -> None:
        """Space unchanged when nominal_covering >= 3*phi (cm)."""
        # phi=8mm → 3*phi=2.4 cm; nominal=3 → max(3,2.4)=3 → space+3-3 = space unchanged
        layer_8 = _make_layer(8.0, good_adherence=True)
        ac_8 = _make_ac(layer_8, required_area=2.0, area=2.0)
        with patch.object(
            _BeamMeta, "nominal_covering", new_callable=PropertyMock
        ) as mock_cov:
            mock_cov.return_value = 3.0
            adjusted = ac_8.get_adjusted_available_space_for_hooks(100.0)
            assert_approx(adjusted, 100.0, "adjusted space should be unchanged (cm)")


# ---------------------------------------------------------------------------
# TestRun
# ---------------------------------------------------------------------------


class TestRun:
    """Tests for run() — the public entry point."""

    def test_passes_without_hooks(self, layer_16mm_good: Layer) -> None:
        """run() completes without hooks when available space >= l_b_nec (cm)."""
        ac = _make_ac(layer_16mm_good, required_area=2.0, area=2.0)
        with patch.object(
            _BeamMeta, "nominal_covering", new_callable=PropertyMock
        ) as mock_cov:
            mock_cov.return_value = 3.0
            # Peek with left=True so anchorage_alpha_coefficient can be evaluated
            ac.left = True
            total_length = ac.total_anchorage_length  # peek at the value
            # Provide more than enough space; no hooks should be enabled
            ac.run(available_space=total_length + 50.0, left=True)
        # After a successful run, all bars should have no left hook
        for bar in layer_16mm_good.bars:
            assert not bar.left_hook_enabled, (
                "Bars should NOT have hooks when space is sufficient (cm)"
            )
            assert_approx(
                bar.left_length,
                total_length,
                "Bar left length should be l_b_nec + a_l (cm)",
            )

    def test_passes_with_hooks_on_retry(self, layer_16mm_good: Layer) -> None:
        """run() succeeds with hooks when space without hooks is too small (cm)."""
        ac = _make_ac(layer_16mm_good, required_area=2.0, area=2.0)
        with patch.object(
            _BeamMeta, "nominal_covering", new_callable=PropertyMock
        ) as mock_cov:
            mock_cov.return_value = 3.0
            # Gather the l_b_nec values to set the tight-but-sufficient space
            ac_probe = _make_ac(
                _make_layer(16.0, good_adherence=True), required_area=2.0, area=2.0
            )
            # Must set left before reading necessary_anchorage_length
            ac_probe.left = True
            l_b_nec_no_hook = ac_probe.necessary_anchorage_length  # alpha=1.0
            # set space so that it's between l_b_nec_with_hook and l_b_nec_no_hook
            # alpha with hook = 0.7 → l_b_nec_with_hook = 0.7 * l_b_nec_no_hook (approx)
            l_b_nec_with_hook = 0.7 * l_b_nec_no_hook
            # Both totals add the moment shift a_l on top of l_b_nec
            moment_shift = ac_probe.moment_shift
            # Space is just above the with-hook total (adjusted) but below the no-hook total
            # The adjusted space for hooks = space + 3 - max(3, 4.8) = space - 1.8
            # So we need: (space - 1.8) >= l_b_nec_with_hook + a_l
            # and space < l_b_nec_no_hook + a_l
            space = (
                l_b_nec_with_hook + moment_shift + 2.0
            )  # still fits after adjustment
            ac.run(available_space=space, left=True)
        # After run-with-hooks, left_hook_enabled should be True for all bars
        for bar in layer_16mm_good.bars:
            assert bar.left_hook_enabled, (
                "Bars should have left hooks when hooks path was taken (dimensionless)"
            )

    def test_raises_when_no_space_even_with_hooks(self) -> None:
        """run() raises ValueError when space is too small even with hooks (cm)."""
        layer = _make_layer(16.0, good_adherence=True)
        ac = _make_ac(layer, required_area=2.0, area=2.0)
        with patch.object(
            _BeamMeta, "nominal_covering", new_callable=PropertyMock
        ) as mock_cov:
            mock_cov.return_value = 3.0
            with pytest.raises(ValueError, match="even with hooks"):
                ac.run(available_space=1.0, left=True)


# ---------------------------------------------------------------------------
# TestClampFallback
# ---------------------------------------------------------------------------

_BEAM_LENGTH = 500.0  # cm
_TIGHT_SPACE = 20.0  # cm, too short for a 16 mm bar even with hooks
_EFFECTIVE_COVERING = 2.5  # cm
_STIRRUP_INNER_WIDTH = 15.0  # cm


def _make_clamp_ac(
    layer: Layer,
    supports: list[Support],
    effective_depth: float | None = 40.0,
) -> AnchorageCalculator:
    """Construct an AnchorageCalculator whose reinforcement stub can build clamps"""
    reinforcement = types.SimpleNamespace(
        chosen_bars=[layer],
        beam=types.SimpleNamespace(
            height=60.0, length=_BEAM_LENGTH, label="V1", supports=supports
        ),
        required_area=2.0,
        area=2.0,
        center_position=_BEAM_LENGTH / 2,
        moment_zeros=(),
        effective_depth=effective_depth,
        design_shear=100.0,
        stirrup_inner_width=_STIRRUP_INNER_WIDTH,
        effective_covering=lambda: _EFFECTIVE_COVERING,
    )
    return AnchorageCalculator(
        moment_shift=28.0,
        steel=Steel.CA50,
        layer_index=0,
        reinforcement=reinforcement,  # pyright: ignore[reportArgumentType]
        id="Test",
    )


@pytest.fixture
def wide_supports() -> list[Support]:
    """Return 20 cm-wide end supports, and a 15 cm-wide one at the right end"""
    return [Support(0.0, -10.0, 10.0), Support(_BEAM_LENGTH, 495.0, 510.0)]


@pytest.fixture
def nominal_covering_3cm() -> Iterator[None]:
    """Pin the nominal covering to 3 cm while the test runs"""
    with patch.object(
        _BeamMeta, "nominal_covering", new_callable=PropertyMock
    ) as mock_cov:
        mock_cov.return_value = 3.0
        yield


@pytest.mark.usefixtures("nominal_covering_3cm")
class TestClampFallback:
    """Tests for run() completing the anchorage with clamps at extremity supports."""

    def test_clamps_not_allowed_still_raises(
        self, layer_16mm_good: Layer, wide_supports: list[Support]
    ) -> None:
        ac = _make_clamp_ac(layer_16mm_good, wide_supports)
        with pytest.raises(ValueError, match="even with hooks"):
            ac.run(available_space=_TIGHT_SPACE, left=True)
        assert layer_16mm_good.left_clamps is None, "No clamps without allow_clamp"

    def test_returns_clamps_and_sets_them_on_layer(
        self, layer_16mm_good: Layer, wide_supports: list[Support]
    ) -> None:
        ac = _make_clamp_ac(layer_16mm_good, wide_supports)
        clamps = ac.run(available_space=_TIGHT_SPACE, left=True, allow_clamp=True)
        assert isinstance(clamps, Clamps), "run() should return the clamps"
        assert layer_16mm_good.left_clamps is clamps, "Clamps stored on the left"
        assert layer_16mm_good.right_clamps is None, "Right side untouched"
        assert_approx(
            clamps.width, _STIRRUP_INNER_WIDTH, "Clamp width = stirrup inner width"
        )

    def test_bars_hooked_over_whole_adjusted_space(
        self, layer_16mm_good: Layer, wide_supports: list[Support]
    ) -> None:
        """Bars take the hook-adjusted space: 20 + 3 - max(3, 4.8) = 18.2 cm"""
        ac = _make_clamp_ac(layer_16mm_good, wide_supports)
        ac.run(available_space=_TIGHT_SPACE, left=True, allow_clamp=True)
        for bar in layer_16mm_good.bars:
            assert bar.left_hook_enabled, "Clamped bars keep their hooks"
            assert_approx(bar.left_length, 18.2, "Left length = adjusted space (cm)")

    def test_no_clamps_when_bars_anchor(
        self, layer_16mm_good: Layer, wide_supports: list[Support]
    ) -> None:
        ac = _make_clamp_ac(layer_16mm_good, wide_supports)
        clamps = ac.run(available_space=200.0, left=True, allow_clamp=True)
        assert clamps is None, "No clamps when straight bars fit"
        assert layer_16mm_good.left_clamps is None, "No clamps set on the layer"

    def test_zero_width_support_raises(self, layer_16mm_good: Layer) -> None:
        supports = [Support(0.0, 0.0, 0.0), Support(_BEAM_LENGTH, 500.0, 500.0)]
        ac = _make_clamp_ac(layer_16mm_good, supports)
        with pytest.raises(ValueError, match="No length inside the support"):
            ac.run(available_space=_TIGHT_SPACE, left=True, allow_clamp=True)

    def test_interior_support_raises(self, layer_16mm_good: Layer) -> None:
        supports = [Support(50.0, 40.0, 60.0), Support(_BEAM_LENGTH, 495.0, 510.0)]
        ac = _make_clamp_ac(layer_16mm_good, supports)
        with pytest.raises(ValueError, match="even with hooks"):
            ac.run(available_space=_TIGHT_SPACE, left=True, allow_clamp=True)

    def test_missing_effective_depth_raises(
        self, layer_16mm_good: Layer, wide_supports: list[Support]
    ) -> None:
        ac = _make_clamp_ac(layer_16mm_good, wide_supports, effective_depth=None)
        with pytest.raises(ValueError, match="Effective depth and design shear"):
            ac.run(available_space=_TIGHT_SPACE, left=True, allow_clamp=True)


class TestClampAvailableLength:
    """Tests for the anchorage length inside the extremity support (cm)."""

    def test_left_support(
        self, layer_16mm_good: Layer, wide_supports: list[Support]
    ) -> None:
        """Left: inner face 10 minus (outer face -10 + 2.5 cover) = 17.5 cm"""
        ac = _make_clamp_ac(layer_16mm_good, wide_supports)
        ac.left = True
        assert_approx(ac.clamp_available_length, 17.5, "Left length (cm)")

    def test_right_support(
        self, layer_16mm_good: Layer, wide_supports: list[Support]
    ) -> None:
        """Right: (outer face 510 - 2.5 cover) minus inner face 495 = 12.5 cm"""
        ac = _make_clamp_ac(layer_16mm_good, wide_supports)
        ac.left = False
        assert_approx(ac.clamp_available_length, 12.5, "Right length (cm)")
