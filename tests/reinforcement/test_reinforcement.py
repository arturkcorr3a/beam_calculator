"""Unit tests for the Reinforcement longitudinal-bar orchestration."""

import types
from typing import cast
from unittest.mock import PropertyMock, patch

import pytest

from src.config import APP_CONFIG
from src.errors import (
    EnginePreconditionError,
    MaxLayersExceededError,
    NoReinforcementLayoutError,
)
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.reinforcement.clamps import Clamps
from src.reinforcement.layer import Layer
from src.reinforcement.reinforcement import (
    DEFAULT_STIRRUP_DIAMETER_FOR_D_CALCULATION,
    Reinforcement,
)
from src.structural_elements.rebar import Rebar
from src.structural_elements.rectangular_beam import RectangularBeam
from src.structural_elements.support import Support
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
        supports=[Support(0.0, -10.0, 10.0), Support(500.0, 490.0, 510.0)],
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


def _place_layers(reinforcement: Reinforcement, *layers: tuple[float, ...]) -> None:
    """Put bars of the given diameters (mm) straight into the first layers"""
    for layer, diameters in zip(reinforcement.chosen_bars, layers, strict=False):
        layer.bars = [Rebar(diameter_mm=d, steel=Steel.CA50) for d in diameters]


class TestClampsFit:
    """Clamp rows stack after the layers, up to the section's mid-height.

    With the default 2.5 cm cover and 1.0 cm stirrup, the room from the stirrup's
    inner face to mid-height of the 60 cm beam is 30 - 3.5 = 26.5 cm.
    """

    def test_stack_height_single_clamp(self, reinforcement: Reinforcement) -> None:
        """2φ16 layer, one φ10 clamp: 1.6 + max(1.6, 2, 1.25) + 1.0 = 4.6 cm"""
        _place_layers(reinforcement, (16, 16))
        height = reinforcement._clamps_stack_height(10, 1)  # pyright: ignore[reportPrivateUsage]
        assert_approx(height, 4.6, "Stack height for one φ10 clamp (cm)")

    def test_stack_height_spacing_uses_larger_diameter(
        self, reinforcement: Reinforcement
    ) -> None:
        """2φ25 layer, one φ6.3 clamp: the spacing to the layer is 2.5 cm, so 2.5 + 2.5 + 0.63"""
        _place_layers(reinforcement, (25, 25))
        height = reinforcement._clamps_stack_height(6.3, 1)  # pyright: ignore[reportPrivateUsage]
        assert_approx(height, 5.63, "Spacing from the larger diameter (cm)")

    def test_stack_height_adds_rows(self, reinforcement: Reinforcement) -> None:
        """Three φ10 clamps add two rows of 2 + 1.0 cm: 4.6 + 6.0 = 10.6 cm"""
        _place_layers(reinforcement, (16, 16))
        height = reinforcement._clamps_stack_height(10, 3)  # pyright: ignore[reportPrivateUsage]
        assert_approx(height, 10.6, "Stack height for three φ10 clamps (cm)")

    def test_stack_height_after_last_layer(self, reinforcement: Reinforcement) -> None:
        """2φ16 + 2φ12.5 layers, one φ10 clamp: (2 + 1.6) + 1.25 + 2 + 1.0 = 7.85 cm"""
        _place_layers(reinforcement, (16, 16), (12.5, 12.5))
        height = reinforcement._clamps_stack_height(10, 1)  # pyright: ignore[reportPrivateUsage]
        assert_approx(height, 7.85, "Clamps stack after the second layer (cm)")

    def test_fits_up_to_mid_height(self, reinforcement: Reinforcement) -> None:
        """Eight φ10 clamps reach 25.6 cm, within the 26.5 cm room"""
        _place_layers(reinforcement, (16, 16))
        assert reinforcement.clamps_fit(10, 8), "Stack within mid-height fits"

    def test_does_not_fit_past_mid_height(self, reinforcement: Reinforcement) -> None:
        """Nine φ10 clamps reach 28.6 cm, past the 26.5 cm room"""
        _place_layers(reinforcement, (16, 16))
        assert not reinforcement.clamps_fit(10, 9), "Stack past mid-height fails"

    def test_top_reinforcement_uses_top_half(
        self, beam_double: RectangularBeam
    ) -> None:
        """Top bars stack downwards from the top face, with the same room"""
        top = Reinforcement(
            beam_double, is_bottom_reinforcement=False, center_position=250.0, id="T"
        )
        _place_layers(top, (16, 16))
        assert top.clamps_fit(10, 8), "Eight φ10 clamps fit in the top half"
        assert not top.clamps_fit(10, 9), "Nine φ10 clamps pass mid-height"


