from src.properties.section_properties_calculator import SectionPropertiesCalculator as SPC
import pytest

@pytest.fixture
def width_20() -> int:
    return 20

@pytest.fixture
def height_60() -> int:
    return 60

def test_moment_of_inertia(width_20: int, height_60: int):
    expected_moi = 360_000
    actual_moi = SPC.moment_of_inertia(width_20, height_60)
    assert actual_moi == expected_moi, "Moment of inertia for a 20 cm x 60 cm section should be 360,000 cm⁴"

def test_cross_sectional_area(width_20: int, height_60: int):
    expected_area = 1_200
    actual_area = SPC.rectangular_cross_sectional_area(width_20, height_60)
    assert actual_area == expected_area, "Cross-sectional area for a 20 cm x 60 cm section should be 1,200 cm²"

def test_gross_section_modulus(width_20: int, height_60: int):
    expected_modulus = 12_000
    actual_modulus = SPC.gross_section_modulus(width_20, height_60)
    assert actual_modulus == expected_modulus, "Gross section modulus for a 20 cm x 60 cm section should be 12,000 cm³"