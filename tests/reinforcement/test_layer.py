"""Unit tests for the Layer reinforcement-row dataclass."""

import pytest

from src.properties.steel import Steel
from src.reinforcement.clamps import Clamps
from src.reinforcement.layer import Layer
from src.structural_elements.rebar import Rebar
from tests.helpers import assert_approx


@pytest.fixture
def layer_two_10mm() -> Layer:
    """Build a layer holding two CA50 10 mm bars at layer index 0."""
    return Layer([Rebar(diameter_mm=10, steel=Steel.CA50) for _ in range(2)], 0)


@pytest.fixture
def empty_layer() -> Layer:
    """Build a layer holding no bars at layer index 0."""
    return Layer([], 0)


class TestArea:
    """Tests for the summed cross-sectional area of the layer's bars."""

    def test_sums_bar_areas(self, layer_two_10mm: Layer) -> None:
        expected_area = 1.5707963267948966  # cm² (2 * pi * 0.5²)
        assert_approx(
            layer_two_10mm.area,
            expected_area,
            "A layer of two 10 mm bars should sum to 2 * pi/4 cm²",
        )

    def test_empty_is_zero(self, empty_layer: Layer) -> None:
        assert empty_layer.area == 0, "An empty layer should have zero area"


class TestHasGoodAdherence:
    """Tests for the ABNT NBR 6118 good-adherence zone check."""

    def test_short_beam_within_threshold(self, layer_two_10mm: Layer) -> None:
        layer_two_10mm.y_centroid_position = 25.0
        assert layer_two_10mm.has_good_adherence(50.0) is True, (
            "For a beam under 60 cm the threshold is 30 cm; 25 cm sits below it"
        )

    def test_short_beam_above_threshold(self, layer_two_10mm: Layer) -> None:
        layer_two_10mm.y_centroid_position = 35.0
        assert layer_two_10mm.has_good_adherence(50.0) is False, (
            "For a beam under 60 cm the threshold is 30 cm; 35 cm sits above it"
        )

    def test_tall_beam_within_threshold(self, layer_two_10mm: Layer) -> None:
        layer_two_10mm.y_centroid_position = 40.0
        assert layer_two_10mm.has_good_adherence(80.0) is True, (
            "For an 80 cm beam the threshold is height - 30 = 50 cm; 40 cm is below"
        )


class TestSetAnchorageLength:
    """Tests for propagating the anchorage length onto each bar."""

    def test_left_sets_left_length(self, layer_two_10mm: Layer) -> None:
        layer_two_10mm.set_anchorage_length(30.0, left=True)
        assert layer_two_10mm.bars[0].left_length == 30.0, (
            "left=True should set the left anchorage length on every bar"
        )

    def test_right_sets_right_length(self, layer_two_10mm: Layer) -> None:
        layer_two_10mm.set_anchorage_length(30.0, left=False)
        assert layer_two_10mm.bars[0].right_length == 30.0, (
            "left=False should set the right anchorage length on every bar"
        )

    def test_empty_raises(self, empty_layer: Layer) -> None:
        with pytest.raises(
            ValueError, match="No bars in the layer to set anchorage length"
        ):
            empty_layer.set_anchorage_length(30.0, left=True)


class TestSetHooks:
    """Tests for enabling/disabling anchorage hooks on each bar."""

    def test_enable_sets_left_hook(self, layer_two_10mm: Layer) -> None:
        layer_two_10mm.set_hooks(left=True, enable=True)
        assert layer_two_10mm.bars[0].left_hook_enabled is True, (
            "Enabling the left hook should flag it on every bar"
        )

    def test_empty_raises(self, empty_layer: Layer) -> None:
        with pytest.raises(
            ValueError, match="No bars in the layer to enable/disable hooks"
        ):
            empty_layer.set_hooks(left=True, enable=True)


class TestClamps:
    """Tests for setting and reading the clamps on each side."""

    def test_no_clamps_by_default(self, layer_two_10mm: Layer) -> None:
        assert layer_two_10mm.get_clamps(left=True) is None, "No left clamps"
        assert layer_two_10mm.get_clamps(left=False) is None, "No right clamps"

    def test_reads_the_set_side(self, layer_two_10mm: Layer) -> None:
        clamps = Clamps(diameter=8, quantity=1, width=15.0, length=40.0)
        layer_two_10mm.set_clamps(left=False, clamps=clamps)
        assert layer_two_10mm.get_clamps(left=False) is clamps, "Right clamps set"
        assert layer_two_10mm.get_clamps(left=True) is None, "Left side untouched"

    def test_area_counts_both_legs(self) -> None:
        """Two 10 mm clamps have four legs: 4 · π · 0.5² / 4 = π cm²"""
        clamps = Clamps(diameter=10, quantity=2, width=15.0, length=40.0)
        assert_approx(clamps.area, 3.14159265, "Area of two 10 mm clamps (cm²)")


class TestGetBarDiametersForPrint:
    """Tests for the human-readable bar-diameter listing."""

    def test_joins_diameters(self, layer_two_10mm: Layer) -> None:
        assert layer_two_10mm.get_bar_diameters_for_print() == "10mm, 10mm", (
            "Two 10 mm bars should render as a comma-separated diameter list"
        )

    def test_empty_is_blank(self, empty_layer: Layer) -> None:
        assert empty_layer.get_bar_diameters_for_print() == "", (
            "An empty layer should render as an empty string"
        )
