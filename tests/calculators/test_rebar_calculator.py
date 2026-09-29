"""Unit tests for src/calculators/rebar_calculator.py — RebarCalculator.

Ports and supersedes tests/reinforcement/test_rebar_calculator.py with
class-based style, assert_approx, and additional branch coverage.
"""

import types
from collections.abc import Generator
from unittest.mock import Mock, PropertyMock, patch

import pytest

from src.calculators.rebar_calculator import RebarCalculator
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.structural_elements.rectangular_beam import (
    RectangularBeam,
    _BeamMeta,  # pyright: ignore[reportPrivateUsage]
)
from tests.helpers import assert_approx

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def beam_mock() -> Generator[Mock, None, None]:
    """A Mock(spec=RectangularBeam) with nominal_covering patched on _BeamMeta.

    Yields the beam mock inside the patch context so callers have a stable
    reference even when the nominal_covering metaclass property is accessed lazily.
    """
    beam = Mock(spec=RectangularBeam)
    beam.width = 20
    beam.height = 60
    beam.length = 500
    beam.concrete = Concrete.C25
    beam.steel = Steel.CA50
    beam.area = 1200
    with patch.object(_BeamMeta, "nominal_covering", new_callable=PropertyMock) as m:
        m.return_value = 3
        yield beam


@pytest.fixture
def calculator(beam_mock: Mock) -> RebarCalculator:
    """RebarCalculator with d=56 cm and d_compressed=4 cm assigned post-construction.

    The _BeamMeta patch is still active (inherited from beam_mock fixture scope).
    """
    stirrups = Mock()
    calc = RebarCalculator(
        beam=beam_mock,
        bending_moment=272,
        stirrups=stirrups,
        bending_moment_position=beam_mock.length / 2,
        id="Test Beam",
    )
    calc.d = 56
    calc.d_compressed = 4
    return calc


@pytest.fixture
def calculator_preset(beam_mock: Mock) -> RebarCalculator:
    """RebarCalculator with d/d_compressed supplied as constructor args (preset path)."""
    stirrups = Mock()
    return RebarCalculator(
        beam=beam_mock,
        bending_moment=272,
        stirrups=stirrups,
        bending_moment_position=beam_mock.length / 2,
        id="Test Beam Preset",
        d=56,
        d_compressed=4,
    )


@pytest.fixture
def calculator_small_moment(beam_mock: Mock) -> RebarCalculator:
    """RebarCalculator for a singly-reinforced case (bending_moment=50 kN.m)."""
    stirrups = Mock()
    calc = RebarCalculator(
        beam=beam_mock,
        bending_moment=50,
        stirrups=stirrups,
        bending_moment_position=beam_mock.length / 2,
        id="Test Beam Small",
    )
    calc.d = 56
    calc.d_compressed = 4
    return calc


# ---------------------------------------------------------------------------
# TestDesignBendingMoment
# ---------------------------------------------------------------------------


class TestDesignBendingMoment:
    """Tests for design_bending_moment (kN·cm)."""

    def test_value(self, calculator: RebarCalculator) -> None:
        """design_bending_moment = abs(272 kN.m * 100 * 1.4) = 38080 kN.cm."""
        assert_approx(
            calculator.design_bending_moment,
            38080.0,
            "design_bending_moment for 272 kN.m (kN.cm)",
        )


# ---------------------------------------------------------------------------
# TestMaxY
# ---------------------------------------------------------------------------


class TestMaxY:
    """Tests for max_y (maximum stress-block depth) in cm."""

    def test_c25_value(self, calculator: RebarCalculator) -> None:
        """max_y for C25/CA50/d=56 cm (cm)."""
        assert_approx(
            calculator.max_y,
            20.160000000000004,
            "max_y for C25/CA50/d=56 cm (cm)",
        )

    def test_c60_ductility_branch(self, beam_mock: Mock) -> None:
        """max_y uses 0.35*lambda_c branch when fck > 50 (cm)."""
        beam_mock.concrete = Concrete.C60
        stirrups = Mock()
        calc = RebarCalculator(
            beam=beam_mock,
            bending_moment=272,
            stirrups=stirrups,
            bending_moment_position=beam_mock.length / 2,
            id="C60 test",
        )
        calc.d = 56
        calc.d_compressed = 4
        # 0.35 * lambda_c(C60=0.775) * 56 = 15.19
        expected = 0.35 * Concrete.C60.lambda_c * 56
        assert_approx(calc.max_y, expected, "max_y for C60/d=56 cm (cm)")


