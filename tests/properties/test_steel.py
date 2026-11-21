"""Unit tests for the Steel enum and its material properties."""

import pytest

from src.errors import StirrupBendUndefinedError
from src.properties.steel import GAMMA_S, Steel
from tests.helpers import assert_approx


@pytest.fixture
def steel_ca25() -> Steel:
    return Steel.CA25


@pytest.fixture
def steel_ca50() -> Steel:
    return Steel.CA50


@pytest.fixture
def steel_ca60() -> Steel:
    return Steel.CA60


class TestSafetyFactor:
    """Tests for the steel safety factor constant."""

    def test_gamma_s(self) -> None:
        expected_gamma_s = 1.15
        assert_approx(
            GAMMA_S,
            expected_gamma_s,
            "The steel safety factor (gamma_s) should be 1.15",
        )


class TestCharacteristicYieldStrength:
    """Tests for the characteristic yield strength (fy) enum values in kN/cm²."""

    def test_ca25_yield_strength(self, steel_ca25: Steel) -> None:
        expected_fy = 25
        assert steel_ca25.value == expected_fy, (
            "For CA-25 steel, fy should be 25 kN/cm²"
        )

    def test_ca50_yield_strength(self, steel_ca50: Steel) -> None:
        expected_fy = 50
        assert steel_ca50.value == expected_fy, (
            "For CA-50 steel, fy should be 50 kN/cm²"
        )

    def test_ca60_yield_strength(self, steel_ca60: Steel) -> None:
        expected_fy = 60
        assert steel_ca60.value == expected_fy, (
            "For CA-60 steel, fy should be 60 kN/cm²"
        )


class TestElasticModulus:
    """Tests for the class-level elastic modulus property."""

    def test_elastic_modulus(self) -> None:
        expected_elastic_modulus = 210_000
        assert Steel.elastic_modulus == expected_elastic_modulus, (
            "The elastic modulus of steel (E_s) should be 210,000 MPa"
        )


class TestDesignYieldStrength:
    """Tests for the design yield strength (fyd) in kN/cm²."""

    def test_ca25_design_yield_strength(self, steel_ca25: Steel) -> None:
        expected_fyd = 21.73913  # kN/cm²
        assert_approx(
            steel_ca25.fyd,
            expected_fyd,
            "For CA-25 steel, fyd should be approximately 21.73913 kN/cm²",
        )

    def test_ca50_design_yield_strength(self, steel_ca50: Steel) -> None:
        expected_fyd = 43.47826  # kN/cm²
        assert_approx(
            steel_ca50.fyd,
            expected_fyd,
            "For CA-50 steel, fyd should be approximately 43.47826 kN/cm²",
        )

    def test_ca60_design_yield_strength(self, steel_ca60: Steel) -> None:
        expected_fyd = 52.17391  # kN/cm²
        assert_approx(
            steel_ca60.fyd,
            expected_fyd,
            "For CA-60 steel, fyd should be approximately 52.17391 kN/cm²",
        )


class TestShearDesignYieldStrength:
    """Tests for the design shear yield strength (fywd), capped at 43.5 kN/cm²."""

    def test_ca25_shear_design_strength(self, steel_ca25: Steel) -> None:
        expected_fywd = 21.73913  # kN/cm²
        assert_approx(
            steel_ca25.fywd,
            expected_fywd,
            "For CA-25 steel, fywd should be approximately 21.73913 kN/cm²",
        )

    def test_ca50_shear_design_strength(self, steel_ca50: Steel) -> None:
        expected_fywd = 43.47826  # kN/cm²
        assert_approx(
            steel_ca50.fywd,
            expected_fywd,
            "For CA-50 steel, fywd should be approximately 43.47826 kN/cm²",
        )

    def test_ca60_shear_design_strength_is_capped(self, steel_ca60: Steel) -> None:
        expected_fywd = 43.5  # kN/cm², capped
        assert_approx(
            steel_ca60.fywd,
            expected_fywd,
            "For CA-60 steel, fywd should be capped at 43.5 kN/cm²",
        )


class TestShearCharacteristicYieldStrength:
    """Tests for the characteristic shear yield strength (fywk), capped at 50 kN/cm²."""

    def test_ca25_shear_characteristic_strength(self, steel_ca25: Steel) -> None:
        expected_fywk = 25  # kN/cm²
        assert steel_ca25.fywk == expected_fywk, (
            "For CA-25 steel, fywk should be 25 kN/cm²"
        )

    def test_ca50_shear_characteristic_strength(self, steel_ca50: Steel) -> None:
        expected_fywk = 50  # kN/cm²
        assert steel_ca50.fywk == expected_fywk, (
            "For CA-50 steel, fywk should be 50 kN/cm²"
        )

    def test_ca60_shear_characteristic_strength_is_capped(
        self, steel_ca60: Steel
    ) -> None:
        expected_fywk = 50  # kN/cm², capped
        assert steel_ca60.fywk == expected_fywk, (
            "For CA-60 steel, fywk should be capped at 50 kN/cm²"
        )


