from unittest.mock import Mock, PropertyMock, patch

import pytest

from src.structural_elements.rectangular_beam import RectangularBeam
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.calculators.rebar_calculator import RebarCalculator


@pytest.fixture
def calculator() -> RebarCalculator:
    # Create a stub RectangularBeam
    beam = Mock(spec=RectangularBeam)
    beam.width = 20  # cm
    beam.height = 60  # cm
    beam.concrete = Concrete.C25
    beam.steel = Steel.CA50
    beam.area = 1200  # cm^2
    with patch.object(RectangularBeam, "nominal_covering", new_callable=PropertyMock) as mock_nominal_covering:
        mock_nominal_covering.return_value = 3

        bending_moment = 272  # kN.m
        stirrups = Mock()
        calculator = RebarCalculator(beam, bending_moment, stirrups, beam.length / 2, "Test Beam")
        calculator.d = 56  # cm (effective depth)
        calculator.d_compressed = 4  # cm (distance from compression face to centroid of compression reinforcement)
        return calculator


def test_max_y(calculator: RebarCalculator):
    expected_y_max = 20.160000000000004  # cm
    actual_y_max = calculator.max_y
    assert pytest.approx(expected_y_max) == pytest.approx(actual_y_max), (
        "Calculated y_max should match the expected value of 20.16 cm"
    )


def test_max_bending_moment(calculator: RebarCalculator):
    expected_max_bending_moment = 28103.04  # cm
    actual_max_bending_moment = calculator.max_bending_moment
    assert pytest.approx(expected_max_bending_moment) == pytest.approx(
        actual_max_bending_moment
    ), "Calculated max bending moment should match the expected value of 28103.04 cm"


def test_min_tension_rebar_area(calculator: RebarCalculator):
    expected_min_tension__rebararea = 1.7999999999999998
    # cm^2
    actual_min_area = calculator.min_tension_rebar_area
    assert pytest.approx(expected_min_tension__rebararea) == pytest.approx(
        actual_min_area
    ), "Min tension rebar area for 20x60 cm beam should be 1.7999999999999998 cm^2"


def test_max_rebar_area(calculator: RebarCalculator):
    expected_max_area = 48  # cm^2
    actual_max_area = calculator.max_rebar_area
    assert expected_max_area == pytest.approx(actual_max_area), (
        "Max rebar area for 20x60 cm beam should be 48 cm^2"
    )


def test_design_bending_moment(calculator: RebarCalculator):
    expected_design_bending_moment = 38080.0  # kN.cm
    actual_design_bending_moment = calculator.design_bending_moment
    assert pytest.approx(expected_design_bending_moment) == pytest.approx(
        actual_design_bending_moment
    ), "Design bending moment should be 38080 kN.cm for a bending moment of 272 kN.m"


def test_calculate_delta_bending_moment(calculator: RebarCalculator):
    expected_delta_bending_moment = 9976.96  # kN.cm
    actual_delta_bending_moment = calculator.calculate_delta_bending_moment()
    assert pytest.approx(expected_delta_bending_moment) == pytest.approx(
        actual_delta_bending_moment
    ), (
        "Delta bending moment should be 9976.96 kN.cm for a design bending moment of 38080 kN.cm and a bending moment of 27200 kN.cm"
    )


def test_is_singly_reinforced(calculator: RebarCalculator):
    assert not calculator.is_singly_reinforced, (
        "Beam should NOT be singly reinforced for the given bending moment and properties"
    )


def test_as1(calculator: RebarCalculator):
    expected_as1 = 14.075999999999999  # cm^2
    actual_as1 = calculator.as1
    assert pytest.approx(expected_as1) == pytest.approx(actual_as1), (
        "Area of tension reinforcement (As1) should be 14.076 cm^2 for the given properties and bending moment"
    )


def test_epsilon_s2(calculator: RebarCalculator):
    expected_epsilon_s2 = 0.002944444444444445  # dimensionless
    actual_epsilon_s2 = calculator.calculate_epsilon_s2()
    assert pytest.approx(expected_epsilon_s2) == pytest.approx(actual_epsilon_s2), (
        "Strain in compression reinforcement (epsilon_s2) should be 0.002944444444444445 for the given properties and bending moment"
    )


def test_sigma_s2(calculator: RebarCalculator):
    expected_sigma_s2 = 43.47826086956522  # kN/cm^2
    actual_sigma_s2 = calculator.calculate_sigma_s2()
    assert pytest.approx(expected_sigma_s2) == pytest.approx(actual_sigma_s2), (
        "Stress in compression reinforcement (sigma_s2) should be 43.47826086956522 kN/cm^2 for the given properties and bending moment"
    )


def test_corrected_sigma_s2(calculator: RebarCalculator):
    expected_corrected_sigma_s2 = 41.96040372670807  # kN/cm^2
    actual_corrected_sigma_s2 = calculator.corrected_sigma_s2
    assert pytest.approx(expected_corrected_sigma_s2) == pytest.approx(
        actual_corrected_sigma_s2
    ), (
        "Corrected stress in compression reinforcement (corrected_sigma_s2) should be 41.96040372670807 kN/cm^2 for the given properties and bending moment"
    )


def test_compressed_rebar_area(calculator: RebarCalculator):
    expected_as_comp = 4.572515951806543  # cm^2
    actual_as_comp = calculator.compressed_rebar_area
    assert pytest.approx(expected_as_comp) == pytest.approx(actual_as_comp), (
        "Area of compression reinforcement (As_comp) should be 4.572515951806543 cm^2 for the given properties and bending moment"
    )


def test_delta_as(calculator: RebarCalculator):
    expected_delta_as = 4.412886153846154  # cm^2
    actual_delta_as = calculator.calculate_delta_as()
    assert pytest.approx(expected_delta_as) == pytest.approx(actual_delta_as), (
        "Delta area of reinforcement (delta_as) should be 4.412886153846154 cm^2 for the given properties and bending moment"
    )


def test_tensioned_rebar_area(calculator: RebarCalculator):
    expected_a_s = 18.488886153846155  # cm^2
    actual_a_s = calculator.tensioned_rebar_area
    assert pytest.approx(expected_a_s) == pytest.approx(actual_a_s), (
        "Total area of tension reinforcement (As) should be 18.488886153846155 cm^2 for the given properties and bending moment"
    )


def test_calculate_and_set_required_reinforcement(calculator: RebarCalculator):
    expected_tensioned_rebar_area = 18.488886153846155  # cm^2
    calculator.calculate_and_set_required_tensioned_rebar_area()
    actual_tensioned_rebar_area = calculator.tensioned_rebar_area
    assert pytest.approx(expected_tensioned_rebar_area) == pytest.approx(
        actual_tensioned_rebar_area
    ), (
        "After calculating and setting required reinforcement, the total area of tension reinforcement (As) should be 18.488886153846155 cm^2 for the given properties and bending moment.\nAlso, it shouldn't throw any exceptions during the calculation and setting process."
    )
