"""Unit tests for the Concrete enum and its material properties."""

from typing import Any, cast

import pytest

from src.config import APP_CONFIG
from src.properties.concrete import GAMMA_C, Concrete
from tests.helpers import assert_approx


@pytest.fixture
def concrete_c25() -> Concrete:
    """Group-1 concrete (fck <= 50 MPa)."""
    return Concrete.C25


@pytest.fixture
def concrete_c60() -> Concrete:
    """Group-2 concrete (fck > 50 MPa)."""
    return Concrete.C60


def _clear_cached_property(member: Concrete, name: str) -> None:
    """Evict one cached_property from an enum member so it recomputes on next access.

    Enum members are singletons, so ``cached_property`` results persist on the member
    across tests. Aggregate-dependent properties must be re-evaluated after the
    configured aggregate changes.

    Args:
        member: The concrete enum member whose cache should be cleared.
        name: The cached_property attribute name to evict.
    """
    # A member's __dict__ is a read-only proxy at the type level, but enum members
    # store cached_property results in a mutable backing dict at runtime.
    member_cache = cast(dict[str, Any], member.__dict__)
    member_cache.pop(name, None)


class TestSafetyFactor:
    """Tests for the concrete safety factor constant."""

    def test_gamma_c(self) -> None:
        expected_gamma_c = 1.4
        assert GAMMA_C == expected_gamma_c, (
            "The concrete safety factor (gamma_c) should be 1.4"
        )


class TestConcreteGroup:
    """Tests for the NBR 8953 concrete group classification."""

    def test_group_1_for_low_strength(self, concrete_c25: Concrete) -> None:
        expected_group = 1
        assert concrete_c25.concrete_group == expected_group, (
            "For concrete with fck 25 MPa, the concrete group should be 1"
        )

    def test_group_2_for_high_strength(self, concrete_c60: Concrete) -> None:
        expected_group = 2
        assert concrete_c60.concrete_group == expected_group, (
            "For concrete with fck 60 MPa, the concrete group should be 2"
        )

class TestElasticModuli:
    """Tests for the elastic and shear moduli, assuming granite/gneiss aggregate."""

    def test_eci_group_1(self, concrete_c25: Concrete) -> None:
        expected_eci = 28_000.0  # MPa
        assert_approx(
            concrete_c25.eci,
            expected_eci,
            "For C25 with granite/gneiss, E_ci should be 28,000 MPa",
        )

    def test_eci_group_2(self, concrete_c60: Concrete) -> None:
        expected_eci = 41_611.92389  # MPa
        assert_approx(
            concrete_c60.eci,
            expected_eci,
            "For C60 with granite/gneiss, E_ci should be approximately 41,611.92389 MPa",
        )

    def test_ecs_group_1(self, concrete_c25: Concrete) -> None:
        expected_ecs = 24_150.0  # MPa
        assert_approx(
            concrete_c25.ecs,
            expected_ecs,
            "For C25 with granite/gneiss, E_cs should be 24,150 MPa",
        )

    def test_ecs_group_2(self, concrete_c60: Concrete) -> None:
        expected_ecs = 39_531.32769  # MPa
        assert_approx(
            concrete_c60.ecs,
            expected_ecs,
            "For C60 with granite/gneiss, E_cs should be approximately 39,531.32769 MPa",
        )

    def test_g_c_group_1(self, concrete_c25: Concrete) -> None:
        expected_g_c = 10_062.5  # MPa
        assert_approx(
            concrete_c25.g_c,
            expected_g_c,
            "For C25 with granite/gneiss, G_c should be 10,062.5 MPa",
        )

    def test_g_c_group_2(self, concrete_c60: Concrete) -> None:
        expected_g_c = 16_471.38654  # MPa
        assert_approx(
            concrete_c60.g_c,
            expected_g_c,
            "For C60 with granite/gneiss, G_c should be approximately 16,471.38654 MPa",
        )


