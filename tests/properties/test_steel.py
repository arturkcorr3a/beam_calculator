from src.properties.steel import Steel
import pytest

@pytest.fixture
def steel_ca50() -> Steel:
    return Steel.CA50

def test_fyd(steel_ca50: Steel):
    expected_fyd = 50 / 1.15
    assert steel_ca50.fyd == pytest.approx(expected_fyd), "For CA-50 steel, fyd should be approximately 43.48 kN/cm²"

def test_elastic_modulus(steel_ca50: Steel):
    expected_elastic_modulus = 210_000
    assert steel_ca50.elastic_modulus == expected_elastic_modulus, "The elastic modulus of steel should be 210,000 MPa"

def test_available_sizes(steel_ca50: Steel):
    # IMPLEMENT teste
    pass