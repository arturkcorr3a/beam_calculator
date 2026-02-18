from src.reinforcement.rebar_calculator import RebarCalculator
from src.properties.concrete import Concrete
from src.properties.steel import Steel
import pytest
from unittest.mock import Mock

@pytest.fixture
def calculator() -> RebarCalculator:
    # Create a stub RectangularBeam
    beam = Mock()
    beam.width = 20  # cm
    beam.height = 60  # cm
    beam.concrete = Concrete.C25
    beam.steel = Steel.CA50
    beam._A = 1200  # cm^2
    beam.nominal_covering = 3  # cm
    
    bending_moment = 272  # kN.m
    return RebarCalculator(beam, bending_moment)

def test_max_rebar_area(calculator: RebarCalculator):
    expected_max_area = 48 # cm^2
    actual_max_area = calculator.max_rebar_area
    assert expected_max_area == pytest.approx(actual_max_area), "Max rebar area for 20x60 cm beam should be 48 cm^2"

def test_is_singly_reinforced(calculator: RebarCalculator):
    assert not calculator.is_singly_reinforced, "Beam should NOT be singly reinforced for the given bending moment and properties"