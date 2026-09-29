"""Unit tests for the SectionPropertiesCalculator geometric helpers."""

import pytest

from src.properties.section_properties_calculator import SectionPropertiesCalculator
from tests.helpers import assert_approx


@pytest.fixture
def width_cm() -> float:
    return 20.0


@pytest.fixture
def height_cm() -> float:
    return 60.0


class TestRectangularProperties:
    """Tests for the rectangular-section geometric properties."""

    def test_moment_of_inertia(self, width_cm: float, height_cm: float) -> None:
        expected_moment_of_inertia = 360_000.0  # cm⁴
        actual_moment_of_inertia = SectionPropertiesCalculator.moment_of_inertia(
            width_cm, height_cm
        )
        assert_approx(
            actual_moment_of_inertia,
            expected_moment_of_inertia,
            "Moment of inertia for a 20 cm x 60 cm section should be 360,000 cm⁴",
        )

    def test_cross_sectional_area(self, width_cm: float, height_cm: float) -> None:
        expected_area = 1_200.0  # cm²
        actual_area = SectionPropertiesCalculator.rectangular_cross_sectional_area(
            width_cm, height_cm
        )
        assert_approx(
            actual_area,
            expected_area,
            "Cross-sectional area for a 20 cm x 60 cm section should be 1,200 cm²",
        )

    def test_gross_section_modulus(self, width_cm: float, height_cm: float) -> None:
        expected_modulus = 12_000.0  # cm³
        actual_modulus = SectionPropertiesCalculator.gross_section_modulus(
            width_cm, height_cm
        )
        assert_approx(
            actual_modulus,
            expected_modulus,
            "Gross section modulus for a 20 cm x 60 cm section should be 12,000 cm³",
        )


class TestCircularProperties:
    """Tests for the circular-section geometric properties."""

    def test_circular_cross_sectional_area(self) -> None:
        diameter_cm = 20.0
        expected_area = 314.15927  # cm²
        actual_area = SectionPropertiesCalculator.circular_cross_sectional_area(
            diameter_cm
        )
        assert_approx(
            actual_area,
            expected_area,
            "Cross-sectional area for a 20 cm diameter circle should be 314.15927 cm²",
        )


class TestCrackedSectionMomentOfInertia:
    """Tests for the cracked (stage II) moment of inertia."""

    def test_tension_reinforcement_only(self) -> None:
        width_cm = 20.0
        effective_depth_cm = 55.0
        tension_reinforcement_area_cm2 = 10.0
        modular_ratio = 10.0
        expected_i_ii = 175_326.45827  # cm⁴
        actual_i_ii = (
            SectionPropertiesCalculator.cracked_section_moment_of_inertia(
                width_cm,
                effective_depth_cm,
                tension_reinforcement_area_cm2,
                modular_ratio,
            )
        )
        assert_approx(
            actual_i_ii,
            expected_i_ii,
            "Cracked moment of inertia for the tension-only section should be "
            "approximately 175,326.45827 cm⁴",
        )

    def test_doubly_reinforced_section(self) -> None:
        width_cm = 20.0
        effective_depth_cm = 55.0
        tension_reinforcement_area_cm2 = 10.0
        modular_ratio = 10.0
        compression_reinforcement_area_cm2 = 3.0
        compression_distance_cm = 5.0
        expected_i_ii = 180_318.67793  # cm⁴
        actual_i_ii = (
            SectionPropertiesCalculator.cracked_section_moment_of_inertia(
                width_cm,
                effective_depth_cm,
                tension_reinforcement_area_cm2,
                modular_ratio,
                compression_reinforcement_area_cm2,
                compression_distance_cm,
            )
        )
        assert_approx(
            actual_i_ii,
            expected_i_ii,
            "Cracked moment of inertia for the doubly-reinforced section should be "
            "approximately 180,318.67793 cm⁴",
        )

    def test_negative_discriminant_raises(self) -> None:
        width_cm = 20.0
        negative_effective_depth_cm = -55.0
        tension_reinforcement_area_cm2 = 10.0
        modular_ratio = 10.0
        with pytest.raises(ArithmeticError, match="discriminant"):
            SectionPropertiesCalculator.cracked_section_moment_of_inertia(
                width_cm,
                negative_effective_depth_cm,
                tension_reinforcement_area_cm2,
                modular_ratio,
            )
