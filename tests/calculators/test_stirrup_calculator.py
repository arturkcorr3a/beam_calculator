"""Unit tests for src/calculators/stirrup_calculator.py — StirrupCalculator."""

import types

import pytest

from src.calculators.stirrup_calculator import StirrupCalculator
from src.config import APP_CONFIG
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from tests.helpers import assert_approx


@pytest.fixture(autouse=True)
def pinned_concrete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the project concrete to C25 for every test in this module"""
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C25)


@pytest.fixture
def beam() -> types.SimpleNamespace:
    """A minimal beam stub: width=20 cm, CA50 steel."""
    return types.SimpleNamespace(
        width=20.0,
        steel=Steel.CA50,
    )


@pytest.fixture
def sc(beam: types.SimpleNamespace) -> StirrupCalculator:
    """StirrupCalculator with V_Sd=200 kN, effective_depth pre-set to 56 cm."""
    calc = StirrupCalculator(beam, design_shear_force=200.0, id="Test")  # pyright: ignore[reportArgumentType]
    calc.effective_depth = 56.0
    return calc


class TestCompressedStrutResistance:
    """Tests for V_Rd2 (compressed strut resistance) in kN."""

    def test_value(self, sc: StirrupCalculator) -> None:
        """V_Rd2 for C25, width=20 cm, d=56 cm (kN)."""
        # 0.27 * 0.9 * (25/10/1.4) * 20 * 56
        assert_approx(
            sc.compressed_strut_resistance,
            486.0,
            "V_Rd2 for C25/20cm/56cm (kN)",
        )


class TestConcreteContribution:
    """Tests for V_c (concrete shear contribution) in kN."""

    def test_value(self, sc: StirrupCalculator) -> None:
        """V_c = 0.6 * fctd * bw * d for C25, width=20 cm, d=56 cm (kN)."""
        assert_approx(
            sc.concrete_contribution,
            86.18278771250553,
            "V_c for C25/20cm/56cm (kN)",
        )


class TestRequiredContribution:
    """Tests for V_sw (required stirrup shear contribution) in kN."""

    def test_positive_contribution(self, sc: StirrupCalculator) -> None:
        """V_sw = max(V_Sd - V_c, 0) is positive when V_Sd > V_c (kN)."""
        # V_Sd=200, V_c≈86.18 → V_sw≈113.82
        assert_approx(
            sc.required_contribution,
            200.0 - 86.18278771250553,
            "V_sw is positive when V_Sd > V_c (kN)",
        )

    def test_clamped_to_zero(self, beam: types.SimpleNamespace) -> None:
        """V_sw is clamped to 0 when V_Sd <= V_c (kN)."""
        # V_Sd=10 kN << V_c≈86.18 kN
        sc_low = StirrupCalculator(beam, design_shear_force=10.0)  # pyright: ignore[reportArgumentType]
        sc_low.effective_depth = 56.0
        assert sc_low.required_contribution == 0, (
            "V_sw should be 0 when V_Sd < V_c (kN)"
        )


class TestMinimumRatio:
    """Tests for the minimum stirrup reinforcement ratio (cm²/cm)."""

    def test_value(self, sc: StirrupCalculator) -> None:
        """minimum_ratio = 0.2 * fct_m / fywk * bw * sin(90°) for C25/CA50 (cm²/cm)."""
        assert_approx(
            sc.minimum_ratio,
            0.020519711360120364,
            "minimum_ratio for C25/CA50/width=20 cm (cm²/cm)",
        )


class TestRequiredRatio:
    """Tests for the required stirrup reinforcement ratio (cm²/cm)."""

    def test_calculated_wins(self, sc: StirrupCalculator) -> None:
        """required_ratio equals calculated A_sw/s when it exceeds minimum (cm²/cm)."""
        # With V_Sd=200, V_c≈86.18 → V_sw≈113.82; fywd=43.478
        # asw_s = 113.82 / (0.9 * 56 * 43.478 * (1+0)) ≈ 0.05185
        expected = sc.required_contribution / (0.9 * 56.0 * Steel.CA50.fywd)
        assert_approx(
            sc.required_ratio, expected, "calculated ratio wins over minimum (cm²/cm)"
        )

    def test_minimum_wins(self, beam: types.SimpleNamespace) -> None:
        """required_ratio equals minimum_ratio when V_Sd is tiny (cm²/cm)."""
        sc_low = StirrupCalculator(beam, design_shear_force=1.0)  # pyright: ignore[reportArgumentType]
        sc_low.effective_depth = 56.0
        # V_sw=0 → asw_s=0 < minimum_ratio → result equals minimum
        assert_approx(
            sc_low.required_ratio,
            sc_low.minimum_ratio,
            "minimum_ratio wins when V_Sd is very small (cm²/cm)",
        )


class TestMaxSpacing:
    """Tests for maximum stirrup spacing (cm)."""

    def test_low_shear_capped_at_30(self, beam: types.SimpleNamespace) -> None:
        """max_spacing = min(0.6*d, 30) = 30 when d=56 and V_Sd <= 0.67*V_Rd2 (cm)."""
        # V_Sd=10, V_Rd2=486 → 0.67*486=325.62 → 10 <= 325.62 → branch 0.6*d=33.6, capped at 30
        sc_low = StirrupCalculator(beam, design_shear_force=10.0)  # pyright: ignore[reportArgumentType]
        sc_low.effective_depth = 56.0
        assert sc_low.max_spacing == 30.0, "max_spacing should be 30 cm (capped) (cm)"

    def test_low_shear_uncapped_0_6d(self, beam: types.SimpleNamespace) -> None:
        """max_spacing = 0.6*d when d is small enough that 0.6*d < 30 and V_Sd <= 0.67*V_Rd2 (cm)."""
        # For d=20: 0.6*20=12 < 30 → uncapped
        sc_small_d = StirrupCalculator(beam, design_shear_force=10.0)  # pyright: ignore[reportArgumentType]
        sc_small_d.effective_depth = 20.0
        assert sc_small_d.max_spacing == 12.0, (
            "max_spacing = 0.6*d=12 cm when d=20 and low shear (cm)"
        )

    def test_high_shear_branch(self, beam: types.SimpleNamespace) -> None:
        """max_spacing = 0.3*d when V_Sd > 0.67*V_Rd2 (cm)."""
        # V_Sd=400 > 0.67*486=325.62 → branch 0.3*d; d=56 → 0.3*56=16.8
        sc_high = StirrupCalculator(beam, design_shear_force=400.0)  # pyright: ignore[reportArgumentType]
        sc_high.effective_depth = 56.0
        assert_approx(
            sc_high.max_spacing, 16.8, "max_spacing=0.3*d=16.8 cm for high shear (cm)"
        )


class TestCalculateMomentShift:
    """Tests for calculate_moment_shift() (cm)."""

    def test_interior_value(self, sc: StirrupCalculator) -> None:
        """Moment shift is in (0.5*d, d) for a typical shear force (cm)."""
        al = sc.calculate_moment_shift()
        assert 0.5 * sc.effective_depth <= al <= sc.effective_depth, (
            "Moment shift should be between 0.5*d and d for typical V_Sd (cm)"
        )

    def test_upper_clamp_to_d(self, beam: types.SimpleNamespace) -> None:
        """al is clamped to d when the formula would exceed d (cm)."""
        # Very small V_Sd barely above V_c drives al → large; it gets clamped to d
        # Set V_Sd just above V_c (V_c≈86.18) so denominator is tiny
        sc_near = StirrupCalculator(beam, design_shear_force=86.2)  # pyright: ignore[reportArgumentType]
        sc_near.effective_depth = 56.0
        al = sc_near.calculate_moment_shift()
        assert al == sc_near.effective_depth, (
            "al should be clamped to d when formula gives a value > d (cm)"
        )

    def test_lower_clamp_to_half_d(self, beam: types.SimpleNamespace) -> None:
        """al is at least 0.5*d (cm)."""
        # cotan(pi/2)=0, so formula collapses to d*(V_Sd/(2*(V_Sd-V_c)))
        # Large V_Sd makes the fraction small → al can go below 0.5*d
        sc_large = StirrupCalculator(beam, design_shear_force=480.0)  # pyright: ignore[reportArgumentType]
        sc_large.effective_depth = 56.0
        al = sc_large.calculate_moment_shift()
        assert al >= 0.5 * sc_large.effective_depth, "al must be at least 0.5*d (cm)"

    def test_equal_to_v_c_returns_d(self, beam: types.SimpleNamespace) -> None:
        """a_l = d when V_Sd == V_c, instead of dividing by zero (cm)."""
        # V_c = 0.6 * fctd * 20 * 56; set V_Sd exactly equal
        fctd = Concrete.C25.fctd
        v_c = 0.6 * fctd * 20.0 * 56.0
        sc_eq = StirrupCalculator(beam, design_shear_force=v_c)  # pyright: ignore[reportArgumentType]
        sc_eq.effective_depth = 56.0
        assert_approx(
            sc_eq.calculate_moment_shift(), 56.0, "a_l should be d when V_Sd = V_c (cm)"
        )

    def test_below_v_c_returns_d(self, beam: types.SimpleNamespace) -> None:
        """a_l = d when V_Sd < V_c (the formula would give a negative value) (cm)."""
        sc_low = StirrupCalculator(beam, design_shear_force=10.0)  # pyright: ignore[reportArgumentType]
        sc_low.effective_depth = 56.0
        assert_approx(
            sc_low.calculate_moment_shift(),
            56.0,
            "a_l should be d when V_Sd < V_c (cm)",
        )

    def test_negative_shear_uses_magnitude(self, beam: types.SimpleNamespace) -> None:
        """A negative V_Sd gives the same a_l as its magnitude (cm)."""
        sc_pos = StirrupCalculator(beam, design_shear_force=200.0)  # pyright: ignore[reportArgumentType]
        sc_neg = StirrupCalculator(beam, design_shear_force=-200.0)  # pyright: ignore[reportArgumentType]
        sc_pos.effective_depth = sc_neg.effective_depth = 56.0
        assert_approx(
            sc_neg.calculate_moment_shift(),
            sc_pos.calculate_moment_shift(),
            "a_l should depend on |V_Sd| only (cm)",
        )


class TestVerifyCompressedStrutResistance:
    """Tests for verify_compressed_strut_resistance()."""

    def test_passes_when_v_sd_below_v_rd2(self, sc: StirrupCalculator) -> None:
        """No error when V_Sd < V_Rd2."""
        # V_Sd=200, V_Rd2=486 → should not raise
        sc.verify_compressed_strut_resistance()  # must not raise

    def test_raises_when_v_sd_exceeds_v_rd2(self, beam: types.SimpleNamespace) -> None:
        """ValueError when V_Sd > V_Rd2."""
        sc_over = StirrupCalculator(beam, design_shear_force=500.0)  # pyright: ignore[reportArgumentType]
        sc_over.effective_depth = 56.0
        with pytest.raises(ValueError, match="exceeds compressed strut resistance"):
            sc_over.verify_compressed_strut_resistance()


class TestCalculate:
    """Tests for the calculate() driver method."""

    def test_returns_required_ratio(self, sc: StirrupCalculator) -> None:
        """calculate(d) returns the required_ratio (cm²/cm) and sets effective_depth."""
        ratio = sc.calculate(56.0)
        assert_approx(
            ratio,
            sc.required_ratio,
            "calculate() return equals required_ratio (cm²/cm)",
        )
        assert sc.effective_depth == 56.0, "effective_depth should be set to 56 cm"

    def test_raises_when_strut_exceeded(self, beam: types.SimpleNamespace) -> None:
        """calculate() raises ValueError when V_Sd > V_Rd2."""
        sc_over = StirrupCalculator(beam, design_shear_force=500.0)  # pyright: ignore[reportArgumentType]
        with pytest.raises(ValueError, match="exceeds compressed strut resistance"):
            sc_over.calculate(56.0)