class TestBondCoefficient:
    """Tests for the bond coefficient (eta_1)."""

    def test_ca25_bond_coefficient(self, steel_ca25: Steel) -> None:
        expected_bond_coefficient = 1.00
        assert steel_ca25.bond_coefficient == expected_bond_coefficient, (
            "For CA-25 steel, the bond coefficient should be 1.00"
        )

    def test_ca50_bond_coefficient(self, steel_ca50: Steel) -> None:
        expected_bond_coefficient = 2.25
        assert steel_ca50.bond_coefficient == expected_bond_coefficient, (
            "For CA-50 steel, the bond coefficient should be 2.25"
        )

    def test_ca60_bond_coefficient(self, steel_ca60: Steel) -> None:
        expected_bond_coefficient = 1.00
        assert steel_ca60.bond_coefficient == expected_bond_coefficient, (
            "For CA-60 steel, the bond coefficient should be 1.00"
        )


class TestBendPinDiameter:
    """Tests for the bending pin diameter (D) of hooks, in cm (Table 9.1)."""

    def test_ca25_small_bar(self, steel_ca25: Steel) -> None:
        assert_approx(
            steel_ca25.bend_pin_diameter(10),
            4.0,
            "For CA-25 bars under 20 mm, D should be 4φ (4.0 cm for 10 mm)",
        )

    def test_ca25_large_bar(self, steel_ca25: Steel) -> None:
        assert_approx(
            steel_ca25.bend_pin_diameter(20),
            10.0,
            "For CA-25 bars of 20 mm or more, D should be 5φ (10.0 cm for 20 mm)",
        )

    def test_ca50_small_bar(self, steel_ca50: Steel) -> None:
        assert_approx(
            steel_ca50.bend_pin_diameter(16),
            8.0,
            "For CA-50 bars under 20 mm, D should be 5φ (8.0 cm for 16 mm)",
        )

    def test_ca50_large_bar(self, steel_ca50: Steel) -> None:
        assert_approx(
            steel_ca50.bend_pin_diameter(20),
            16.0,
            "For CA-50 bars of 20 mm or more, D should be 8φ (16.0 cm for 20 mm)",
        )

    def test_ca60_small_bar(self, steel_ca60: Steel) -> None:
        assert_approx(
            steel_ca60.bend_pin_diameter(10),
            6.0,
            "For CA-60 bars under 20 mm, D should be 6φ (6.0 cm for 10 mm)",
        )

    def test_ca60_large_bar_raises(self, steel_ca60: Steel) -> None:
        with pytest.raises(ValueError):
            steel_ca60.bend_pin_diameter(20)


class TestFrameJointBendDiameter:
    """Tests for the bend diameter (cm) of bars bent in a frame joint, NBR 6118 18.2.2."""

    def test_ca25(self, steel_ca25: Steel) -> None:
        assert_approx(
            steel_ca25.frame_joint_bend_diameter(10),
            10.0,
            "For CA-25, D should be 10φ (10.0 cm for 10 mm)",
        )

    def test_ca50(self, steel_ca50: Steel) -> None:
        assert_approx(
            steel_ca50.frame_joint_bend_diameter(16),
            24.0,
            "For CA-50, D should be 15φ (24.0 cm for 16 mm)",
        )

    def test_ca50_large_bar(self, steel_ca50: Steel) -> None:
        assert_approx(
            steel_ca50.frame_joint_bend_diameter(25),
            37.5,
            "For CA-50, D should stay 15φ for φ >= 20 mm (37.5 cm for 25 mm)",
        )

    def test_ca60(self, steel_ca60: Steel) -> None:
        assert_approx(
            steel_ca60.frame_joint_bend_diameter(10),
            18.0,
            "For CA-60, D should be 18φ (18.0 cm for 10 mm)",
        )


class TestStirrupBendDiameter:
    """Tests for the stirrup bend diameter, from Table 9.2 of NBR 6118."""

    @pytest.mark.parametrize(
        ("steel", "diameter_mm", "expected"),
        [
            (Steel.CA25, 10.0, 3.0),
            (Steel.CA50, 6.3, 1.89),
            (Steel.CA50, 10.0, 3.0),
            (Steel.CA60, 10.0, 3.0),
            (Steel.CA25, 12.5, 5.0),
            (Steel.CA50, 12.5, 6.25),
            (Steel.CA25, 20.0, 10.0),
            (Steel.CA50, 20.0, 16.0),
        ],
    )
    def test_table_9_2(self, steel: Steel, diameter_mm: float, expected: float) -> None:
        assert_approx(
            steel.stirrup_bend_diameter(diameter_mm),
            expected,
            f"{steel.name} φ{diameter_mm:g} bend diameter (cm)",
        )

    def test_ca60_above_10_mm_raises(self) -> None:
        with pytest.raises(StirrupBendUndefinedError, match="No stirrup bend diameter"):
            Steel.CA60.stirrup_bend_diameter(12.5)


