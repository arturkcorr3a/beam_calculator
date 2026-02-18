from src.properties.concrete import Concrete
import pytest

@pytest.fixture
def concrete_fck_25() -> Concrete:
    return Concrete.C25

def test_concrete_group(concrete_fck_25: Concrete):
    expected_group = 1
    assert concrete_fck_25.concrete_group == expected_group, "For concrete with fck 25 MPa, the concrete group should be 1"

def test_eci(concrete_fck_25: Concrete):
    expected_eci = 28_000 # MPa
    assert concrete_fck_25.eci == pytest.approx(expected_eci), "For concrete with fck 25 MPa and granite/gnaisse, the initial elastic modulus (E_ci) should be 28,000 MPa"

def test_ecs(concrete_fck_25: Concrete):
    expected_ecs = 24_150 # MPa
    assert concrete_fck_25.ecs == pytest.approx(expected_ecs), "For concrete with fck 25 MPa and granite/gnaisse, the secant elastic modulus (E_cs) should be approximately 24,150 MPa"

def test_g_c(concrete_fck_25: Concrete):
    expected_g_c = 10_062.5 # MPa
    assert concrete_fck_25.g_c == pytest.approx(expected_g_c), "For concrete with fck 25 MPa and granite/gnaisse, the shear modulus (G_c) should be approximately 10,062.5 MPa"

def test_fcd(concrete_fck_25: Concrete):
    expected_fcd = 2.5 / 1.4
    assert concrete_fck_25.fcd == pytest.approx(expected_fcd), "For concrete with fck 25 MPa, fcd should be approximately 1.786 kN/cm²"

def test_alpha_c(concrete_fck_25: Concrete):
    expected_alpha_c = 0.85
    assert concrete_fck_25.alpha_c == pytest.approx(expected_alpha_c), "For concrete with fck 25 MPa, alpha_c should be 0.85"

def test_eta_c(concrete_fck_25: Concrete):
    expected_eta_c = 1.0
    assert concrete_fck_25.eta_c == pytest.approx(expected_eta_c), "For concrete with fck 25 MPa, eta_c should be 1.0"

def test_uniform_stress(concrete_fck_25: Concrete):
    expected_uniform_stress = 0.85 * (2.5 / 1.4) * 1.0
    assert concrete_fck_25.calculate_uniform_stress() == pytest.approx(expected_uniform_stress), "For concrete with fck 25 MPa, the uniform stress should be approximately 1.521 kN/cm²"

def test_lambda_c(concrete_fck_25: Concrete):
    expected_lambda_c = 0.8
    assert concrete_fck_25.lambda_c == pytest.approx(expected_lambda_c), "For concrete with fck 25 MPa, lambda_c should be 0.8"

def test_epsilon_c2(concrete_fck_25: Concrete):
    expected_epsilon_c2 = 2.0 / 1_000
    assert concrete_fck_25.epsilon_c2 == pytest.approx(expected_epsilon_c2), "For concrete with fck 25 MPa, epsilon_c2 should be 0.002"

def test_epsilon_cu(concrete_fck_25: Concrete):
    expected_epsilon_cu = 3.5 / 1_000
    assert concrete_fck_25.epsilon_cu == pytest.approx(expected_epsilon_cu), "For concrete with fck 25 MPa, epsilon_cu should be 0.0035"
    