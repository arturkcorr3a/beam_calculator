"""Unit tests for the DeformationChecker abstract base class.

Tests the concrete arithmetic methods via a minimal stub subclass that injects
exact ``service_moment``, ``immediate_deflection``, and ``design_load`` values
so each assertion isolates only the base-class arithmetic under test.
"""

from dataclasses import dataclass

import pytest

from src.checkers.deformation_checker import DeformationChecker
from src.config import APP_CONFIG
from src.properties.concrete import Concrete
from src.properties.section_properties_calculator import (
    SectionPropertiesCalculator as section,
)
from src.properties.steel import Steel
from tests.helpers import assert_approx

# ---------------------------------------------------------------------------
# Minimal concrete subclass for testing
# ---------------------------------------------------------------------------


@dataclass(kw_only=True)
class _StubChecker(DeformationChecker):
    """Minimal concrete DeformationChecker exercising only base-class arithmetic."""

    _service_moment: float = 0.0
    _immediate_deflection: float = 0.0
    _design_load: float = 0.0

    @property
    def service_moment(self) -> float:
        return self._service_moment

    @property
    def design_load(self) -> float:
        return self._design_load

    @property
    def immediate_deflection(self) -> float:
        return self._immediate_deflection


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def pinned_concrete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the project concrete to C30 for every test in this module"""
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C30)


@pytest.fixture
def base_checker() -> _StubChecker:
    """Return a _StubChecker with standard base geometry (b=20, h unset, C30, span=500).

    Parameters intentionally kept small and round for easy mental verification.
    ``height`` and ``effective_depth`` are not set here — any test that calls
    a method which reads them must call ``verify(h)`` first or assign them
    directly.
    """
    return _StubChecker(
        permanent_load=10.0,
        variable_load=5.0,
        span=500.0,
        width=20.0,
        effective_depth_discount=4.0,
        compressed_reinforcement_area=0.0,
        effective_depth_compressed=0.0,
        tensioned_reinforcement_area=5.0,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAcceptableDeflection:
    """Tests for the acceptable_deflection property."""

    def test_returns_span_over_250(self, base_checker: _StubChecker) -> None:
        """Acceptable deflection is span / 250."""
        assert_approx(
            base_checker.acceptable_deflection,
            500.0 / 250.0,
            "Acceptable deflection should be span/250 = 2.0 cm",
        )


class TestCrackingMoment:
    """Tests for the cracking_moment property."""

    def test_uses_gross_inertia_and_fctm(self, base_checker: _StubChecker) -> None:
        """Cracking moment uses 1.5 * fct_m * I_gross / (h/2)."""
        base_checker.verify(60.0)
        i_gross = section.moment_of_inertia(20.0, 60.0)  # 360000 cm⁴
        expected = 1.5 * Concrete.C30.fct_m * i_gross / (60.0 / 2.0)
        assert_approx(
            base_checker.cracking_moment,
            expected,
            "Cracking moment should be 1.5*fct_m*I/(h/2) kN.cm",
        )


class TestIsCracked:
    """Tests for the is_cracked boolean property."""

    def test_true_when_service_exceeds_cracking(
        self, base_checker: _StubChecker
    ) -> None:
        """Element is cracked when service_moment > cracking_moment."""
        base_checker.verify(60.0)
        # cracking_moment ≈ 5213.64 kN.cm; set service well above it
        base_checker._service_moment = base_checker.cracking_moment * 2.0  # pyright: ignore[reportPrivateUsage]
        assert base_checker.is_cracked, (
            "is_cracked should be True when service_moment > cracking_moment"
        )

    def test_false_when_below(self, base_checker: _StubChecker) -> None:
        """Element is not cracked when service_moment < cracking_moment."""
        base_checker.verify(60.0)
        base_checker._service_moment = base_checker.cracking_moment * 0.5  # pyright: ignore[reportPrivateUsage]
        assert not base_checker.is_cracked, (
            "is_cracked should be False when service_moment < cracking_moment"
        )

    def test_false_at_equality_strict_gt(self, base_checker: _StubChecker) -> None:
        """is_cracked uses strict >, so equality is NOT cracked."""
        base_checker.verify(60.0)
        base_checker._service_moment = base_checker.cracking_moment  # pyright: ignore[reportPrivateUsage]
        assert not base_checker.is_cracked, (
            "is_cracked should be False when service_moment == cracking_moment "
            "(strict > comparison)"
        )


class TestEquivalentMomentOfInertia:
    """Tests for the equivalent_moment_of_inertia property (Branson formula)."""

    def test_returns_gross_when_not_cracked(self, base_checker: _StubChecker) -> None:
        """Branch 1: if not cracked, returns gross section I."""
        base_checker.verify(60.0)
        base_checker._service_moment = base_checker.cracking_moment * 0.5  # pyright: ignore[reportPrivateUsage]
        i_gross = section.moment_of_inertia(20.0, 60.0)
        assert_approx(
            base_checker.equivalent_moment_of_inertia,
            i_gross,
            "Equivalent I should equal gross I when element is not cracked (cm⁴)",
        )

    def test_branson_formula_when_cracked(self, base_checker: _StubChecker) -> None:
        """Branch 2 (cracked): Branson formula with moments_ratio = 0.5."""
        base_checker.verify(60.0)
        cracking_m = base_checker.cracking_moment
        # service = 2× cracking → k = 0.5
        base_checker._service_moment = cracking_m * 2.0  # pyright: ignore[reportPrivateUsage]

        i_gross = section.moment_of_inertia(20.0, 60.0)
        modular_ratio = Steel.elastic_modulus / Concrete.C30.ecs
        i_cracked = section.cracked_section_moment_of_inertia(
            20.0, 56.0, 5.0, modular_ratio, 0.0, 0.0
        )
        k = 0.5
        expected = min(k**3 * i_gross + (1 - k**3) * i_cracked, i_gross)

        assert_approx(
            base_checker.equivalent_moment_of_inertia,
            expected,
            "Equivalent I (cracked, k=0.5) should match Branson formula (cm⁴)",
        )

    def test_equivalent_never_exceeds_gross(self, base_checker: _StubChecker) -> None:
        """Branson result is always capped at the gross section I."""
        base_checker.verify(60.0)
        # Set service very close to cracking (k≈1): Branson converges to gross
        base_checker._service_moment = base_checker.cracking_moment * 1.001  # pyright: ignore[reportPrivateUsage]
        i_gross = section.moment_of_inertia(20.0, 60.0)
        assert base_checker.equivalent_moment_of_inertia <= i_gross + 1e-9, (
            "Equivalent I must never exceed the gross section I"
        )


class TestLongTermDeflection:
    """Tests for the long_term_deflection property (creep amplification)."""

    def test_rho_zero_gives_triple_immediate(self, base_checker: _StubChecker) -> None:
        """When Asc = 0 (rho = 0) the long-term factor is 1 + 2/(1+0) = 3."""
        base_checker.verify(60.0)
        base_checker._service_moment = base_checker.cracking_moment * 0.5  # pyright: ignore[reportPrivateUsage]
        base_checker._immediate_deflection = 1.0  # pyright: ignore[reportPrivateUsage]

        expected = 3.0 * 1.0
        assert_approx(
            base_checker.long_term_deflection,
            expected,
            "Long-term deflection should be 3× immediate when Asc=0 (cm)",
        )

    def test_nonzero_rho(self, base_checker: _StubChecker) -> None:
        """Nonzero Asc reduces the creep multiplier: rho=0.01 → factor = 1+2/1.5."""
        base_checker.compressed_reinforcement_area = 11.2  # rho = 11.2/(20*56) = 0.01
        base_checker.verify(60.0)
        base_checker._service_moment = base_checker.cracking_moment * 0.5  # pyright: ignore[reportPrivateUsage]
        base_checker._immediate_deflection = 1.0  # pyright: ignore[reportPrivateUsage]

        rho = 11.2 / (20.0 * 56.0)
        fluency = 2.0 / (1.0 + 50.0 * rho)
        expected = (1.0 + fluency) * 1.0

        assert_approx(
            base_checker.long_term_deflection,
            expected,
            "Long-term deflection with rho=0.01 should be (1+2/1.5)×immediate (cm)",
        )

    def test_zero_effective_depth_raises_zero_division(
        self, base_checker: _StubChecker
    ) -> None:
        """Division by zero when effective_depth == 0 (height == discount).

        Sets height and effective_depth directly to avoid triggering
        long_term_deflection inside verify() before the pytest.raises block.
        """
        base_checker.compressed_reinforcement_area = 5.0
        # Manually replicate what verify(4.0) would set, skipping the evaluation
        base_checker.height = 4.0
        base_checker.effective_depth = 0.0  # 4.0 - 4.0 = 0
        base_checker._service_moment = (  # pyright: ignore[reportPrivateUsage]
            0.0  # keep not-cracked
        )
        base_checker._immediate_deflection = 1.0  # pyright: ignore[reportPrivateUsage]

        with pytest.raises(ZeroDivisionError):
            _ = base_checker.long_term_deflection


class TestVerify:
    """Tests for the verify method."""

    def test_sets_height_and_effective_depth(self, base_checker: _StubChecker) -> None:
        """verify(h) stores h and computes effective_depth = h - discount."""
        base_checker.verify(60.0)
        assert base_checker.height == 60.0, "height should be set to 60.0 cm"
        assert base_checker.effective_depth == 56.0, (
            "effective_depth should be height - discount = 56.0 cm"
        )

    def test_pass_when_within_limit(self, base_checker: _StubChecker) -> None:
        """verify returns True when long_term_deflection <= acceptable_deflection."""
        # Make immediate very small so long_term << span/250
        base_checker._immediate_deflection = 0.001  # pyright: ignore[reportPrivateUsage]
        assert base_checker.verify(60.0), (
            "verify should return True when deflection is within limit"
        )

    def test_fail_when_exceeds(self, base_checker: _StubChecker) -> None:
        """verify returns False when long_term_deflection > acceptable_deflection."""
        # span/250 = 2.0 cm; long_term = 3×immediate → need immediate > 2/3 ≈ 0.67
        base_checker._immediate_deflection = 10.0  # pyright: ignore[reportPrivateUsage]
        assert not base_checker.verify(60.0), (
            "verify should return False when deflection exceeds limit"
        )

    def test_pass_at_equality_boundary(self, base_checker: _StubChecker) -> None:
        """verify uses <=, so equality is a pass."""
        # span/250 = 2.0; rho=0 → long_term = 3×immediate; need 3×immediate == 2.0
        # → immediate = 2/3
        base_checker._immediate_deflection = 2.0 / 3.0  # pyright: ignore[reportPrivateUsage]
        # Pin service below cracking so is_cracked=False and equivalent_I = gross
        base_checker.verify(60.0)
        base_checker._service_moment = base_checker.cracking_moment * 0.1  # pyright: ignore[reportPrivateUsage]

        result = base_checker.verify(60.0)
        # 2.0 / 3.0 * 3 = 2.0 = acceptable_deflection → exactly at boundary
        assert result, "verify should return True when deflection == acceptable limit"


class TestTensionedReinforcementAreaBase:
    """Tests for the base _tensioned_reinforcement_area property."""

    def test_returns_tensioned_field(self, base_checker: _StubChecker) -> None:
        """Base implementation returns the tensioned_reinforcement_area field."""
        base_checker.verify(60.0)
        assert (
            base_checker._tensioned_reinforcement_area  # pyright: ignore[reportPrivateUsage]
            == 5.0
        ), "Base _tensioned_reinforcement_area should return the constructor-set value"


class TestResult:
    """result() snapshots the verification at the last verified height."""

    def test_raises_before_verify(self, base_checker: _StubChecker) -> None:
        with pytest.raises(ValueError, match="not been verified"):
            base_checker.result()

    def test_reflects_last_verify(self, base_checker: _StubChecker) -> None:
        base_checker.verify(50.0)
        base_checker.verify(40.0)
        result = base_checker.result()
        assert result.height == 40.0, "result should use the last verified height (cm)"
        assert_approx(
            result.effective_depth, 36.0, "d should be h minus the discount (cm)"
        )
        assert_approx(
            result.long_term_deflection,
            base_checker.long_term_deflection,
            "result should copy the long-term deflection (cm)",
        )
        assert_approx(
            result.acceptable_deflection, 2.0, "limit should be span / 250 (cm)"
        )

    def test_passes_matches_verify(self, base_checker: _StubChecker) -> None:
        base_checker._immediate_deflection = 10.0  # pyright: ignore[reportPrivateUsage]
        verdict = base_checker.verify(40.0)
        assert base_checker.result().passes == verdict, (
            "result.passes should agree with verify's verdict"
        )