class TestLinearMass:
    """The nominal linear mass is the section area times 7850 kg/m³ (NBR 7480)."""

    @pytest.mark.parametrize(
        ("diameter_mm", "table_mass"),
        [
            (3.4, 0.071),
            (3.8, 0.089),
            (4.2, 0.109),
            (4.6, 0.130),
            (5.0, 0.154),
            (5.5, 0.187),
            (6.0, 0.222),
            (6.3, 0.245),
            (6.4, 0.253),
            (7.0, 0.302),
            (8.0, 0.395),
            (10.0, 0.617),
            (12.5, 0.963),
            (16.0, 1.578),
            (20.0, 2.466),
            (22.0, 2.984),
            (25.0, 3.853),
            (32.0, 6.313),
            (40.0, 9.865),
        ],
    )
    def test_tables_b1_and_b2(self, diameter_mm: float, table_mass: float) -> None:
        assert_approx(
            Steel.CA50.linear_mass(diameter_mm),
            table_mass,
            f"φ{diameter_mm:g} matches the table to its three decimals (kg/m)",
            abs_tol=0.00051,
        )

    def test_wire_9_5_follows_the_formula(self) -> None:
        """Table B.2 prints 0.558 kg/m, but its own area of 70.9 mm² gives 0.557 kg/m"""
        assert_approx(
            Steel.CA60.linear_mass(9.5),
            0.5564,
            "φ9.5 by the table's footnote formula (kg/m)",
            abs_tol=0.0001,
        )


class TestAvailableSizes:
    """Tests for the available rebar diameters (mm): the NBR 7480 sizes with a SINAPI price."""

    def test_ca25_available_sizes(self, steel_ca25: Steel) -> None:
        expected_sizes: list[float] = [6.3, 8, 10, 12.5, 16, 20, 25, 32]
        assert steel_ca25.available_sizes == expected_sizes, (
            "CA-25 should offer the NBR 7480 diameters that have a SINAPI price"
        )

    def test_ca50_available_sizes(self, steel_ca50: Steel) -> None:
        expected_sizes: list[float] = [6.3, 8, 10, 12.5, 16, 20, 25, 32]
        assert steel_ca50.available_sizes == expected_sizes, (
            "CA-50 should offer the NBR 7480 diameters that have a SINAPI price"
        )

    def test_ca60_available_sizes(self, steel_ca60: Steel) -> None:
        expected_sizes: list[float] = [4.2, 5.0, 6.0, 7.0, 8.0, 9.5]
        assert steel_ca60.available_sizes == expected_sizes, (
            "CA-60 should offer the thin-wire NBR 7480 diameters that have a SINAPI price"
        )

    @pytest.mark.parametrize("steel", [Steel.CA25, Steel.CA50])
    @pytest.mark.parametrize("diameter", [22.0, 40.0])
    def test_unpriced_ribbed_sizes_removed(self, steel: Steel, diameter: float) -> None:
        assert steel.is_size_available(diameter) is False, (
            f"{steel.name} φ{diameter:g} has no SINAPI price and should not be offered"
        )

    @pytest.mark.parametrize("diameter", [3.4, 3.8, 4.6, 5.5, 6.4, 10.0])
    def test_unpriced_ca60_sizes_removed(
        self, steel_ca60: Steel, diameter: float
    ) -> None:
        assert steel_ca60.is_size_available(diameter) is False, (
            f"CA-60 φ{diameter:g} has no SINAPI price and should not be offered"
        )


class TestIsSizeAvailable:
    """Tests for the is_size_available membership check."""

    def test_available_diameter_returns_true(self, steel_ca50: Steel) -> None:
        available_diameter = 12.5
        assert steel_ca50.is_size_available(available_diameter) is True, (
            "A 12.5 mm bar should be available for CA-50 steel"
        )

    def test_unavailable_diameter_returns_false(self, steel_ca50: Steel) -> None:
        unavailable_diameter = 9.5
        assert steel_ca50.is_size_available(unavailable_diameter) is False, (
            "A 9.5 mm bar should not be available for CA-50 steel"
        )

    def test_thin_wire_diameter_available_for_ca60(self, steel_ca60: Steel) -> None:
        available_diameter = 9.5
        assert steel_ca60.is_size_available(available_diameter) is True, (
            "A 9.5 mm bar should be available for CA-60 steel"
        )