# ---------------------------------------------------------------------------
# TestMaxBendingMoment
# ---------------------------------------------------------------------------


class TestMaxBendingMoment:
    """Tests for max_bending_moment (kN·cm)."""

    def test_value(self, calculator: RebarCalculator) -> None:
        """max_bending_moment for C25/CA50/d=56/y_max=20.16 (kN.cm)."""
        assert_approx(
            calculator.max_bending_moment,
            28103.04,
            "max_bending_moment for C25/CA50/d=56 cm (kN.cm)",
        )


# ---------------------------------------------------------------------------
# TestIsSinglyReinforced
# ---------------------------------------------------------------------------


class TestIsSinglyReinforced:
    """Tests for is_singly_reinforced."""

    def test_doubly_reinforced(self, calculator: RebarCalculator) -> None:
        """is_singly_reinforced is False for a large bending moment."""
        assert not calculator.is_singly_reinforced, (
            "Beam should NOT be singly reinforced for 272 kN.m (dimensionless)"
        )

    def test_singly_reinforced(self, calculator_small_moment: RebarCalculator) -> None:
        """is_singly_reinforced is True for a small bending moment."""
        assert calculator_small_moment.is_singly_reinforced, (
            "Beam should be singly reinforced for 50 kN.m (dimensionless)"
        )


# ---------------------------------------------------------------------------
# TestActualY
# ---------------------------------------------------------------------------


class TestActualY:
    """Tests for actual_y (actual stress-block depth) in cm."""

    def test_value_singly_reinforced(
        self, calculator_small_moment: RebarCalculator
    ) -> None:
        """actual_y is a valid float < max_y for a singly-reinforced case (cm)."""
        y = calculator_small_moment.actual_y
        assert 0 < y < calculator_small_moment.max_y, (
            "actual_y should be in (0, max_y) for singly-reinforced case (cm)"
        )

    def test_raises_on_negative_sqrt_domain(self, calculator: RebarCalculator) -> None:
        """actual_y raises ValueError (math domain) when design_bending_moment is huge."""
        # Force an impossibly large design_bending_moment so sqrt goes negative
        calculator.design_bending_moment = 1e12
        with pytest.raises((ValueError, Exception)):
            _ = calculator.actual_y


# ---------------------------------------------------------------------------
# TestAs1
# ---------------------------------------------------------------------------


class TestAs1:
    """Tests for as1 (first-layer tensile area) in cm²."""

    def test_doubly_reinforced(self, calculator: RebarCalculator) -> None:
        """as1 uses max_y for doubly-reinforced case (cm²)."""
        assert_approx(
            calculator.as1,
            14.075999999999999,
            "as1 for doubly-reinforced case (cm²)",
        )

    def test_singly_reinforced_uses_actual_y(
        self, calculator_small_moment: RebarCalculator
    ) -> None:
        """as1 uses actual_y for singly-reinforced case (cm²)."""
        y = calculator_small_moment.actual_y
        uniform_stress = Concrete.C25.uniform_stress
        expected = (uniform_stress * 20 * y) / Steel.CA50.fyd
        assert_approx(
            calculator_small_moment.as1,
            expected,
            "as1 uses actual_y for singly-reinforced case (cm²)",
        )


# ---------------------------------------------------------------------------
# TestCompressedReinforcement
# ---------------------------------------------------------------------------


class TestCompressedReinforcement:
    """Tests for compressed reinforcement properties (doubly-reinforced)."""

    def test_epsilon_s2(self, calculator: RebarCalculator) -> None:
        """Strain in compression reinforcement (dimensionless)."""
        assert_approx(
            calculator.calculate_epsilon_s2(),
            0.002944444444444445,
            "epsilon_s2 (dimensionless)",
        )

    def test_sigma_s2(self, calculator: RebarCalculator) -> None:
        """Stress in compression reinforcement (kN/cm²)."""
        assert_approx(
            calculator.calculate_sigma_s2(),
            43.47826086956522,
            "sigma_s2 (kN/cm²)",
        )

    def test_corrected_sigma_s2(self, calculator: RebarCalculator) -> None:
        """Corrected stress in compression reinforcement (kN/cm²)."""
        assert_approx(
            calculator.corrected_sigma_s2,
            41.96040372670807,
            "corrected_sigma_s2 (kN/cm²)",
        )

    def test_compressed_rebar_area(self, calculator: RebarCalculator) -> None:
        """Required compressed rebar area (cm²)."""
        assert_approx(
            calculator.compressed_rebar_area,
            4.572515951806543,
            "compressed_rebar_area (cm²)",
        )

    def test_delta_as(self, calculator: RebarCalculator) -> None:
        """Additional tensile area from compression reinforcement (cm²)."""
        assert_approx(
            calculator.calculate_delta_as(),
            4.412886153846154,
            "delta_as (cm²)",
        )


