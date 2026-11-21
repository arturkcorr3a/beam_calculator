"""Unit tests for src/calculators/utils.py — cotangent helper."""

from math import pi

import pytest

from src.calculators.utils import cotan
from src.errors import EnginePreconditionError
from tests.helpers import assert_approx


class TestCotan:
    """Tests for the cotan() function."""

    @pytest.mark.parametrize(
        ("alpha", "expected"),
        [
            (pi / 4, 1.0),
            (pi / 3, 0.5773502691896257),
            (3 * pi / 4, -1.0),
        ],
    )
    def test_reciprocal_values(self, alpha: float, expected: float) -> None:
        """cotan(alpha) returns 1/tan(alpha) for standard angles (dimensionless)."""
        assert_approx(cotan(alpha), expected, "cotan reciprocal value (dimensionless)")

    def test_zero_at_half_pi(self) -> None:
        """cotan(pi/2) is exactly 0.0 (dimensionless)."""
        assert cotan(pi / 2) == 0.0, "cotan(pi/2) should be 0.0 (dimensionless)"

    def test_zero_at_three_half_pi(self) -> None:
        """cotan(3*pi/2) is exactly 0.0 (dimensionless)."""
        assert cotan(3 * pi / 2) == 0.0, "cotan(3*pi/2) should be 0.0 (dimensionless)"

    def test_raises_at_zero(self) -> None:
        """cotan(0) raises ValueError (cotangent undefined)."""
        with pytest.raises(EnginePreconditionError, match="undefined"):
            cotan(0)

    def test_raises_at_pi(self) -> None:
        """cotan(pi) raises ValueError (cotangent undefined)."""
        with pytest.raises(EnginePreconditionError, match="undefined"):
            cotan(pi)

    def test_raises_at_two_pi(self) -> None:
        """cotan(2*pi) raises ValueError (cotangent undefined)."""
        with pytest.raises(EnginePreconditionError, match="undefined"):
            cotan(2 * pi)

    def test_tolerance_edge_still_raises(self) -> None:
        """cotan(pi + 5e-6) still raises because abs_tol=1e-5 (5e-6 < 1e-5)."""
        with pytest.raises(EnginePreconditionError, match="undefined"):
            cotan(pi + 5e-6)

    def test_just_outside_tolerance_does_not_raise(self) -> None:
        """cotan(pi + 2e-5) does NOT raise because 2e-5 > abs_tol=1e-5 (dimensionless)."""
        result = cotan(pi + 2e-5)
        # cotan near pi is a large negative number; just verify it returns a float
        assert isinstance(result, float), (
            "cotan slightly past tolerance should return a float (dimensionless)"
        )
