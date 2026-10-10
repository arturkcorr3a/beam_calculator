"""Unit tests for the Reinforcement longitudinal-bar orchestration."""

import types
from typing import cast

import pytest

from src.config import APP_CONFIG
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.reinforcement.reinforcement import Reinforcement
from src.structural_elements.rebar import Rebar
from src.structural_elements.rectangular_beam import RectangularBeam
from tests.helpers import assert_approx


@pytest.fixture
def beam_double() -> RectangularBeam:
    """Build a light beam double (C25/CA50, 20x60 cm, 500 cm long).

    The reinforcement orchestration only reads material grades and geometry off
    the beam, so a ``SimpleNamespace`` cast to ``RectangularBeam`` avoids running
    the structural analysis while still driving the real
    ``RebarChooser`` and ``AnchorageCalculator``.
    """
    beam = types.SimpleNamespace(
        steel=Steel.CA50,
        concrete=Concrete.C25,
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
        reinforcement.set_required_area(4.0)
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
        ], "The optimal solution for 4 cm² is two 16 mm bars in layer 0"
        assert_approx(
            reinforcement.get_distance_for_d_calculation("R"),
            0.8,
            "The single-layer centroid sits 0.8 cm from the bottom edge",
        )

    def test_rechoosing_discards_previous_bars(
        self, reinforcement: Reinforcement
    ) -> None:
        """A second choice does not keep the multi-layer bars of the first (cm²)."""
        reinforcement.set_required_area(14.0)
        first_area = reinforcement.area
        assert len(reinforcement.chosen_bars[1].bars) > 0, (
            "14 cm² in a 20 cm wide beam should need a second layer"
        )

        reinforcement.set_required_area(14.0)

        assert_approx(
            reinforcement.area,
            first_area,
            "Re-choosing the same area should give the same bars, not pile them up",
        )


class TestValidateLayerIndex:
    """Tests for the layer-index bounds check."""

    def test_out_of_range_raises(self, reinforcement: Reinforcement) -> None:
        reinforcement.set_required_area(4.0)
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


class TestClearChosenBars:
    """Tests for resetting the chosen-bar layers."""

    def test_resets_layers(self, reinforcement: Reinforcement) -> None:
        reinforcement.set_required_area(4.0)
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
        reinforcement.set_required_area(4.0)
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
        reinforcement.set_required_area(4.0)
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
        at_start.set_required_area(4.0)
        at_midspan = _make_reinforcement(beam_double, center_position=250.0)
        at_midspan.set_required_area(4.0)
        assert_approx(
            _bars(at_start)[0].right_length,
            _bars(at_midspan)[0].right_length,
            "Right anchorage at x = 0 should equal the mid-span one (cm)",
        )

    def test_midspan_anchors_both_sides(self, beam_double: RectangularBeam) -> None:
        """Away from the ends both anchorage lengths are calculated (cm)."""
        reinforcement = _make_reinforcement(beam_double, center_position=250.0)
        reinforcement.set_required_area(4.0)
        for bar in _bars(reinforcement):
            assert bar.left_length > 0, "Left anchorage should be calculated"
            assert bar.right_length > 0, "Right anchorage should be calculated"
            assert bar.left_hook_enabled is False, "No left hook away from the ends"
            assert bar.right_hook_enabled is False, "No right hook away from the ends"
