"""Unit tests for BeamDeformationChecker.

All indeterminatebeam-backed calls are intercepted with a ``Mock(spec=RectangularBeam)``
so these tests remain fast and do not depend on structural-solver internals. Both
``get_bending_moment`` and ``get_deflection`` are queried at a specific position
(the interest point), not with ``return_absmax``.
"""

from typing import cast
from unittest.mock import Mock

import pytest

from src.checkers.beam_deformation_checker import BeamDeformationChecker
from src.properties.concrete import Concrete
from src.properties.section_properties_calculator import (
    SectionPropertiesCalculator as section,
)
from src.structural_elements.rectangular_beam import RectangularBeam
from tests.helpers import assert_approx

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_POSITION_CM = 250.0


@pytest.fixture
def beam_mock() -> RectangularBeam:
    """Return a Mock(spec=RectangularBeam) with canned bending-moment and deflection.

    Canned values:
        get_bending_moment(position) → 42.0 kN.m
        get_deflection(position)     → 0.85 cm
    """
    mock = Mock(spec=RectangularBeam)
    mock.get_bending_moment.return_value = 42.0
    mock.get_deflection.return_value = 0.85
    return cast(RectangularBeam, mock)


def _make_checker(
    beam_mock: RectangularBeam,
    *,
    permanent_load: float = 10.0,
    variable_load: float = 5.0,
    tensioned_reinforcement_area: float = 5.0,
    position: float = _POSITION_CM,
) -> BeamDeformationChecker:
    """Build a BeamDeformationChecker backed by a mocked RectangularBeam."""
    return BeamDeformationChecker(
        permanent_load=permanent_load,
        variable_load=variable_load,
        concrete=Concrete.C30,
        span=500.0,
        width=20.0,
        effective_depth_discount=4.0,
        compressed_reinforcement_area=0.0,
        effective_depth_compressed=0.0,
        tensioned_reinforcement_area=tensioned_reinforcement_area,
        structural_beam=beam_mock,
        position=position,
    )


@pytest.fixture
def beam_checker(beam_mock: RectangularBeam) -> BeamDeformationChecker:
    """Return a BeamDeformationChecker backed by a mocked RectangularBeam."""
    return _make_checker(beam_mock)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestServiceMoment:
    """Tests for BeamDeformationChecker.service_moment."""

    def test_returns_absolute_local_moment_in_kncm(
        self, beam_checker: BeamDeformationChecker
    ) -> None:
        """service_moment is the absolute local moment converted kN.m → kN.cm."""
        assert_approx(
            beam_checker.service_moment,
            4200.0,
            "service_moment should be abs(get_bending_moment(position)) * 100 (kN.cm)",
        )

    def test_queries_moment_at_position(
        self,
        beam_checker: BeamDeformationChecker,
        beam_mock: RectangularBeam,
    ) -> None:
        """service_moment calls get_bending_moment at the interest-point position."""
        _ = beam_checker.service_moment
        mock = cast(Mock, beam_mock)
        mock.get_bending_moment.assert_called_once_with(_POSITION_CM)

    def test_negative_moment_uses_absolute_value(
        self, beam_mock: RectangularBeam
    ) -> None:
        """A hogging (negative) local moment yields a positive service moment (kN.cm)."""
        cast(Mock, beam_mock).get_bending_moment.return_value = -30.0
        checker = _make_checker(beam_mock)
        assert_approx(
            checker.service_moment,
            3000.0,
            "service_moment should use the absolute local moment (kN.cm)",
        )


class TestImmediateDeflection:
    """Tests for BeamDeformationChecker.immediate_deflection (Branson-scaled)."""

    def test_uncracked_returns_gross_deflection(
        self, beam_mock: RectangularBeam
    ) -> None:
        """When the service moment is below cracking, deflection equals the elastic value."""
        # Tiny moment → not cracked → I_eq == I_gross → no scaling
        cast(Mock, beam_mock).get_bending_moment.return_value = 0.5
        cast(Mock, beam_mock).get_deflection.return_value = 0.85
        checker = _make_checker(beam_mock)
        checker.height = 60.0
        checker.effective_depth = 56.0
        assert not checker.is_cracked, "a 0.5 kN.m moment should not crack the section"
        assert_approx(
            checker.immediate_deflection,
            0.85,
            "uncracked immediate_deflection should equal the gross-section deflection (cm)",
        )

    def test_queries_deflection_at_position(
        self,
        beam_checker: BeamDeformationChecker,
        beam_mock: RectangularBeam,
    ) -> None:
        """immediate_deflection queries get_deflection at the interest-point position."""
        beam_checker.height = 60.0
        beam_checker.effective_depth = 56.0
        _ = beam_checker.immediate_deflection
        cast(Mock, beam_mock).get_deflection.assert_called_once_with(_POSITION_CM)

    def test_cracked_scales_deflection_by_branson_ratio(
        self, beam_mock: RectangularBeam
    ) -> None:
        """When cracked, deflection is scaled by I_gross / I_eq (> 1), amplifying it."""
        # Large moment → cracked → I_eq < I_gross → deflection amplified
        cast(Mock, beam_mock).get_bending_moment.return_value = 200.0
        cast(Mock, beam_mock).get_deflection.return_value = 0.85
        checker = _make_checker(beam_mock, tensioned_reinforcement_area=10.0)
        checker.height = 60.0
        checker.effective_depth = 56.0

        gross = section.moment_of_inertia(checker.width, checker.height)
        expected = 0.85 * (gross / checker.equivalent_moment_of_inertia)

        assert checker.is_cracked, "a 200 kN.m moment should crack the 20x60 section"
        assert checker.immediate_deflection > 0.85, (
            "cracked immediate_deflection should exceed the gross-section deflection"
        )
        assert_approx(
            checker.immediate_deflection,
            expected,
            "cracked immediate_deflection should be elastic * (I_gross / I_eq) (cm)",
        )


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
        checker = _make_checker(beam_mock, permanent_load=perm, variable_load=var)
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
        """verify returns True when the deflection at the point is well within the limit."""
        mock = cast(Mock, beam_mock)
        mock.get_deflection.return_value = 0.001  # far below span/250 = 2.0 cm
        mock.get_bending_moment.return_value = 1.0  # small moment → not cracked
        checker = _make_checker(beam_mock)
        assert checker.verify(60.0), (
            "verify should return True when deflection << acceptable_deflection"
        )

    def test_verify_fail_with_large_deflection(
        self,
        beam_mock: RectangularBeam,
    ) -> None:
        """verify returns False when the deflection at the point exceeds the limit."""
        mock = cast(Mock, beam_mock)
        mock.get_deflection.return_value = 100.0  # far above span/250 = 2.0 cm
        mock.get_bending_moment.return_value = 1.0
        checker = _make_checker(beam_mock)
        assert not checker.verify(60.0), (
            "verify should return False when deflection >> acceptable_deflection"
        )