class TestFaceExtent:
    """Distance from the face to the inner edge of its bars (cover 2.5 + stirrup 1.0 cm)."""

    def test_single_layer(self, reinforcement: Reinforcement) -> None:
        """2φ16: 3.5 + 1.6 = 5.1 cm"""
        _place_layers(reinforcement, (16, 16))
        assert_approx(reinforcement.face_extent(), 5.1, "extent (cm)")

    def test_two_layers(self, reinforcement: Reinforcement) -> None:
        """2φ16 + 2φ12.5: 3.5 + 1.6 + 2 + 1.25 = 8.35 cm"""
        _place_layers(reinforcement, (16, 16), (12.5, 12.5))
        assert_approx(reinforcement.face_extent(), 8.35, "extent (cm)")

    def test_no_bars_counts_construction_bar(
        self, reinforcement: Reinforcement
    ) -> None:
        """No chosen bars: a construction bar with the stirrup's φ1.0, 3.5 + 1.0 = 4.5 cm"""
        assert_approx(reinforcement.face_extent(), 4.5, "extent (cm)")


class TestValidateLayerIndex:
    """Tests for the layer-index bounds check."""

    def test_out_of_range_raises(self, reinforcement: Reinforcement) -> None:
        reinforcement.set_required_area(4.02)
        with pytest.raises(
            EnginePreconditionError, match="Layer index must be between 0 and"
        ):
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
        # 13 cm available (20 - 2 x (2.5 cover + 1.0 default stirrup)), 3 cm
        # spacing: 2φ16 + 2φ10 needs 14.2 cm, but 2φ16 + 1φ10 fit (10.2 cm)
        bars = [Rebar(diameter_mm=16, steel=Steel.CA50) for _ in range(2)] + [
            Rebar(diameter_mm=10, steel=Steel.CA50) for _ in range(3)
        ]
        reinforcement.distribute_bars_in_layers(bars)
        layers = reinforcement.chosen_bars
        assert sorted(_diameters(layers[0])) == [10, 16, 16], (
            "Layer 0 should hold both φ16 plus the one φ10 that still fits"
        )
        assert _diameters(layers[1]) == [10, 10], (
            "Only the φ10 that do not fit should open layer 1"
        )

    def test_continued_diameter_gets_own_instance_per_layer(
        self, reinforcement: Reinforcement
    ) -> None:
        """A diameter split across layers has one instance per layer, so lengths set on one layer do not leak into the other"""
        bars = [Rebar(diameter_mm=16, steel=Steel.CA50) for _ in range(2)] + [
            Rebar(diameter_mm=10, steel=Steel.CA50) for _ in range(3)
        ]
        reinforcement.distribute_bars_in_layers(bars)
        layers = reinforcement.chosen_bars
        first_layer_bar = next(b for b in layers[0].bars if b.diameter_mm == 10)
        second_layer_bars = layers[1].bars
        assert all(bar is not first_layer_bar for bar in second_layer_bars), (
            "Layer 1 should not reuse the φ10 instance of layer 0"
        )
        assert second_layer_bars[0] is second_layer_bars[1], (
            "Bars of one diameter should still share an instance within a layer"
        )

        layers[1].set_anchorage_length(80.0, left=True)
        assert first_layer_bar.left_length == 0.0, (
            "Setting layer 1's length should leave layer 0's φ10 unchanged"
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


class TestCheckForEnoughSpace:
    """The layer width excludes the cover and the stirrup on both sides (cm)."""

    # 3φ25 with 3 cm spacing needs 7.5 + 2 x 3 = 13.5 cm
    THREE_25MM_BARS = [Rebar(diameter_mm=25, steel=Steel.CA50) for _ in range(3)]

    def test_default_stirrup_reduces_available_width(
        self, reinforcement: Reinforcement
    ) -> None:
        # 20 - 2 x (2.5 cover + 1.0 default stirrup) = 13 cm available
        assert not reinforcement.check_for_enough_space(self.THREE_25MM_BARS), (
            "3φ25 should not fit once the default stirrup is discounted"
        )

    def test_uses_chosen_stirrup_diameter(self, reinforcement: Reinforcement) -> None:
        reinforcement.stirrup_diameter = 0.63  # cm, φ6.3
        # 20 - 2 x (2.5 cover + 0.63 stirrup) = 13.74 cm available
        assert reinforcement.check_for_enough_space(self.THREE_25MM_BARS), (
            "3φ25 should fit with the thinner chosen stirrup"
        )


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
            assert bar.left_length > 0, "Left bar runs over the start support"
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
            assert bar.right_length > 0, "Right bar runs over the end support"
            assert bar.left_length > 0, "Left anchorage should be calculated"
            assert bar.right_hook_enabled is True, (
                "Right hook should anchor the bar into the end support"
            )
            assert bar.left_hook_enabled is False, (
                "Interior side needs no hook with 250+ cm available"
            )

    @pytest.mark.parametrize("center_position", [0.0, 500.0])
    def test_end_support_hooks_must_fit(
        self, beam_double: RectangularBeam, center_position: float
    ) -> None:
        """No option is valid when the end support's hooks never fit in the section."""
        reinforcement = _make_reinforcement(beam_double, center_position)
        reinforcement.effective_depth = 55.0  # cm
        reinforcement.design_shear = 100.0  # kN
        with (
            patch.object(Rebar, "hook_height", new_callable=PropertyMock) as height,
            pytest.raises(
                NoReinforcementLayoutError, match="No valid reinforcement combination"
            ),
        ):
            height.return_value = 100.0  # cm, taller than the 60 cm section
            reinforcement.set_required_area(4.02)

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

    @pytest.mark.parametrize(
        ("center_position", "left"), [(0.0, True), (500.0, False)], ids=["start", "end"]
    )
    def test_top_tensioned_bars_bend_into_pillar(
        self, pillar_beam: RectangularBeam, center_position: float, left: bool
    ) -> None:
        """Over a 20 cm pillar the bars run 10 cm − max(c_nom, 3φ), then bend at 15φ (cm)."""
        reinforcement = _make_top_reinforcement(pillar_beam, center_position)
        reinforcement.set_required_area(4.02)
        for bar in _bars(reinforcement):
            diameter_cm = bar.diameter_mm / 10  # cm
            geometry = bar.left_hook_geometry if left else bar.right_hook_geometry
            length = bar.left_length if left else bar.right_length
            expected_length = 10.0 - max(
                RectangularBeam.nominal_covering, 3 * diameter_cm
            )  # cm
            assert geometry is not None, "The pillar side should be a frame joint"
            assert_approx(geometry.pin_diameter, 15 * diameter_cm, "D = 15φ (cm)")
            assert_approx(length, expected_length, "Axis to the outer face (cm)")

    @pytest.mark.parametrize("center_position", [0.0, 500.0])
    def test_top_tensioned_bars_skip_hook_height_check(
        self, pillar_beam: RectangularBeam, center_position: float
    ) -> None:
        """The frame-joint leg goes into the pillar, so tall hooks do not block it."""
        reinforcement = _make_top_reinforcement(pillar_beam, center_position)
        with patch.object(Rebar, "hook_height", new_callable=PropertyMock) as height:
            height.return_value = 100.0  # cm, taller than the 60 cm section
            reinforcement.set_required_area(4.02)
        assert reinforcement.is_chosen, "A combination should be chosen"

    def test_top_compressed_bars_keep_standard_hook(
        self, pillar_beam: RectangularBeam
    ) -> None:
        """Compressed top bars at x = 0 keep the standard hook and run to the outer face (cm)."""
        reinforcement = _make_top_reinforcement(pillar_beam, 0.0, is_tensioned=False)
        reinforcement.set_required_area(4.02)
        for bar in _bars(reinforcement):
            assert bar.left_hook_enabled is True, "The bar keeps its hook"
            assert bar.left_hook_geometry is None, "The hook is the standard one"
            expected_length = 10.0 - max(
                RectangularBeam.nominal_covering, 3 * bar.diameter_mm / 10
            )  # cm
            assert_approx(
                bar.left_length, expected_length, "Axis to the outer face (cm)"
            )


@pytest.fixture
def pillar_beam() -> RectangularBeam:
    """Build a beam double (CA50, 20x60 cm, 500 cm long) over 20 cm-wide end pillars."""
    beam = types.SimpleNamespace(
        steel=Steel.CA50,
        width=20.0,
        height=60.0,
        length=500.0,
        supports=[Support(0.0, -10.0, 10.0), Support(500.0, 490.0, 510.0)],
    )
    return cast(RectangularBeam, beam)


def _make_top_reinforcement(
    beam: RectangularBeam, center_position: float, is_tensioned: bool = True
) -> Reinforcement:
    """Build a top Reinforcement over the beam at a given center (cm)."""
    reinforcement = Reinforcement(
        beam,
        is_bottom_reinforcement=False,
        center_position=center_position,
        id="R",
        is_tensioned=is_tensioned,
    )
    reinforcement.moment_shift = 28.0  # cm
    return reinforcement


_SHORT_BEAM_LENGTH = 60.0  # cm, too short to anchor any bar past a_l = 28 cm


def _make_short_beam(supports: list[Support]) -> RectangularBeam:
    """Build a 20x60 cm beam double, 60 cm long, over the given supports."""
    beam = types.SimpleNamespace(
        steel=Steel.CA50,
        width=20.0,
        height=60.0,
        length=_SHORT_BEAM_LENGTH,
        label="V1",
        supports=supports,
    )
    return cast(RectangularBeam, beam)


def _make_clamp_ready_reinforcement(beam: RectangularBeam) -> Reinforcement:
    """Build a midspan bottom Reinforcement with d and V_d set for clamps."""
    reinforcement = _make_reinforcement(beam, center_position=_SHORT_BEAM_LENGTH / 2)
    reinforcement.effective_depth = 55.0  # cm
    reinforcement.design_shear = 100.0  # kN
    return reinforcement


@pytest.fixture
def wide_supports() -> list[Support]:
    """Return 20 cm-wide supports at both ends of the short beam."""
    return [
        Support(0.0, -10.0, 10.0),
        Support(
            _SHORT_BEAM_LENGTH, _SHORT_BEAM_LENGTH - 10.0, _SHORT_BEAM_LENGTH + 10.0
        ),
    ]


class TestClampPass:
    """Clamps are only allowed once no option anchors without them."""

    def test_anchorable_option_gets_no_clamps(
        self, reinforcement: Reinforcement
    ) -> None:
        """Bars that anchor straight or hooked never get clamps."""
        reinforcement.set_required_area(4.02)
        for layer in reinforcement.chosen_bars:
            assert layer.left_clamps is None, "No left clamps when bars anchor"
            assert layer.right_clamps is None, "No right clamps when bars anchor"

    def test_short_beam_uses_clamps(self, wide_supports: list[Support]) -> None:
        """When no option anchors, the clamp pass chooses one with clamps on both sides."""
        reinforcement = _make_clamp_ready_reinforcement(_make_short_beam(wide_supports))
        reinforcement.set_required_area(2.0)
        assert reinforcement.is_chosen, "An option should be chosen with clamps"
        for layer in reinforcement.chosen_bars:
            if not layer.bars:
                continue
            assert layer.left_clamps is not None, "Left side needs clamps"
            assert layer.right_clamps is not None, "Right side needs clamps"

    def test_short_beam_without_support_width_raises(self) -> None:
        """Zero-width supports leave no room for clamps, so choosing still fails."""
        supports = [
            Support(0.0, 0.0, 0.0),
            Support(_SHORT_BEAM_LENGTH, _SHORT_BEAM_LENGTH, _SHORT_BEAM_LENGTH),
        ]
        reinforcement = _make_clamp_ready_reinforcement(_make_short_beam(supports))
        with pytest.raises(
            NoReinforcementLayoutError, match="No valid reinforcement combination"
        ):
            reinforcement.set_required_area(2.0)

    def test_clamp_pass_requires_depth_and_shear(
        self, wide_supports: list[Support]
    ) -> None:
        """Reaching the clamp pass without d or V_d raises instead of failing silently."""
        reinforcement = _make_reinforcement(
            _make_short_beam(wide_supports), center_position=_SHORT_BEAM_LENGTH / 2
        )
        with pytest.raises(
            EnginePreconditionError, match="Effective depth and design shear"
        ):
            reinforcement.set_required_area(2.0)


class TestAnchorageSummaries:
    """The chosen bars keep their final l_b and l_b,nec per layer and side (cm)."""

    def test_one_summary_per_layer_and_side(self, reinforcement: Reinforcement) -> None:
        reinforcement.set_required_area(4.02)  # 2φ16 in layer 0
        sides = [(a.layer_index, a.side) for a in reinforcement.anchorages]
        assert sides == [(0, "left"), (0, "right")], (
            "only the non-empty layer 0 should be summarized, left then right"
        )

    def test_lengths_are_within_bounds(self, reinforcement: Reinforcement) -> None:
        """25φ ≤ l_b; 0.3·l_b ≤ l_b,nec ≤ l_b for a straight bar with As,ef ≥ As,req"""
        reinforcement.set_required_area(4.02)
        for summary in reinforcement.anchorages:
            assert summary.basic_length >= 25 * 1.6, "l_b of a 16 mm bar ≥ 25φ"
            assert summary.necessary_length <= summary.basic_length + 1e-9, (
                "l_b,nec should not exceed l_b with As,ef ≥ As,req and α ≤ 1"
            )
            assert summary.necessary_length >= 0.3 * summary.basic_length - 1e-9, (
                "l_b,nec should respect l_b,min"
            )

    def test_hooked_side_uses_reduced_length(
        self, beam_double: RectangularBeam
    ) -> None:
        """At x = 0 the left bars are hooked (α = 0.7); the right ones straight"""
        reinforcement = _make_reinforcement(beam_double, center_position=0.0)
        reinforcement.set_required_area(4.02)
        left, right = reinforcement.anchorages
        assert left.necessary_length < right.necessary_length, (
            "the hooked side should need a shorter anchorage"
        )

    def test_empty_before_choosing(self, reinforcement: Reinforcement) -> None:
        assert reinforcement.anchorages == ()

    def test_only_the_chosen_option_is_kept(self, reinforcement: Reinforcement) -> None:
        """Options tried and discarded leave no summaries behind"""
        reinforcement.set_required_area(18.0)  # several options tried, 2 layers
        used = [i for i, layer in enumerate(reinforcement.chosen_bars) if layer.bars]
        expected = [(i, side) for i in used for side in ("left", "right")]
        sides = [(a.layer_index, a.side) for a in reinforcement.anchorages]
        assert sides == expected, "one summary per used layer and side of the choice"


_TWO_SPAN_LENGTH = 1000.0  # cm


@pytest.fixture
def two_span_reinforcement() -> Reinforcement:
    """Choose 2φ16 at the middle of the first span of a two-span 1000 cm beam

    The pillars are 20 cm wide: 0 (-10..10), 500 (490..510) and 1000 (990..1010).
    The bars stop well short of both supports of the span.
    """
    beam = types.SimpleNamespace(
        steel=Steel.CA50,
        width=20.0,
        height=60.0,
        length=_TWO_SPAN_LENGTH,
        label="V1",
        supports=[
            Support(0.0, -10.0, 10.0),
            Support(500.0, 490.0, 510.0),
            Support(1000.0, 990.0, 1010.0),
        ],
    )
    reinforcement = Reinforcement(
        cast(RectangularBeam, beam),
        is_bottom_reinforcement=True,
        center_position=250.0,
        id="R",
        support_moments=(0.0, -40.0, 0.0),
        span_moment=50.0,
    )
    reinforcement.moment_shift = 28.0  # cm
    reinforcement.effective_depth = 55.0  # cm
    reinforcement.design_shear = 100.0  # kN
    reinforcement.set_required_area(4.02)  # 2φ16 in layer 0
    return reinforcement


class TestLayerReachesSupport:
    """A layer reaches a support when it is anchored inside it (NBR 6118 - 18.3.2.4.1)."""

    def test_short_bars_do_not_reach(
        self, two_span_reinforcement: Reinforcement
    ) -> None:
        assert not two_span_reinforcement.layer_reaches_support(0, 1, left=False), (
            "bars anchored near midspan do not reach the inner support"
        )
        assert not two_span_reinforcement.layer_reaches_support(0, 0, left=True), (
            "bars anchored near midspan do not reach the outer support"
        )

    def test_empty_layer_raises(self, two_span_reinforcement: Reinforcement) -> None:
        with pytest.raises(EnginePreconditionError, match="no bars"):
            two_span_reinforcement.layer_reaches_support(1, 1, left=False)


class TestExtendLayerToSupport:
    """Extending a layer anchors it inside the support, replacing that side."""

    def test_inner_support_ten_diameters(
        self, two_span_reinforcement: Reinforcement
    ) -> None:
        """Face at 490 cm, 240 cm from the section; 10φ = 16 cm"""
        two_span_reinforcement.extend_layer_to_support(0, 1, left=False)
        for bar in _bars(two_span_reinforcement):
            assert_approx(bar.right_length, 256.0, "Face distance + 10φ (cm)")
            assert not bar.right_hook_enabled, "Straight bars past the face"
        assert two_span_reinforcement.layer_reaches_support(0, 1, left=False), (
            "the extended layer reaches the support"
        )

    def test_other_side_is_kept(self, two_span_reinforcement: Reinforcement) -> None:
        before = [bar.left_length for bar in _bars(two_span_reinforcement)]
        two_span_reinforcement.extend_layer_to_support(0, 1, left=False)
        after = [bar.left_length for bar in _bars(two_span_reinforcement)]
        assert after == before, "the left side is untouched"

    def test_outer_support(self, two_span_reinforcement: Reinforcement) -> None:
        two_span_reinforcement.extend_layer_to_support(0, 0, left=True)
        assert two_span_reinforcement.layer_reaches_support(0, 0, left=True), (
            "the extended layer is anchored inside the outer support"
        )
        for bar in _bars(two_span_reinforcement):
            assert bar.left_length > 240.0, "bars run past the face at 10 cm"
        assert two_span_reinforcement.chosen_bars[0].left_clamps is not None, (
            "the 20 cm pillar is too narrow for l_b,nec; clamps complete it"
        )

    def test_clamps_count_as_reaching(
        self, two_span_reinforcement: Reinforcement
    ) -> None:
        layer = two_span_reinforcement.chosen_bars[0]
        layer.set_clamps(
            True, Clamps(diameter=6.3, quantity=1, length=10.0, width=10.0)
        )
        assert two_span_reinforcement.layer_reaches_support(0, 0, left=True), (
            "clamps on a side mean the bars are anchored in its support"
        )

    def test_summary_replaced_in_order(
        self, two_span_reinforcement: Reinforcement
    ) -> None:
        left_before = two_span_reinforcement.anchorages[0]
        two_span_reinforcement.extend_layer_to_support(0, 1, left=False)
        sides = [(a.layer_index, a.side) for a in two_span_reinforcement.anchorages]
        assert sides == [(0, "left"), (0, "right")], (
            "one summary per side, left then right"
        )
        assert two_span_reinforcement.anchorages[0] == left_before, (
            "the left summary is kept"
        )

    def test_clamps_on_that_side_are_dropped(
        self, two_span_reinforcement: Reinforcement
    ) -> None:
        layer = two_span_reinforcement.chosen_bars[0]
        layer.set_clamps(
            False, Clamps(diameter=6.3, quantity=1, length=10.0, width=10.0)
        )
        two_span_reinforcement.extend_layer_to_support(0, 1, left=False)
        assert layer.right_clamps is None, "10φ past the face needs no clamps"


def _support_point(
    base: Reinforcement, stacked: bool, required_area: float = 1.0
) -> Reinforcement:
    """Size bars at the left end support's inner face (10 cm) of the base's beam"""
    reinforcement = Reinforcement(
        base.beam,
        is_bottom_reinforcement=True,
        center_position=10.0,
        id="S",
        anchored_support=0,
        stacked_on=base if stacked else None,
    )
    reinforcement.moment_shift = 28.0  # cm
    reinforcement.effective_depth = 55.0  # cm
    reinforcement.design_shear = 100.0  # kN
    reinforcement.set_required_area(required_area)
    return reinforcement


class TestAnchoredSupportPoint:
    """A point on a support's inner face anchors inside it and runs into the span."""

    def test_anchored_inside_the_support(
        self, two_span_reinforcement: Reinforcement
    ) -> None:
        point = _support_point(two_span_reinforcement, stacked=False)
        for bar in _bars(point):
            assert bar.left_length > 0, "the bars enter the support past its face"
            assert point.center_position - bar.left_length >= -10.0, (
                "the bars stay inside the pillar (-10..10 cm)"
            )
        assert point.layer_reaches_support(0, 0, left=True), (
            "the bars are anchored inside the support (18.3.2.4.1)"
        )

    def test_runs_into_the_span(self, two_span_reinforcement: Reinforcement) -> None:
        """Towards the span: at least a_l = 28 cm plus l_b,nec"""
        point = _support_point(two_span_reinforcement, stacked=False)
        right_summary = next(a for a in point.anchorages if a.side == "right")
        for bar in _bars(point):
            assert bar.right_length >= 28.0 + right_summary.necessary_length - 1e-9, (
                "the span side is anchored like an interest point"
            )


class TestStackedReinforcement:
    """A reinforcement stacked on another one starts after the base's last layer."""

    def test_first_layer_index(self, two_span_reinforcement: Reinforcement) -> None:
        point = _support_point(two_span_reinforcement, stacked=True)
        assert point.first_layer_index == 1, "the base fills layer 0"
        assert len(point.chosen_bars) == APP_CONFIG.max_layers - 1, (
            "only the layers left after the base's are available"
        )

    def test_unstacked_starts_at_zero(
        self, two_span_reinforcement: Reinforcement
    ) -> None:
        point = _support_point(two_span_reinforcement, stacked=False)
        assert point.first_layer_index == 0, "no base: the first layer is 0"

    def test_layer_sits_above_the_base(
        self, two_span_reinforcement: Reinforcement
    ) -> None:
        """Base edge (1.6 cm) + spacing for the larger φ + half the new φ"""
        point = _support_point(two_span_reinforcement, stacked=True)
        base_layer = two_span_reinforcement.chosen_bars[0]
        new_diameter = max(b.diameter_mm for b in point.chosen_bars[0].bars) / 10
        spacing = Reinforcement.get_vertical_spacing(max(1.6, new_diameter))
        expected = base_layer.y_centroid_position - 0.8 + 1.6 + spacing
        expected += new_diameter / 2
        assert_approx(
            point.chosen_bars[0].y_centroid_position,
            expected,
            "y of the stacked layer from the bottom face (cm)",
        )

    def test_same_covering_as_the_base(
        self, two_span_reinforcement: Reinforcement
    ) -> None:
        point = _support_point(two_span_reinforcement, stacked=True)
        assert_approx(
            point.effective_covering(),
            two_span_reinforcement.effective_covering(),
            "the stacked bars sit inside the same stirrup (cm)",
        )

    def test_no_layer_left_raises(
        self, two_span_reinforcement: Reinforcement, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(APP_CONFIG, "max_layers", 1)
        with pytest.raises(MaxLayersExceededError, match="No layer left"):
            _support_point(two_span_reinforcement, stacked=True)


# ---------------------------------------------------------------------------
# Staggering by layer (NBR 6118 - Section 18.3.2.3.1)
# ---------------------------------------------------------------------------

_SECTION_MOMENT = 30.0  # kN.m


def _no_positions(level: float) -> list[float]:
    """Stand in for a moment diagram that never reaches the level"""
    return []


def _staggered(
    beam: RectangularBeam, center_position: float = 250.0, is_tensioned: bool = True
) -> Reinforcement:
    """Build a bottom reinforcement with 2φ16 in layer 0 and 1φ10 in layer 1, staggered"""
    reinforcement = Reinforcement(
        beam,
        is_bottom_reinforcement=True,
        center_position=center_position,
        id="R",
        is_tensioned=is_tensioned,
        section_moment=_SECTION_MOMENT,
        moment_positions=_no_positions,
    )
    reinforcement.moment_shift = 28.0  # cm
    _place_layers(reinforcement, (16.0, 16.0), (10.0,))
    return reinforcement


def _set_lengths(layer: Layer, left: float, right: float) -> None:
    """Set the side lengths (cm) of every bar of a layer"""
    layer.set_anchorage_length(left, left=True)
    layer.set_anchorage_length(right, left=False)


def _enforce(reinforcement: Reinforcement) -> None:
    """Run the staggered-length pass on the reinforcement"""
    reinforcement._enforce_staggered_lengths()  # pyright: ignore[reportPrivateUsage]


class TestLayerMomentBand:
    """Tests for the band of the section moment each layer resists (kN.m)."""

    def test_bands_follow_the_layer_areas(self, beam_double: RectangularBeam) -> None:
        reinforcement = _staggered(beam_double)
        areas = [layer.area for layer in reinforcement.chosen_bars[:2]]  # cm²
        split = _SECTION_MOMENT * areas[0] / sum(areas)  # kN.m
        first = reinforcement.layer_moment_band(0)
        innermost = reinforcement.layer_moment_band(1)
        assert first is not None and innermost is not None, "both layers staggered"
        assert_approx(first[0], 0.0, "first band starts at zero (kN.m)")
        assert_approx(first[1], split, "first band top by area share (kN.m)")
        assert_approx(innermost[0], split, "innermost band bottom (kN.m)")
        assert_approx(innermost[1], _SECTION_MOMENT, "innermost band ends at M (kN.m)")

    def test_compressed_bars_are_not_staggered(
        self, beam_double: RectangularBeam
    ) -> None:
        reinforcement = _staggered(beam_double, is_tensioned=False)
        assert reinforcement.layer_moment_band(0) is None, "compressed: no band"

    def test_no_diagram_is_not_staggered(self, reinforcement: Reinforcement) -> None:
        _place_layers(reinforcement, (16.0,))
        assert reinforcement.layer_moment_band(0) is None, "no diagram: no band"

    def test_empty_layer_raises(self, beam_double: RectangularBeam) -> None:
        reinforcement = _staggered(beam_double)
        with pytest.raises(EnginePreconditionError, match="no bars"):
            reinforcement.layer_moment_band(2)


class TestEnforceStaggeredLengths:
    """Tests for keeping each layer at least as long as the layer above it (cm)."""

    def test_lower_layer_is_raised(self, beam_double: RectangularBeam) -> None:
        reinforcement = _staggered(beam_double)
        first, innermost = reinforcement.chosen_bars[:2]
        _set_lengths(first, left=50.0, right=100.0)
        _set_lengths(innermost, left=80.0, right=60.0)
        _enforce(reinforcement)
        for bar in first.bars:
            assert_approx(bar.left_length, 80.0, "raised to the layer above (cm)")
            assert_approx(bar.right_length, 100.0, "already longer: kept (cm)")

    def test_raise_is_capped_by_the_space(self, beam_double: RectangularBeam) -> None:
        reinforcement = _staggered(beam_double)
        first, innermost = reinforcement.chosen_bars[:2]
        _set_lengths(first, left=50.0, right=50.0)
        _set_lengths(innermost, left=400.0, right=50.0)
        _enforce(reinforcement)
        space = 250.0 - RectangularBeam.nominal_covering  # cm
        for bar in first.bars:
            assert_approx(bar.left_length, space, "capped at the beam's end (cm)")

    def test_hooked_raise_keeps_the_hook_cover(
        self, beam_double: RectangularBeam
    ) -> None:
        """Hooked 16 mm bars keep max(c_nom, 3φ) to the beam's end"""
        reinforcement = _staggered(beam_double)
        first, innermost = reinforcement.chosen_bars[:2]
        first.set_hooks(left=True, enable=True)
        _set_lengths(first, left=50.0, right=50.0)
        _set_lengths(innermost, left=400.0, right=50.0)
        _enforce(reinforcement)
        covering = RectangularBeam.nominal_covering  # cm
        expected = 250.0 - max(covering, 3 * 1.6)  # cm
        for bar in first.bars:
            assert_approx(bar.left_length, expected, "capped before the hook (cm)")

    def test_side_with_clamps_is_kept(self, beam_double: RectangularBeam) -> None:
        reinforcement = _staggered(beam_double)
        first, innermost = reinforcement.chosen_bars[:2]
        _set_lengths(first, left=50.0, right=50.0)
        _set_lengths(innermost, left=80.0, right=50.0)
        first.set_clamps(
            True, Clamps(diameter=6.3, quantity=1, length=10.0, width=10.0)
        )
        _enforce(reinforcement)
        for bar in first.bars:
            assert_approx(bar.left_length, 50.0, "clamped side left as it is (cm)")

    def test_end_support_side_is_kept(self, beam_double: RectangularBeam) -> None:
        reinforcement = _staggered(beam_double, center_position=0.0)
        first, innermost = reinforcement.chosen_bars[:2]
        _set_lengths(first, left=0.0, right=50.0)
        _set_lengths(innermost, left=10.0, right=80.0)
        _enforce(reinforcement)
        for bar in first.bars:
            assert_approx(bar.left_length, 0.0, "end support side left as it is (cm)")
            assert_approx(bar.right_length, 80.0, "interior side raised (cm)")
