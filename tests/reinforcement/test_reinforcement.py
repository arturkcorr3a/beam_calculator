"""Unit tests for the Reinforcement longitudinal-bar orchestration."""

import types
from typing import cast

import pytest

from src.config import APP_CONFIG
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.reinforcement.layer import Layer
from src.reinforcement.reinforcement import (
    DEFAULT_STIRRUP_DIAMETER_FOR_D_CALCULATION,
    Reinforcement,
)
from src.structural_elements.rebar import Rebar
from src.structural_elements.rectangular_beam import RectangularBeam
from tests.helpers import assert_approx


@pytest.fixture(autouse=True)
def pinned_concrete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the project concrete to C30 for every test in this module"""
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C30)


@pytest.fixture
def beam_double() -> RectangularBeam:
    """Build a light beam double (CA50, 20x60 cm, 500 cm long).

    The reinforcement orchestration only reads material grades and geometry off
    the beam, so a ``SimpleNamespace`` cast to ``RectangularBeam`` avoids running
    the structural analysis while still driving the real
    ``RebarChooser`` and ``AnchorageCalculator``.
    """
    beam = types.SimpleNamespace(
        steel=Steel.CA50,
        width=20.0,
        height=60.0,
        length=500.0,
    )
    return cast(RectangularBeam, beam)


@pytest.fixture
def reinforcement(beam_double: RectangularBeam) -> Reinforcement:
    """Build a bottom Reinforcement centered at midspan over the beam double.

    The moment shift a_l (cm) is set because ``choose`` runs the full
    anchorage calculation, which requires it.
    """
    reinforcement = Reinforcement(
        beam_double,
        is_bottom_reinforcement=True,
        center_position=250.0,
        id="R",
    )
    reinforcement.moment_shift = 28.0
    return reinforcement


class TestPureHelpers:
    """Tests for the spacing/distance helpers that need no chosen bars."""

    def test_get_horizontal_spacing_governed_by_aggregate(
        self, reinforcement: Reinforcement
    ) -> None:
        expected = 3.0  # cm: max(1.0, 2, 1.2 * 2.5)
        assert_approx(
            reinforcement.get_horizontal_spacing(1.0),
            expected,
            "1.2 * default 2.5 cm aggregate governs the horizontal spacing",
        )

    def test_get_horizontal_spacing_governed_by_diameter(
        self, reinforcement: Reinforcement
    ) -> None:
        expected = 5.0  # cm: max(5.0, 2, 1.2 * 2.5)
        assert_approx(
            reinforcement.get_horizontal_spacing(5.0),
            expected,
            "A large bar diameter governs the horizontal spacing",
        )

    def test_get_vertical_spacing(self) -> None:
        expected = 2.0  # cm: max(1.0, 2, 0.5 * 2.5)
        assert_approx(
            Reinforcement.get_vertical_spacing(1.0),
            expected,
            "The 2 cm floor governs the vertical spacing for a thin bar",
        )

    def test_d_calculation_not_chosen(self, reinforcement: Reinforcement) -> None:
        assert_approx(
            reinforcement.get_distance_for_d_calculation("R"),
            1.0,
            "With no reinforcement chosen the default distance is returned",
        )

    def test_area_empty_before_choose(self, reinforcement: Reinforcement) -> None:
        assert reinforcement.area == 0, (
            "Before choosing bars the reinforcement area should be zero"
        )


class TestChoose:
    """Tests for the required-area guard and the full selection path."""

    def test_requires_area_first(self, reinforcement: Reinforcement) -> None:
        # ``choose`` formats ``required_area`` (None) before the ValueError
        # guard runs, so the observable failure is a TypeError from the
        # ``.2f`` format. The ValueError guard is unreachable via any supported
        # path (``set_required_area`` never stores None), so the observable
        # behavior is asserted instead.
        with pytest.raises(TypeError):
            reinforcement.choose()

    def test_full_selection(self, reinforcement: Reinforcement) -> None:
        reinforcement.set_required_area(4.02)
        assert reinforcement.is_chosen is True, (
            "Choosing bars for a reachable area should flag the reinforcement"
        )
        assert_approx(
            reinforcement.area,
            4.0212385965949355,
            "Two 16 mm bars should provide ~4.02 cm²",
        )
        assert [bar.diameter_mm for bar in reinforcement.chosen_bars[0].bars] == [
            16,
            16,
        ], "The minimum-area solution for 4.02 cm² is two 16 mm bars in layer 0"
        assert_approx(
            reinforcement.get_distance_for_d_calculation("R"),
            0.8,
            "The single-layer centroid sits 0.8 cm from the stirrup's inner face",
        )

    def test_near_minimum_area_prefers_fewer_bars(
        self, reinforcement: Reinforcement
    ) -> None:
        """For 2.0 cm², 1x12.5mm + 1x10mm (2.01 cm²) beats 4x8mm and 2x16mm"""
        reinforcement.set_required_area(2.0)
        assert sorted(bar.diameter_mm for bar in reinforcement.chosen_bars[0].bars) == [
            10,
            12.5,
        ], "Within the area tolerance, two bars should beat four 8 mm bars"
        assert_approx(
            reinforcement.area,
            2.0125827937059615,
            "1x12.5mm + 1x10mm should total ~2.01 cm²",
        )

    def test_near_minimum_area_prefers_fewer_layers(
        self, reinforcement: Reinforcement
    ) -> None:
        """For 4.0 cm², one layer of 2x16mm beats the two-layer 4.013 cm² mix"""
        reinforcement.set_required_area(4.0)
        assert [bar.diameter_mm for bar in reinforcement.chosen_bars[0].bars] == [
            16,
            16,
        ], "Two 16 mm bars in one layer should be chosen"
        assert reinforcement.chosen_bars[1].bars == [], "No second layer should be used"

    def test_rechoosing_discards_previous_bars(
        self, reinforcement: Reinforcement
    ) -> None:
        """A second choice does not keep the multi-layer bars of the first (cm²)."""
        reinforcement.set_required_area(18.0)
        first_area = reinforcement.area
        assert len(reinforcement.chosen_bars[1].bars) > 0, (
            "18 cm² in a 20 cm wide beam should need a second layer"
        )

        reinforcement.set_required_area(18.0)

        assert_approx(
            reinforcement.area,
            first_area,
            "Re-choosing the same area should give the same bars, not pile them up",
        )


class TestLayerCentroidPosition:
    """y_centroid_position is the layer height from the bottom face (cm)."""

    def test_bottom_layer_measured_from_bottom_face(
        self, reinforcement: Reinforcement
    ) -> None:
        reinforcement.set_required_area(4.02)  # 2φ16 in layer 0
        expected = (
            RectangularBeam.nominal_covering
            + DEFAULT_STIRRUP_DIAMETER_FOR_D_CALCULATION
            + 0.8
        )  # cm: cover + default stirrup + φ16/2
        assert_approx(
            reinforcement.chosen_bars[0].y_centroid_position,
            expected,
            "Bottom layer height should add the cover and stirrup to φ/2",
        )

    def test_uses_chosen_stirrup_diameter(self, reinforcement: Reinforcement) -> None:
        reinforcement.stirrup_diameter = 0.63  # cm, φ6.3
        reinforcement.set_required_area(4.02)
        expected = RectangularBeam.nominal_covering + 0.63 + 0.8  # cm
        assert_approx(
            reinforcement.chosen_bars[0].y_centroid_position,
            expected,
            "Bottom layer height should use the chosen stirrup diameter",
        )

    def test_top_layer_measured_from_bottom_face(
        self, beam_double: RectangularBeam
    ) -> None:
        top = Reinforcement(
            beam_double, is_bottom_reinforcement=False, center_position=250.0, id="T"
        )
        top.moment_shift = 28.0
        top.set_required_area(4.02)  # 2φ16 in layer 0
        expected = beam_double.height - (
            RectangularBeam.nominal_covering
            + DEFAULT_STIRRUP_DIAMETER_FOR_D_CALCULATION
            + 0.8
        )  # cm
        assert_approx(
            top.chosen_bars[0].y_centroid_position,
            expected,
            "Top layer height should be h minus cover, stirrup and φ/2",
        )


class TestValidateLayerIndex:
    """Tests for the layer-index bounds check."""

    def test_out_of_range_raises(self, reinforcement: Reinforcement) -> None:
        reinforcement.set_required_area(4.02)
        with pytest.raises(ValueError, match="Layer index must be between 0 and"):
            reinforcement._validate_layer_index(99)  # pyright: ignore[reportPrivateUsage]


class TestDistributeBars:
    """Tests for the maximum-layers constructability guard."""

    def test_exceeds_max_layers_raises(
        self, reinforcement: Reinforcement, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(APP_CONFIG, "max_layers", 1)
        bars = [Rebar(diameter_mm=32, steel=Steel.CA50) for _ in range(20)]
        with pytest.raises(
            ValueError,
            match="Cannot distribute bars within the maximum number of layers",
        ):
            reinforcement.distribute_bars_in_layers(bars)

    def test_smaller_group_fills_remaining_space_in_layer(
        self, reinforcement: Reinforcement
    ) -> None:
        """Smaller bars fill the room left in a layer before a new layer opens"""
        # 15 cm available (20 - 2 x 2.5 cover), 3 cm spacing: 2φ16 + 3φ10
        # needs 18.2 cm, but 2φ16 + 2φ10 fit (14.2 cm)
        bars = [Rebar(diameter_mm=16, steel=Steel.CA50) for _ in range(2)] + [
            Rebar(diameter_mm=10, steel=Steel.CA50) for _ in range(3)
        ]
        reinforcement.distribute_bars_in_layers(bars)
        layers = reinforcement.chosen_bars
        assert sorted(_diameters(layers[0])) == [10, 10, 16, 16], (
            "Layer 0 should hold both φ16 plus the two φ10 that still fit"
        )
        assert _diameters(layers[1]) == [10], (
            "Only the φ10 that does not fit should open layer 1"
        )

    def test_three_groups_beyond_max_layers_raise_value_error(
        self, beam_double: RectangularBeam
    ) -> None:
        """Three diameter groups past the last layer raise ValueError, not IndexError"""
        narrow_beam = cast(
            RectangularBeam,
            types.SimpleNamespace(**{**vars(beam_double), "width": 12.0}),
        )
        reinforcement = Reinforcement(
            narrow_beam, is_bottom_reinforcement=True, center_position=250.0
        )
        bars = (
            [Rebar(diameter_mm=25, steel=Steel.CA50) for _ in range(3)]
            + [Rebar(diameter_mm=12.5, steel=Steel.CA50)]
            + [Rebar(diameter_mm=10, steel=Steel.CA50)]
        )
        with pytest.raises(
            ValueError,
            match="Cannot distribute bars within the maximum number of layers",
        ):
            reinforcement.distribute_bars_in_layers(bars)


def _layer(*diameters_mm: float) -> Layer:
    """Build a layer 0 holding CA50 bars of the given diameters (mm), in order."""
    return Layer([Rebar(diameter_mm=d, steel=Steel.CA50) for d in diameters_mm], 0)


def _diameters(layer: Layer) -> list[float]:
    """Return the layer's bar diameters (mm), left to right."""
    return [bar.diameter_mm for bar in layer.bars]


