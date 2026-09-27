"""Unit tests for BeamDeformationChecker.

All indeterminatebeam-backed calls are intercepted with a ``Mock(spec=RectangularBeam)``
so these tests remain fast and do not depend on structural-solver internals.
"""

from typing import cast
from unittest.mock import Mock

import pytest

from src.checkers.beam_deformation_checker import BeamDeformationChecker
from src.properties.concrete import Concrete
from src.structural_elements.rectangular_beam import RectangularBeam
from tests.helpers import assert_approx

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def beam_mock() -> RectangularBeam:
    """Return a Mock(spec=RectangularBeam) with canned bending-moment and deflection.

    Canned values:
        get_bending_moment(return_absmax=True) → 42.0 kN.m
        get_deflection(return_absmax=True)     → 0.85 cm
    """
    mock = Mock(spec=RectangularBeam)
    mock.get_bending_moment.return_value = 42.0
    mock.get_deflection.return_value = 0.85
    return cast(RectangularBeam, mock)


@pytest.fixture
def beam_checker(beam_mock: RectangularBeam) -> BeamDeformationChecker:
    """Return a BeamDeformationChecker backed by a mocked RectangularBeam."""
    return BeamDeformationChecker(
        permanent_load=10.0,
        variable_load=5.0,
        concrete=Concrete.C30,
        span=500.0,
        width=20.0,
        effective_depth_discount=4.0,
        compressed_reinforcement_area=0.0,
        effective_depth_compressed=0.0,
        tensioned_reinforcement_area=5.0,
        structural_beam=beam_mock,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestServiceMoment:
    """Tests for BeamDeformationChecker.service_moment."""

    def test_returns_beam_absmax_bending_moment(
        self, beam_checker: BeamDeformationChecker
    ) -> None:
        """service_moment returns the value forwarded from get_bending_moment."""
        assert_approx(
            beam_checker.service_moment,
            42.0,
            "service_moment should equal get_bending_moment(return_absmax=True) (kN.m)",
        )

    def test_calls_structural_beam_with_return_absmax(
        self,
        beam_checker: BeamDeformationChecker,
        beam_mock: RectangularBeam,
    ) -> None:
        """service_moment calls get_bending_moment with return_absmax=True."""
        _ = beam_checker.service_moment
        mock = cast(Mock, beam_mock)
        mock.get_bending_moment.assert_called_once_with(return_absmax=True)


class TestImmediateDeflection:
    """Tests for BeamDeformationChecker.immediate_deflection."""

    def test_returns_beam_absmax_deflection(
        self, beam_checker: BeamDeformationChecker
    ) -> None:
        """immediate_deflection returns the value forwarded from get_deflection."""
        assert_approx(
            beam_checker.immediate_deflection,
            0.85,
            "immediate_deflection should equal get_deflection(return_absmax=True) (cm)",
        )

    def test_calls_get_deflection_with_return_absmax(
        self,
        beam_checker: BeamDeformationChecker,
        beam_mock: RectangularBeam,
    ) -> None:
        """immediate_deflection calls get_deflection with return_absmax=True."""
        _ = beam_checker.immediate_deflection
        mock = cast(Mock, beam_mock)
        mock.get_deflection.assert_called_once_with(return_absmax=True)


class TestDesignLoad:
    """Tests for BeamDeformationChecker.design_load."""

    def test_almost_permanent_over_100(
        self, beam_checker: BeamDeformationChecker
    ) -> None:
        """design_load = (perm + 0.3*var) / 100 = (10 + 1.5) / 100 = 0.115 kN/cm."""
        assert_approx(
            beam_checker.design_load,
            0.115,
            "design_load should be (perm + 0.3*var) / 100 (kN/cm)",
        )

    @pytest.mark.parametrize(
        "perm, var, expected",
        [
            (0.0, 0.0, 0.0),
            (10.0, 0.0, 0.1),
            (0.0, 10.0, 0.03),
            (20.0, 10.0, 0.23),
        ],
    )
    def test_parametrized_combinations(
        self,
        beam_mock: RectangularBeam,
        perm: float,
        var: float,
        expected: float,
    ) -> None:
        """design_load matches (perm + 0.3*var)/100 for various load combinations."""
        checker = BeamDeformationChecker(
            permanent_load=perm,
            variable_load=var,
            concrete=Concrete.C30,
            span=500.0,
            width=20.0,
            effective_depth_discount=4.0,
            compressed_reinforcement_area=0.0,
            effective_depth_compressed=0.0,
            tensioned_reinforcement_area=5.0,
            structural_beam=beam_mock,
        )
        assert_approx(
            checker.design_load,
            expected,
            f"design_load for perm={perm}, var={var} should be {expected} kN/cm",
        )


class TestBeamVerifyIntegration:
    """Integration tests for BeamDeformationChecker.verify using mocked beam."""

    def test_verify_pass_with_small_deflection(
        self,
        beam_mock: RectangularBeam,
    ) -> None:
        """verify returns True when the mocked deflection is well within the limit."""
        mock = cast(Mock, beam_mock)
        mock.get_deflection.return_value = 0.001  # far below span/250 = 2.0 cm
        mock.get_bending_moment.return_value = 1.0  # small moment → not cracked
        checker = BeamDeformationChecker(
            permanent_load=10.0,
            variable_load=5.0,
            concrete=Concrete.C30,
            span=500.0,
            width=20.0,
            effective_depth_discount=4.0,
            compressed_reinforcement_area=0.0,
            effective_depth_compressed=0.0,
            tensioned_reinforcement_area=5.0,
            structural_beam=beam_mock,
        )
        assert checker.verify(60.0), (
            "verify should return True when deflection << acceptable_deflection"
        )

    def test_verify_fail_with_large_deflection(
        self,
        beam_mock: RectangularBeam,
    ) -> None:
        """verify returns False when the mocked deflection exceeds the limit."""
        mock = cast(Mock, beam_mock)
        mock.get_deflection.return_value = 100.0  # far above span/250 = 2.0 cm
        mock.get_bending_moment.return_value = 1.0
        checker = BeamDeformationChecker(
            permanent_load=10.0,
            variable_load=5.0,
            concrete=Concrete.C30,
            span=500.0,
            width=20.0,
            effective_depth_discount=4.0,
            compressed_reinforcement_area=0.0,
            effective_depth_compressed=0.0,
            tensioned_reinforcement_area=5.0,
            structural_beam=beam_mock,
        )
        assert not checker.verify(60.0), (
            "verify should return False when deflection >> acceptable_deflection"
        )