# ---------------------------------------------------------------------------
# TestTensionedRebarArea
# ---------------------------------------------------------------------------


class TestTensionedRebarArea:
    """Tests for tensioned_rebar_area in cm²."""

    def test_doubly_reinforced(self, calculator: RebarCalculator) -> None:
        """tensioned_rebar_area = as1 + delta_as for doubly-reinforced (cm²)."""
        assert_approx(
            calculator.tensioned_rebar_area,
            18.488886153846155,
            "tensioned_rebar_area for doubly-reinforced (cm²)",
        )

    def test_singly_reinforced(self, calculator_small_moment: RebarCalculator) -> None:
        """tensioned_rebar_area = as1 for singly-reinforced (cm²)."""
        assert_approx(
            calculator_small_moment.tensioned_rebar_area,
            calculator_small_moment.as1,
            "tensioned_rebar_area equals as1 for singly-reinforced (cm²)",
        )


# ---------------------------------------------------------------------------
# TestMinTensionRebarArea
# ---------------------------------------------------------------------------


class TestMinTensionRebarArea:
    """Tests for min_tension_rebar_area in cm²."""

    def test_value(self, calculator: RebarCalculator) -> None:
        """min_tension_rebar_area for 20×60 cm C25/CA50 beam (cm²)."""
        assert_approx(
            calculator.min_tension_rebar_area,
            1.7999999999999998,
            "min_tension_rebar_area for 20×60/C25/CA50 (cm²)",
        )


# ---------------------------------------------------------------------------
# TestMaxRebarArea
# ---------------------------------------------------------------------------


class TestMaxRebarArea:
    """Tests for max_rebar_area in cm²."""

    def test_value(self, calculator: RebarCalculator) -> None:
        """max_rebar_area = 0.04 * 1200 = 48 cm² (cm²)."""
        assert_approx(
            calculator.max_rebar_area,
            48.0,
            "max_rebar_area = 0.04 * area (cm²)",
        )


# ---------------------------------------------------------------------------
# TestCalculateDeltaBendingMoment
# ---------------------------------------------------------------------------


class TestCalculateDeltaBendingMoment:
    """Tests for calculate_delta_bending_moment() in kN·cm."""

    def test_value(self, calculator: RebarCalculator) -> None:
        """delta_bending_moment = design_bm - max_bm (kN.cm)."""
        assert_approx(
            calculator.calculate_delta_bending_moment(),
            9976.96,
            "delta_bending_moment for 272 kN.m case (kN.cm)",
        )


# ---------------------------------------------------------------------------
# TestCalculateAndSetRequiredTensionedRebarArea
# ---------------------------------------------------------------------------


class TestCalculateAndSetRequiredTensionedRebarArea:
    """Tests for calculate_and_set_required_tensioned_rebar_area()."""

    def test_within_limits_does_not_raise(self, calculator: RebarCalculator) -> None:
        """No error when total area <= max_rebar_area (cm²)."""
        # tensioned≈18.49 + compressed≈4.57 ≈ 23.06 < 48 cm²
        calculator.calculate_and_set_required_tensioned_rebar_area()

    def test_raises_when_area_exceeds_max(self, beam_mock: Mock) -> None:
        """ValueError when total area > max_rebar_area (cm²)."""
        # Shrink beam area so max_rebar_area = 0.04 * 400 = 16 < 23 cm²
        beam_mock.area = 400
        stirrups = Mock()
        calc = RebarCalculator(
            beam=beam_mock,
            bending_moment=272,
            stirrups=stirrups,
            bending_moment_position=beam_mock.length / 2,
            id="overload test",
        )
        calc.d = 56
        calc.d_compressed = 4
        with pytest.raises(ValueError, match="exceeds maximum allowable limit"):
            calc.calculate_and_set_required_tensioned_rebar_area()


# ---------------------------------------------------------------------------
# TestPresetDepths
# ---------------------------------------------------------------------------