class TestArrangeBarsInLayer:
    """Tests for the symmetric, largest-outside bar arrangement within a layer."""

    def test_empty_layer_stays_empty(self, reinforcement: Reinforcement) -> None:
        layer = _layer()
        reinforcement.arrange_bars_in_layer(layer)
        assert layer.bars == [], "An empty layer should remain empty"

    def test_single_diameter_unchanged(self, reinforcement: Reinforcement) -> None:
        layer = _layer(16, 16, 16)
        reinforcement.arrange_bars_in_layer(layer)
        assert _diameters(layer) == [16, 16, 16], (
            "A single-diameter layer should keep all its bars"
        )

    def test_even_counts_put_largest_outside(
        self, reinforcement: Reinforcement
    ) -> None:
        layer = _layer(10, 10, 16, 10, 10, 16)
        reinforcement.arrange_bars_in_layer(layer)
        assert _diameters(layer) == [16, 10, 10, 10, 10, 16], (
            "Largest bars should sit at both ends of a symmetric row"
        )

    def test_odd_count_bar_goes_to_center(self, reinforcement: Reinforcement) -> None:
        layer = _layer(12.5, 20, 12.5, 20, 20)
        reinforcement.arrange_bars_in_layer(layer)
        assert _diameters(layer) == [20, 12.5, 20, 12.5, 20], (
            "The unpaired bar should sit in the center of the row"
        )

    def test_multiple_odd_counts_fill_middle(
        self, reinforcement: Reinforcement
    ) -> None:
        layer = _layer(12.5, 16, 12.5, 20)
        reinforcement.arrange_bars_in_layer(layer)
        assert _diameters(layer) == [12.5, 20, 16, 12.5], (
            "Paired bars should stay outside, unpaired bars fill the middle"
        )

    def test_area_preserved(self, reinforcement: Reinforcement) -> None:
        layer = _layer(10, 20, 16, 20, 10, 10)
        area_before = layer.area
        reinforcement.arrange_bars_in_layer(layer)
        assert_approx(layer.area, area_before, "Arranging should not change the area")


