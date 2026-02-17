from src.properties.concrete import Concrete
import pytest

@pytest.fixture
def concrete_fck_25() -> Concrete:
    return Concrete.C25

def test_concrete_group(concrete_fck_25: Concrete):
    expected_group = 1
    assert concrete_fck_25.concrete_group == expected_group, "For concrete with fck 25 MPa, the concrete group should be 1"

def test_eci(concrete_fck_25: Concrete):
    # IMPLEMENT
    pass

def test_ecs(concrete_fck_25: Concrete):
    # IMPLEMENT
    pass

def test_g_c(concrete_fck_25: Concrete):
    # IMPLEMENT
    pass

def test_fcd(concrete_fck_25: Concrete):
    expected_fcd = 25 / 1.4
    assert concrete_fck_25.fcd == pytest.approx(expected_fcd), "For concrete with fck 25 MPa, fcd should be approximately 17.86 MPa"

def test_alpha_c(concrete_fck_25: Concrete):
    expected_alpha_c = 0.85
    assert concrete_fck_25.alpha_c == pytest.approx(expected_alpha_c), "For concrete with fck 25 MPa, alpha_c should be 0.85"

def test_eta_c(concrete_fck_25: Concrete):
    expected_eta_c = 1.0
    assert concrete_fck_25.eta_c == pytest.approx(expected_eta_c), "For concrete with fck 25 MPa, eta_c should be 1.0"

def test_uniform_stress(concrete_fck_25: Concrete):
    expected_uniform_stress = 0.85 * (25 / 1.4) * 1.0
    assert concrete_fck_25.calculate_uniform_stress() == pytest.approx(expected_uniform_stress), "For concrete with fck 25 MPa, the uniform stress should be approximately 15.21 MPa"

def test_lambda_c(concrete_fck_25: Concrete):
    expected_lambda_c = 0.8
    assert concrete_fck_25.lambda_c == pytest.approx(expected_lambda_c), "For concrete with fck 25 MPa, lambda_c should be 0.8"

def test_epsilon_c2(concrete_fck_25: Concrete):
    # IMPLEMENT
    pass

def test_epsilon_cu(concrete_fck_25: Concrete):
    # IMPLEMENT
    pass