class TestPresetDepths:
    """Tests for the preset_d / preset_d_compressed short-circuit paths."""

    def test_preset_d_is_used(self, calculator_preset: RebarCalculator) -> None:
        """d returns the preset value directly (cm)."""
        assert calculator_preset.d == 56, "preset_d should be returned as d (cm)"

    def test_preset_d_compressed_is_used(
        self, calculator_preset: RebarCalculator
    ) -> None:
        """d_compressed returns the preset value directly (cm)."""
        assert calculator_preset.d_compressed == 4, (
            "preset_d_compressed should be returned as d_compressed (cm)"
        )


# ---------------------------------------------------------------------------
# TestEffectiveDepthErrors
# ---------------------------------------------------------------------------


class TestEffectiveDepthErrors:
    """Tests for ValueError when reinforcement is chosen but empty."""

    def test_d_raises_when_first_layer_is_empty(self, beam_mock: Mock) -> None:
        """d raises ValueError when tensioned reinforcement is chosen but empty."""
        # Build a stirrups stub with diameter=None so the default path is taken
        stirrups_stub = types.SimpleNamespace(
            diameter=None,
            calculator=types.SimpleNamespace(calculate_moment_shift=lambda: 0),
        )
        calc = RebarCalculator(
            beam=beam_mock,
            bending_moment=272,
            stirrups=stirrups_stub,  # type: ignore[arg-type]
            bending_moment_position=250,
            id="err test",
        )
        # Mark the tensioned reinforcement as chosen but leave bars empty
        calc.tensioned_reinforcement.is_chosen = True
        # chosen_bars[0].bars is already [] from construction
        with pytest.raises(ValueError, match="no bars have been set"):
            _ = calc.d


# ---------------------------------------------------------------------------
# TestCleanup
# ---------------------------------------------------------------------------


class TestCleanup:
    """Tests for cleanup() — cache eviction."""

    def test_cleanup_clears_cached_properties(
        self, calculator: RebarCalculator
    ) -> None:
        """cleanup() removes cached max_y, corrected_sigma_s2, tensioned_rebar_area."""
        # Populate caches
        _ = calculator.max_y
        _ = calculator.corrected_sigma_s2
        _ = calculator.tensioned_rebar_area
        assert "max_y" in calculator.__dict__, "max_y should be cached before cleanup"
        calculator.cleanup()
        assert "max_y" not in calculator.__dict__, "max_y should be gone after cleanup"
        assert "corrected_sigma_s2" not in calculator.__dict__, (
            "corrected_sigma_s2 should be gone after cleanup"
        )
        assert "tensioned_rebar_area" not in calculator.__dict__, (
            "tensioned_rebar_area should be gone after cleanup"
        )


# ---------------------------------------------------------------------------
# TestCalculate (isolated/mocked, per plan)
# ---------------------------------------------------------------------------


class TestCalculate:
    """Tests for calculate() — the convergence loop (mocked, not full solve)."""

    def test_loop_terminates_with_preset_d(
        self, calculator_preset: RebarCalculator
    ) -> None:
        """calculate() exits the loop when d is stable (preset path), without error."""
        # Stub stirrups.calculate_and_choose to be a no-op
        calculator_preset.stirrups.calculate_and_choose = Mock(return_value=(30.0, 1.0))  # type: ignore[assignment]
        # Stub set_required_area on both reinforcements to be no-ops
        calculator_preset.tensioned_reinforcement.set_required_area = Mock()  # type: ignore[method-assign]
        calculator_preset.compressed_reinforcement.set_required_area = Mock()  # type: ignore[method-assign]

        calculator_preset.calculate()  # must not raise or loop forever

        # stirrups.calculate_and_choose should have been called at least once
        assert calculator_preset.stirrups.calculate_and_choose.called, (
            "stirrups.calculate_and_choose should be called during calculate()"
        )

    def test_singly_reinforced_does_not_call_compressed_set_required_area(
        self, beam_mock: Mock
    ) -> None:
        """calculate() does not set compressed reinforcement area for singly-reinforced."""
        stirrups = Mock()
        stirrups.calculate_and_choose = Mock(return_value=(30.0, 1.0))
        calc = RebarCalculator(
            beam=beam_mock,
            bending_moment=50,  # small → singly reinforced
            stirrups=stirrups,
            bending_moment_position=beam_mock.length / 2,
            id="single test",
            d=56,
            d_compressed=4,
        )
        calc.tensioned_reinforcement.set_required_area = Mock()  # type: ignore[method-assign]
        calc.compressed_reinforcement.set_required_area = Mock()  # type: ignore[method-assign]

        calc.calculate()

        calc.compressed_reinforcement.set_required_area.assert_not_called()  # type: ignore[attr-defined]