class TestClearChosenBars:
    """Tests for resetting the chosen-bar layers."""

    def test_resets_layers(self, reinforcement: Reinforcement) -> None:
        reinforcement.set_required_area(4.02)
        reinforcement.clear_chosen_bars()
        assert reinforcement.chosen_bars[0].bars == [], (
            "Clearing should empty every layer's bar list"
        )
        assert reinforcement.is_chosen is True, (
            "clear_chosen_bars only rebuilds the layers; it leaves is_chosen set"
        )


def _make_reinforcement(beam: RectangularBeam, center_position: float) -> Reinforcement:
    """Build a bottom Reinforcement over the beam double at a given center (cm)."""
    reinforcement = Reinforcement(
        beam,
        is_bottom_reinforcement=True,
        center_position=center_position,
        id="R",
    )
    reinforcement.moment_shift = 28.0  # cm
    return reinforcement


def _bars(reinforcement: Reinforcement) -> list[Rebar]:
    """Return every chosen bar across all layers."""
    return [bar for layer in reinforcement.chosen_bars for bar in layer.bars]


class TestEndSupportAnchorage:
    """Bars at an end support are hooked into it and anchored towards the interior."""

    def test_beam_start_anchors_right_only(self, beam_double: RectangularBeam) -> None:
        """At x = 0 the left side is hooked with zero length; the right one is calculated (cm)."""
        reinforcement = _make_reinforcement(beam_double, center_position=0.0)
        reinforcement.set_required_area(4.02)
        for bar in _bars(reinforcement):
            assert bar.left_length == 0, "No left anchorage at the beam start"
            assert bar.right_length > 0, "Right anchorage should be calculated"
            assert bar.left_hook_enabled is True, (
                "Left hook should anchor the bar into the start support"
            )
            assert bar.right_hook_enabled is False, (
                "Interior side needs no hook with 250+ cm available"
            )

    def test_beam_end_anchors_left_only(self, beam_double: RectangularBeam) -> None:
        """At x = L the right side is hooked with zero length; the left one is calculated (cm)."""
        reinforcement = _make_reinforcement(beam_double, center_position=500.0)
        reinforcement.set_required_area(4.02)
        for bar in _bars(reinforcement):
            assert bar.right_length == 0, "No right anchorage at the beam end"
            assert bar.left_length > 0, "Left anchorage should be calculated"
            assert bar.right_hook_enabled is True, (
                "Right hook should anchor the bar into the end support"
            )
            assert bar.left_hook_enabled is False, (
                "Interior side needs no hook with 250+ cm available"
            )

    def test_end_support_right_length_matches_midspan(
        self, beam_double: RectangularBeam
    ) -> None:
        """The anchorage length does not depend on position; only the skipped side does (cm)."""
        at_start = _make_reinforcement(beam_double, center_position=0.0)
        at_start.set_required_area(4.02)
        at_midspan = _make_reinforcement(beam_double, center_position=250.0)
        at_midspan.set_required_area(4.02)
        assert_approx(
            _bars(at_start)[0].right_length,
            _bars(at_midspan)[0].right_length,
            "Right anchorage at x = 0 should equal the mid-span one (cm)",
        )

    def test_midspan_anchors_both_sides(self, beam_double: RectangularBeam) -> None:
        """Away from the ends both anchorage lengths are calculated (cm)."""
        reinforcement = _make_reinforcement(beam_double, center_position=250.0)
        reinforcement.set_required_area(4.02)
        for bar in _bars(reinforcement):
            assert bar.left_length > 0, "Left anchorage should be calculated"
            assert bar.right_length > 0, "Right anchorage should be calculated"
            assert bar.left_hook_enabled is False, "No left hook away from the ends"
            assert bar.right_hook_enabled is False, "No right hook away from the ends"
