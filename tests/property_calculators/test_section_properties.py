from properties.section_properties_calculator import cross_sectional_area
import pytest

# IMPLEMENT create better tests for functions
# perhaps, have two full examples of beams with known results and create all the tests for the same examples
def test_cross_sectional_area():
    A = cross_sectional_area(0.3, 0.5)
    assert A == pytest.approx(0.15), "Cross-sectional area calculation is incorrect."