"""Tests for src/calculators/layout_selection.py."""

import pytest

from src.calculators.layout_selection import LayoutPass, select_layout
from tests.helpers import assert_approx

# Bar areas (cm²): 3φ16 = 6.03, 2φ20 = 6.28, 4φ16 = 8.04
_THREE_16 = LayoutPass(
    signature=(((16.0, 16.0), (16.0,)), ()),
    tensioned_required=5.98,
    compressed_required=0.0,
    tensioned_provided=6.03,
    compressed_provided=0.0,
)
_TWO_20 = LayoutPass(
    signature=(((20.0, 20.0),), ()),
    tensioned_required=6.12,
    compressed_required=0.0,
    tensioned_provided=6.28,
    compressed_provided=0.0,
)
_FOUR_16 = LayoutPass(
    signature=(((16.0, 16.0), (16.0, 16.0)), ()),
    tensioned_required=6.20,
    compressed_required=0.0,
    tensioned_provided=8.04,
    compressed_provided=0.0,
)


class TestSelectLayout:
    """select_layout keeps the cheapest layout covering the area required at its own d."""

    def test_flip_keeps_the_safe_layout(self) -> None:
        """3x16 needs 6.12 at its own d (unsafe), 2x20 needs 5.98 (safe)"""
        kept, is_safe = select_layout([_THREE_16, _TWO_20], (5.98, 0.0))
        assert kept is _TWO_20, "2x20mm should be kept"
        assert is_safe, "2x20mm covers the area required at its own d"

    def test_cheapest_safe_layout_wins(self) -> None:
        """Both 2x20 and 4x16 are safe; the smaller area wins"""
        kept, is_safe = select_layout([_TWO_20, _FOUR_16], (6.0, 0.0))
        assert kept is _TWO_20, "the smaller safe area should be kept"
        assert is_safe, "the kept layout should be safe"

    def test_no_safe_layout_keeps_the_largest(self) -> None:
        """Without a safe layout, keep the largest area and flag it"""
        kept, is_safe = select_layout([_THREE_16, _TWO_20], (7.0, 0.0))
        assert kept is _TWO_20, "the largest area should be kept"
        assert not is_safe, "no layout covers its own required area"

    def test_compressed_shortfall_disqualifies(self) -> None:
        """A layout whose compressed bars fall short of its own-d requirement is unsafe"""
        doubly = LayoutPass(
            signature=(((20.0, 20.0),), ((10.0, 10.0),)),
            tensioned_required=6.0,
            compressed_required=1.0,
            tensioned_provided=6.28,
            compressed_provided=1.57,
        )
        kept, is_safe = select_layout([doubly], (6.0, 2.0))
        assert kept is doubly, "the only layout should be kept"
        assert not is_safe, "1.57 cm² compressed is below the 2.0 cm² required"

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError):
            select_layout([], (1.0, 0.0))


class TestLayoutPass:
    """LayoutPass totals and describes its bars."""

    def test_total_provided(self) -> None:
        assert_approx(_TWO_20.total_provided, 6.28, "total chosen area (cm²)")

    def test_describe_groups_layers(self) -> None:
        assert _THREE_16.describe() == "3x16mm", "bars across layers are counted"

    def test_describe_includes_compressed(self) -> None:
        doubly = LayoutPass(
            signature=(((20.0, 16.0),), ((10.0, 10.0),)),
            tensioned_required=0.0,
            compressed_required=0.0,
            tensioned_provided=0.0,
            compressed_provided=0.0,
        )
        assert doubly.describe() == "1x20mm, 1x16mm + 2x10mm (compressed)", (
            "compressed bars are listed after the tensioned ones"
        )
