"""Unit tests for the loading force and combination functions."""

import types
from typing import cast

import pytest

from src.loading.forces import (
    almost_permanent_combination_els,
    calculate_cracking_moment,
    design_effort_elu,
    max_design_bending_moment,
    min_design_bending_moment,
    normal_elu_combination,
)
from src.properties.concrete import Concrete
from src.structural_elements.rectangular_beam import RectangularBeam
from tests.helpers import assert_approx


@pytest.fixture
def beam_c25_20x60() -> RectangularBeam:
    """Minimal duck-typed C25 beam, 20 cm wide by 60 cm tall.

    Uses ``types.SimpleNamespace`` rather than a mock so that any access to an
    attribute the production code does not expect fails loudly. The nested
    concrete namespace is built from the real ``Concrete.C25`` member so the
    reference values stay in sync with the material definition. The result is
    cast to ``RectangularBeam`` because the functions under test only read the
    ``width``, ``height``, and ``concrete`` attributes.
    """
    beam = types.SimpleNamespace(
        width=20.0,
        height=60.0,
        concrete=types.SimpleNamespace(
            uniform_stress=Concrete.C25.uniform_stress,
            fctk_sup=Concrete.C25.fctk_sup,
        ),
    )
    return cast(RectangularBeam, beam)


class TestDesignEffortElu:
    """Tests for the ELU design effort load-factor application."""

    def test_positive(self) -> None:
        expected_effort = 140.0  # kN.cm
        assert_approx(
            design_effort_elu(100.0),
            expected_effort,
            "Applying gamma_f = 1.4 to 100 should give 140",
        )

    def test_zero(self) -> None:
        expected_effort = 0.0
        assert design_effort_elu(0.0) == expected_effort, (
            "Zero bending moment should give zero design effort"
        )

    def test_negative(self) -> None:
        expected_effort = -70.0  # kN.cm
        assert_approx(
            design_effort_elu(-50.0),
            expected_effort,
            "Applying gamma_f = 1.4 to -50 should give -70",
        )


class TestMaxDesignBendingMoment:
    """Tests for the maximum design bending moment of a singly reinforced beam."""

    def test_known_values_c25_20x60(self, beam_c25_20x60: RectangularBeam) -> None:
        expected_moment = 15178.57143  # kN.cm
        assert_approx(
            max_design_bending_moment(beam_c25_20x60, d=55.0, y_max=10.0),
            expected_moment,
            "For C25 20x60 with d=55 and y_max=10, M_max should be ~15178.57143 kN.cm",
        )


class TestMinDesignBendingMoment:
    """Tests for the minimum design bending moment from minimum rebar area."""

    def test_known_values_c25_20x60(self, beam_c25_20x60: RectangularBeam) -> None:
        expected_moment = 3201.07497  # kN.cm
        assert_approx(
            min_design_bending_moment(beam_c25_20x60),
            expected_moment,
            "For C25 20x60, M_min should be ~3201.07497 kN.cm",
        )


class TestAlmostPermanentCombinationEls:
    """Tests for the almost permanent load combination (CQP) for ELS."""

    def test_residential_factor(self) -> None:
        expected_combination = 23.0  # kN (20 + 0.3 * 10)
        assert_approx(
            almost_permanent_combination_els(20.0, 10.0, psi_2=0.3),
            expected_combination,
            "20 permanent + 0.3 * 10 variable should give 23",
        )

    def test_commercial_factor(self) -> None:
        expected_combination = 36.0  # kN (30 + 0.4 * 15)
        assert_approx(
            almost_permanent_combination_els(30.0, 15.0, psi_2=0.4),
            expected_combination,
            "30 permanent + 0.4 * 15 variable should give 36",
        )

    def test_storage_factor(self) -> None:
        expected_combination = 39.0  # kN (30 + 0.6 * 15)
        assert_approx(
            almost_permanent_combination_els(30.0, 15.0, psi_2=0.6),
            expected_combination,
            "30 permanent + 0.6 * 15 variable should give 39",
        )

    def test_zero_loads(self) -> None:
        expected_combination = 0.0
        assert (
            almost_permanent_combination_els(0.0, 0.0, psi_2=0.6)
            == expected_combination
        ), "Zero loads should give a zero combination"


class TestNormalEluCombination:
    """Tests for the normal ELU load combination applying gamma_f = 1.4."""

    def test_known_loads(self) -> None:
        expected_combination = 42.0  # kN (1.4 * (20 + 10))
        assert_approx(
            normal_elu_combination(20.0, 10.0),
            expected_combination,
            "1.4 * (20 + 10) should give 42",
        )

    def test_only_permanent(self) -> None:
        expected_combination = 21.0  # kN (1.4 * 15)
        assert_approx(
            normal_elu_combination(15.0, 0.0),
            expected_combination,
            "1.4 * (15 + 0) should give 21",
        )

    def test_zero_loads(self) -> None:
        expected_combination = 0.0
        assert normal_elu_combination(0.0, 0.0) == expected_combination, (
            "Zero loads should give a zero combination"
        )


class TestCalculateCrackingMoment:
    """Tests for the cracking moment (M_r) of a rectangular section."""

    def test_known_values(self) -> None:
        expected_moment = 4500.0  # kN.cm (1.5 * 0.25 * 360000 / 30)
        assert_approx(
            calculate_cracking_moment(0.25, 30.0, 360000.0),
            expected_moment,
            "1.5 * 0.25 * 360000 / 30 should give 4500 kN.cm",
        )

    def test_scales_with_inertia(self) -> None:
        expected_moment = 9000.0  # kN.cm (doubling inertia doubles M_r)
        assert_approx(
            calculate_cracking_moment(0.25, 30.0, 720000.0),
            expected_moment,
            "Doubling the moment of inertia should double the cracking moment",
        )
