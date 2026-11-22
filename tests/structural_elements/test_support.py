"""Unit tests for the Support structural element."""

import pytest

from src.errors import EnginePreconditionError
from src.structural_elements.support import Support


class TestValidation:
    """Tests for the left <= center <= right face ordering."""

    def test_valid_support_stores_positions(self) -> None:
        support = Support(center=100.0, left=90.0, right=110.0)
        assert support.center == 100.0, "Center should be stored as given"
        assert support.left == 90.0, "Left face should be stored as given"
        assert support.right == 110.0, "Right face should be stored as given"

    def test_zero_width_support_constructs(self) -> None:
        support = Support(center=0.0, left=0.0, right=0.0)
        assert support.left == support.right, "A point support has coincident faces"

    def test_left_face_after_center_raises(self) -> None:
        with pytest.raises(EnginePreconditionError, match="left <= center <= right"):
            Support(center=100.0, left=101.0, right=110.0)

    def test_center_after_right_face_raises(self) -> None:
        with pytest.raises(EnginePreconditionError, match="left <= center <= right"):
            Support(center=100.0, left=90.0, right=99.0)


class TestIsExtremity:
    """Tests for detecting supports on either end of the beam."""

    def test_start_support(self) -> None:
        support = Support(center=0.0, left=-10.0, right=10.0)
        assert support.is_extremity(500.0), "A support at 0 cm is an extremity"

    def test_end_support(self) -> None:
        support = Support(center=500.0, left=490.0, right=510.0)
        assert support.is_extremity(500.0), (
            "A support at the beam length is an extremity"
        )

    def test_interior_support(self) -> None:
        support = Support(center=300.0, left=290.0, right=310.0)
        assert not support.is_extremity(500.0), (
            "An interior support is not an extremity"
        )

    def test_within_tolerance(self) -> None:
        support = Support(center=499.9995, left=490.0, right=510.0)
        assert support.is_extremity(500.0), "A center within 1e-3 cm of the end counts"

    def test_outside_tolerance(self) -> None:
        support = Support(center=0.01, left=-10.0, right=10.0)
        assert not support.is_extremity(500.0), (
            "A center 0.01 cm from the start does not count"
        )
