"""Unit tests for the Support structural element."""

import pytest

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
        with pytest.raises(ValueError, match="left <= center <= right"):
            Support(center=100.0, left=101.0, right=110.0)

    def test_center_after_right_face_raises(self) -> None:
        with pytest.raises(ValueError, match="left <= center <= right"):
            Support(center=100.0, left=90.0, right=99.0)