class TestAlphaEAggregate:
    """Tests for the alpha_e factor across every aggregate branch.

    Uses monkeypatch to change the configured aggregate and clears the cached
    alpha_e on the (singleton) enum member before each read.
    """

    def test_basalt(
        self, concrete_c25: Concrete, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(APP_CONFIG, "aggregate", "basalt")
        _clear_cached_property(concrete_c25, "alpha_e")
        expected_alpha_e = 1.2
        assert concrete_c25.alpha_e == expected_alpha_e, (
            "For basalt aggregate, alpha_e should be 1.2"
        )

    def test_diabase(
        self, concrete_c25: Concrete, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(APP_CONFIG, "aggregate", "diabase")
        _clear_cached_property(concrete_c25, "alpha_e")
        expected_alpha_e = 1.2
        assert concrete_c25.alpha_e == expected_alpha_e, (
            "For diabase aggregate, alpha_e should be 1.2"
        )

    def test_granite(
        self, concrete_c25: Concrete, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(APP_CONFIG, "aggregate", "granite")
        _clear_cached_property(concrete_c25, "alpha_e")
        expected_alpha_e = 1.0
        assert concrete_c25.alpha_e == expected_alpha_e, (
            "For granite aggregate, alpha_e should be 1.0"
        )

    def test_gneiss(
        self, concrete_c25: Concrete, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(APP_CONFIG, "aggregate", "gneiss")
        _clear_cached_property(concrete_c25, "alpha_e")
        expected_alpha_e = 1.0
        assert concrete_c25.alpha_e == expected_alpha_e, (
            "For gneiss aggregate, alpha_e should be 1.0"
        )

    def test_limestone(
        self, concrete_c25: Concrete, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(APP_CONFIG, "aggregate", "limestone")
        _clear_cached_property(concrete_c25, "alpha_e")
        expected_alpha_e = 0.9
        assert concrete_c25.alpha_e == expected_alpha_e, (
            "For limestone aggregate, alpha_e should be 0.9"
        )

    def test_sandstone(
        self, concrete_c25: Concrete, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(APP_CONFIG, "aggregate", "sandstone")
        _clear_cached_property(concrete_c25, "alpha_e")
        expected_alpha_e = 0.7
        assert concrete_c25.alpha_e == expected_alpha_e, (
            "For sandstone aggregate, alpha_e should be 0.7"
        )

    def test_unknown_aggregate_raises(
        self, concrete_c25: Concrete, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(APP_CONFIG, "aggregate", "unobtainium")
        _clear_cached_property(concrete_c25, "alpha_e")
        with pytest.raises(ValueError, match="Unknown aggregate type"):
            _ = concrete_c25.alpha_e


class TestStressBlockFactors:
    """Tests for the Rüsch, brittleness, and stress block factors."""

    def test_alpha_c_group_1(self, concrete_c25: Concrete) -> None:
        expected_alpha_c = 0.85
        assert_approx(
            concrete_c25.alpha_c,
            expected_alpha_c,
            "For C25, alpha_c should be 0.85",
        )

    def test_alpha_c_group_2(self, concrete_c60: Concrete) -> None:
        expected_alpha_c = 0.8075
        assert_approx(
            concrete_c60.alpha_c,
            expected_alpha_c,
            "For C60, alpha_c should be approximately 0.8075",
        )

    def test_eta_c_group_1(self, concrete_c25: Concrete) -> None:
        expected_eta_c = 1.0
        assert_approx(
            concrete_c25.eta_c,
            expected_eta_c,
            "For C25, eta_c should be 1.0",
        )

    def test_eta_c_group_2(self, concrete_c60: Concrete) -> None:
        expected_eta_c = 0.87358
        assert_approx(
            concrete_c60.eta_c,
            expected_eta_c,
            "For C60, eta_c should be approximately 0.87358",
        )

    def test_lambda_c_group_1(self, concrete_c25: Concrete) -> None:
        expected_lambda_c = 0.8
        assert_approx(
            concrete_c25.lambda_c,
            expected_lambda_c,
            "For C25, lambda_c should be 0.8",
        )

    def test_lambda_c_group_2(self, concrete_c60: Concrete) -> None:
        expected_lambda_c = 0.775
        assert_approx(
            concrete_c60.lambda_c,
            expected_lambda_c,
            "For C60, lambda_c should be 0.775",
        )


class TestStrains:
    """Tests for the compressive strain limits."""

    def test_epsilon_c2_group_1(self, concrete_c25: Concrete) -> None:
        expected_epsilon_c2 = 0.002
        assert_approx(
            concrete_c25.epsilon_c2,
            expected_epsilon_c2,
            "For C25, epsilon_c2 should be 0.002",
        )

    def test_epsilon_c2_group_2(self, concrete_c60: Concrete) -> None:
        expected_epsilon_c2 = 0.00228802
        assert_approx(
            concrete_c60.epsilon_c2,
            expected_epsilon_c2,
            "For C60, epsilon_c2 should be approximately 0.00228802",
        )

    def test_epsilon_cu_group_1(self, concrete_c25: Concrete) -> None:
        expected_epsilon_cu = 0.0035
        assert_approx(
            concrete_c25.epsilon_cu,
            expected_epsilon_cu,
            "For C25, epsilon_cu should be 0.0035",
        )

    def test_epsilon_cu_group_2(self, concrete_c60: Concrete) -> None:
        expected_epsilon_cu = 0.0028835
        assert_approx(
            concrete_c60.epsilon_cu,
            expected_epsilon_cu,
            "For C60, epsilon_cu should be approximately 0.0028835",
        )


class TestCompressiveStrength:
    """Tests for the design compressive strength and equivalent uniform stress."""

    def test_fcd_group_1(self, concrete_c25: Concrete) -> None:
        expected_fcd = 1.78571  # kN/cm²
        assert_approx(
            concrete_c25.fcd,
            expected_fcd,
            "For C25, fcd should be approximately 1.78571 kN/cm²",
        )

    def test_fcd_group_2(self, concrete_c60: Concrete) -> None:
        expected_fcd = 4.28571  # kN/cm²
        assert_approx(
            concrete_c60.fcd,
            expected_fcd,
            "For C60, fcd should be approximately 4.28571 kN/cm²",
        )

    def test_uniform_stress_group_1(self, concrete_c25: Concrete) -> None:
        expected_uniform_stress = 1.51786  # kN/cm²
        assert_approx(
            concrete_c25.uniform_stress,
            expected_uniform_stress,
            "For C25, the uniform stress should be approximately 1.51786 kN/cm²",
        )

    def test_uniform_stress_group_2(self, concrete_c60: Concrete) -> None:
        expected_uniform_stress = 3.02321  # kN/cm²
        assert_approx(
            concrete_c60.uniform_stress,
            expected_uniform_stress,
            "For C60, the uniform stress should be approximately 3.02321 kN/cm²",
        )


class TestTensileStrength:
    """Tests for the tensile strength values in kN/cm²."""

    def test_fct_m_group_1(self, concrete_c25: Concrete) -> None:
        expected_fct_m = 0.2564964  # kN/cm²
        assert_approx(
            concrete_c25.fct_m,
            expected_fct_m,
            "For C25, fct_m should be approximately 0.2564964 kN/cm²",
        )

    def test_fct_m_group_2(self, concrete_c60: Concrete) -> None:
        expected_fct_m = 0.43547  # kN/cm²
        assert_approx(
            concrete_c60.fct_m,
            expected_fct_m,
            "For C60, fct_m should be approximately 0.43547 kN/cm²",
        )

    def test_fctk_sup_group_1(self, concrete_c25: Concrete) -> None:
        expected_fctk_sup = 0.33344531  # kN/cm²
        assert_approx(
            concrete_c25.fctk_sup,
            expected_fctk_sup,
            "For C25, fctk_sup should be approximately 0.33344531 kN/cm²",
        )

    def test_fctk_inf_group_1(self, concrete_c25: Concrete) -> None:
        expected_fctk_inf = 0.17954747  # kN/cm²
        assert_approx(
            concrete_c25.fctk_inf,
            expected_fctk_inf,
            "For C25, fctk_inf should be approximately 0.17954747 kN/cm²",
        )

    def test_fctd_group_1(self, concrete_c25: Concrete) -> None:
        expected_fctd = 0.1282482  # kN/cm²
        assert_approx(
            concrete_c25.fctd,
            expected_fctd,
            "For C25, fctd should be approximately 0.1282482 kN/cm²",
        )

    def test_fctd_group_2(self, concrete_c60: Concrete) -> None:
        expected_fctd = 0.21774  # kN/cm²
        assert_approx(
            concrete_c60.fctd,
            expected_fctd,
            "For C60, fctd should be approximately 0.21774 kN/cm²",
        )


class TestShearFactor:
    """Tests for the alpha_v2 shear factor."""

    def test_alpha_v2_group_1(self, concrete_c25: Concrete) -> None:
        expected_alpha_v2 = 0.9
        assert_approx(
            concrete_c25.alpha_v2,
            expected_alpha_v2,
            "For C25, alpha_v2 should be 0.9",
        )

    def test_alpha_v2_group_2(self, concrete_c60: Concrete) -> None:
        expected_alpha_v2 = 0.76
        assert_approx(
            concrete_c60.alpha_v2,
            expected_alpha_v2,
            "For C60, alpha_v2 should be 0.76",
        )


class TestDensity:
    """Tests for the concrete density static method in kN/m³."""

    def test_reinforced_density(self) -> None:
        expected_density = 25.0  # kN/m³
        assert Concrete.density(reinforced=True) == expected_density, (
            "Reinforced concrete density should be 25.0 kN/m³"
        )

    def test_plain_density(self) -> None:
        expected_density = 24.0  # kN/m³
        assert Concrete.density(reinforced=False) == expected_density, (
            "Plain concrete density should be 24.0 kN/m³"
        )
