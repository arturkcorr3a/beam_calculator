"""Tests for src/detailing/builder.py."""

import types
from typing import cast

import pytest

from src.config import APP_CONFIG
from src.detailing.builder import build_detailing_beam
from src.detailing.detailed_bar import BarRole, DetailedBar
from src.pavement_elements.continuous_beam import ContinuousBeam
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.reinforcement.clamps import Clamps
from src.reinforcement.reinforcement import Reinforcement
from src.reinforcement.stirrups import StirrupZone
from src.structural_elements.rebar import HookGeometry, Rebar
from src.structural_elements.rectangular_beam import RectangularBeam
from src.structural_elements.support import Support
from tests.helpers import assert_approx


@pytest.fixture(autouse=True)
def pinned_concrete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the project concrete to C30 for every test in this module"""
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C30)


@pytest.fixture
def structural_beam() -> RectangularBeam:
    """Build a 20 x 60 cm, 500 cm long CA-50 section on pillars 20, 30 and 20 cm wide"""
    beam = types.SimpleNamespace(
        steel=Steel.CA50,
        width=20.0,
        height=60.0,
        length=500.0,
        supports=[
            Support(0.0, -10.0, 10.0),
            Support(250.0, 235.0, 265.0),
            Support(500.0, 490.0, 510.0),
        ],
    )
    return cast(RectangularBeam, beam)


def _bar(diameter_mm: float, left: float, right: float) -> Rebar:
    """Build a CA-50 bar with the given straight lengths to each side (cm)"""
    bar = Rebar(diameter_mm=diameter_mm, steel=Steel.CA50)
    bar.left_length = left
    bar.right_length = right
    return bar


@pytest.fixture
def bottom_reinforcement(structural_beam: RectangularBeam) -> Reinforcement:
    """Build a bottom reinforcement at x = 125 cm: layer 0 with 2φ16 + 1φ10, layer 1 with 1φ16

    Layer 0's φ16 has a right hook; layer 1's φ16 is its own instance with longer lengths.
    """
    reinforcement = Reinforcement(
        structural_beam, is_bottom_reinforcement=True, center_position=125.0
    )
    reinforcement.required_area = 4.5  # cm²
    bar_16 = _bar(16, 100.0, 110.0)
    bar_16.right_hook_enabled = True
    bar_10 = _bar(10, 90.0, 90.0)
    layer_0, layer_1 = reinforcement.chosen_bars[0], reinforcement.chosen_bars[1]
    layer_0.bars = [bar_16, bar_10, bar_16]
    layer_0.y_centroid_position = 4.5  # cm
    layer_1.bars = [_bar(16, 120.0, 130.0)]
    layer_1.y_centroid_position = 8.9  # cm
    return reinforcement


@pytest.fixture
def top_reinforcement(structural_beam: RectangularBeam) -> Reinforcement:
    """Build a compressed top reinforcement at x = 125 cm with 2φ12.5, 80 cm to each side"""
    reinforcement = Reinforcement(
        structural_beam,
        is_bottom_reinforcement=False,
        center_position=125.0,
        is_tensioned=False,
    )
    reinforcement.required_area = 2.0  # cm²
    bar = _bar(12.5, 80.0, 80.0)
    layer = reinforcement.chosen_bars[0]
    layer.bars = [bar, bar]
    layer.y_centroid_position = 56.0  # cm
    return reinforcement


def _beam(
    structural_beam: RectangularBeam,
    reinforcements: list[Reinforcement],
    spacing: float | None = 15.0,
    zones: tuple[list[StirrupZone], list[StirrupZone]] = ([], []),
    slab_thicknesses: tuple[float | None, float | None] = (None, None),
) -> ContinuousBeam:
    """Build a dimensioned two-span beam double with φ6.3 stirrups

    Args:
        spacing: Chosen (edge) stirrup spacing of both spans (cm).
        zones: Design spacing zones of each span, along the beam (cm); empty when the stirrups were not distributed.
        slab_thicknesses: Thickness of the two slabs on the first span (cm), None for no slab.
    """
    first_span_slabs = tuple(
        None if thickness is None else types.SimpleNamespace(thickness=thickness)
        for thickness in slab_thicknesses
    )
    spans = [
        types.SimpleNamespace(
            start_pillar_id=start_id,
            end_pillar_id=end_id,
            supported_slabs=slabs,
            stirrups=types.SimpleNamespace(
                beam=structural_beam,
                diameter=0.63,
                spacing=spacing,
                steel=Steel.CA50,
                zones=span_zones,
            ),
        )
        for (start_id, end_id), span_zones, slabs in zip(
            [("P1", "P2"), ("P2", "P3")],
            zones,
            [first_span_slabs, (None, None)],
            strict=True,
        )
    ]
    beam = types.SimpleNamespace(
        id="V9",
        analysis=types.SimpleNamespace(),
        spans=spans,
        reinforcement=reinforcements,
    )
    return cast(ContinuousBeam, beam)


def _run(bars: list[DetailedBar], layer_index: int, diameter_mm: float) -> DetailedBar:
    """Return the only bar run of a layer and diameter"""
    runs = [
        bar
        for bar in bars
        if bar.layer_index == layer_index and bar.diameter_mm == diameter_mm
    ]
    assert len(runs) == 1, f"Expected one φ{diameter_mm:g} run in layer {layer_index}"
    return runs[0]


class TestBuildSection:
    """The detailing beam copies the section, cover and supports."""

    def test_copies_section_and_supports(
        self, structural_beam: RectangularBeam, bottom_reinforcement: Reinforcement
    ) -> None:
        beam = _beam(structural_beam, [bottom_reinforcement])
        detailing = build_detailing_beam(beam)
        assert detailing.beam_id == "V9", "The detailing should name its beam"
        assert (detailing.width, detailing.height) == (20.0, 60.0), (
            "The section should be copied (cm)"
        )
        assert detailing.nominal_covering == RectangularBeam.nominal_covering, (
            "The cover should be the project's nominal cover"
        )
        assert detailing.supports == tuple(structural_beam.supports), (
            "The supports should be copied"
        )
        assert (detailing.start, detailing.end) == (-10.0, 510.0), (
            "The beam should run between the end pillars' outer faces (cm)"
        )
        assert detailing.analysis is beam.analysis, (
            "The detailing should keep the beam's analysis"
        )


class TestBuildBars:
    """Each layer becomes one bar run per diameter, with the layer's own lengths."""

    def test_one_run_per_layer_and_diameter(
        self, structural_beam: RectangularBeam, bottom_reinforcement: Reinforcement
    ) -> None:
        detailing = build_detailing_beam(_beam(structural_beam, [bottom_reinforcement]))
        runs = [(b.layer_index, b.diameter_mm, b.quantity) for b in detailing.bars]
        assert runs == [(0, 16, 2), (0, 10, 1), (1, 16, 1)], (
            "Runs should follow the layers, largest diameter first, with each count"
        )

    def test_runs_take_extent_from_center_and_lengths(
        self, structural_beam: RectangularBeam, bottom_reinforcement: Reinforcement
    ) -> None:
        detailing = build_detailing_beam(_beam(structural_beam, [bottom_reinforcement]))
        layer_0_bar = _run(detailing.bars, 0, 16)
        layer_1_bar = _run(detailing.bars, 1, 16)
        assert (layer_0_bar.start, layer_0_bar.end) == (25.0, 235.0), (
            "Layer 0's φ16 should run 125 − 100 to 125 + 110 cm"
        )
        assert (layer_1_bar.start, layer_1_bar.end) == (5.0, 255.0), (
            "Layer 1's φ16 should keep its own lengths, 125 − 120 to 125 + 130 cm"
        )

    def test_hooks_copied_per_side(
        self, structural_beam: RectangularBeam, bottom_reinforcement: Reinforcement
    ) -> None:
        detailing = build_detailing_beam(_beam(structural_beam, [bottom_reinforcement]))
        bar = _run(detailing.bars, 0, 16)
        source = bottom_reinforcement.chosen_bars[0].bars[0]
        assert bar.left_hook is None, "The left side has no hook"
        assert bar.left_hook_length == 0.0, "No left hook, no extra length"
        assert bar.right_hook == HookGeometry(pin_diameter=8.0, tip_length=12.8), (
            "The right hook should be the standard CA-50 φ16 hook (5φ pin, 8φ tip)"
        )
        assert_approx(
            bar.right_hook_length,
            source.right_hook_length,
            "The right hook's extra length should be the source bar's",
        )
        assert_approx(
            bar.total_length,
            source.total_length,
            "The cut length should be the source bar's",
        )

    def test_bars_of_a_layer_share_its_edge(
        self, structural_beam: RectangularBeam, bottom_reinforcement: Reinforcement
    ) -> None:
        detailing = build_detailing_beam(_beam(structural_beam, [bottom_reinforcement]))
        bar_16 = _run(detailing.bars, 0, 16)
        bar_10 = _run(detailing.bars, 0, 10)
        assert_approx(
            bar_16.y - 0.8,
            bar_10.y - 0.5,
            "Both diameters should touch the same edge line (cm)",
        )
        mean_y = (2 * 2.0106193 * bar_16.y + 0.7853982 * bar_10.y) / (
            2 * 2.0106193 + 0.7853982
        )
        assert_approx(
            mean_y,
            4.5,
            "The area-weighted mean axis height should be the layer centroid (cm)",
            abs_tol=1e-4,
        )

    def test_top_bar_axis_measured_from_bottom(
        self, structural_beam: RectangularBeam, top_reinforcement: Reinforcement
    ) -> None:
        detailing = build_detailing_beam(_beam(structural_beam, [top_reinforcement]))
        bar = detailing.bars[0]
        assert_approx(
            bar.y, 56.0, "A single-diameter layer's axis is the layer centroid (cm)"
        )
        assert not bar.is_bottom, "The bars should be on the top face"

    def test_copies_design_flags(
        self,
        structural_beam: RectangularBeam,
        bottom_reinforcement: Reinforcement,
        top_reinforcement: Reinforcement,
    ) -> None:
        beam = _beam(structural_beam, [bottom_reinforcement, top_reinforcement])
        detailing = build_detailing_beam(beam)
        bottom_bar = _run(detailing.bars_on_face(is_bottom=True), 0, 16)
        top_bar = detailing.bars_on_face(is_bottom=False)[0]
        assert bottom_bar.is_tensioned, "The bottom bars were designed tensioned"
        assert not top_bar.is_tensioned, "The top bars were designed compressed"
        assert bottom_bar.role == BarRole.MAIN, "Designed bars are main bars"
        assert bottom_bar.source_positions == (125.0,), (
            "Source is the interest point (cm)"
        )
        assert bottom_bar.good_adherence, "A layer at 4.5 cm sits in the good bond zone"
        assert_approx(
            bottom_bar.area_ratio,
            4.5 / bottom_reinforcement.area,
            "Area ratio should be the required over the provided area",
        )


class TestBuildClamps:
    """One clamp set per side, even when several layers share it."""

    def test_shared_clamps_copied_once(
        self, structural_beam: RectangularBeam, bottom_reinforcement: Reinforcement
    ) -> None:
        clamps = Clamps(diameter=12.5, quantity=1, width=12.7, length=50.9)
        for layer in bottom_reinforcement.chosen_bars[:2]:
            layer.set_clamps(left=True, clamps=clamps)
        detailing = build_detailing_beam(_beam(structural_beam, [bottom_reinforcement]))
        assert len(detailing.clamps) == 1, "A shared clamp set should be copied once"
        detailed = detailing.clamps[0]
        assert detailed.left, "The clamps anchor the left end"
        assert detailed.is_bottom, "The clamps anchor bottom bars"
        assert detailed.position == 25.0, (
            "The U should bend at layer 0's left end, 125 − 100 cm"
        )
        assert (detailed.diameter_mm, detailed.quantity) == (12.5, 1), (
            "Diameter (mm) and quantity should be copied"
        )
        assert_approx(
            detailed.total_length, 2 * 50.9 + 12.7, "Cut length is 2 legs + width (cm)"
        )

    def test_no_clamps(
        self, structural_beam: RectangularBeam, bottom_reinforcement: Reinforcement
    ) -> None:
        detailing = build_detailing_beam(_beam(structural_beam, [bottom_reinforcement]))
        assert detailing.clamps == [], "Layers without clamps give no clamp sets"


class TestBuildStirrups:
    """Each span's stirrup zones are clipped to the inner faces of its pillars."""

    def test_stirrups_between_inner_faces(
        self, structural_beam: RectangularBeam, bottom_reinforcement: Reinforcement
    ) -> None:
        detailing = build_detailing_beam(_beam(structural_beam, [bottom_reinforcement]))
        first, second = detailing.stirrups
        assert (first.start, first.end) == (10.0, 235.0), (
            "Span P1–P2 stirrups run from P1's right face to P2's left face (cm)"
        )
        assert (second.start, second.end) == (265.0, 490.0), (
            "Span P2–P3 stirrups run from P2's right face to P3's left face (cm)"
        )
        assert first.diameter_mm == 6.3, "The diameter should be converted to mm"
        assert (first.outer_width, first.outer_height) == (15.0, 55.0), (
            "The stirrup sits on the 2.5 cm cover of a 20 x 60 cm section (cm)"
        )
        assert_approx(
            first.cut_length,
            149.27522023056943,
            "Raw cut length of a φ6.3 CA-50 stirrup (cm)",
        )
        assert (first.start_pillar_id, first.end_pillar_id) == ("P1", "P2"), (
            "The span's pillars should be copied"
        )

    def test_undistributed_stirrups_are_one_zone(
        self, structural_beam: RectangularBeam, bottom_reinforcement: Reinforcement
    ) -> None:
        detailing = build_detailing_beam(_beam(structural_beam, [bottom_reinforcement]))
        assert detailing.stirrups[0].zones == (StirrupZone(10.0, 235.0, 15.0),), (
            "Stirrups without zones should be one zone at the chosen spacing (cm)"
        )

    def test_scaled_zones_clipped_to_faces(
        self, structural_beam: RectangularBeam, bottom_reinforcement: Reinforcement
    ) -> None:
        first_span = [
            StirrupZone(0.0, 60.0, 12.0),
            StirrupZone(60.0, 190.0, 24.0),
            StirrupZone(190.0, 250.0, 12.0),
        ]
        second_span = [StirrupZone(250.0, 500.0, 24.0)]
        beam = _beam(
            structural_beam,
            [bottom_reinforcement],
            spacing=12.0,
            zones=(first_span, second_span),
        )
        first, second = build_detailing_beam(beam).stirrups
        assert first.zones == (
            StirrupZone(10.0, 60.0, 12.0),
            StirrupZone(60.0, 190.0, 24.0),
            StirrupZone(190.0, 235.0, 12.0),
        ), "The edge zones should start and end at the pillars' faces (cm)"
        assert second.zones == (StirrupZone(265.0, 490.0, 24.0),), (
            "A single zone should be clipped to both faces (cm)"
        )

    def test_zone_inside_pillar_dropped(
        self, structural_beam: RectangularBeam, bottom_reinforcement: Reinforcement
    ) -> None:
        first_span = [
            StirrupZone(0.0, 8.0, 12.0),
            StirrupZone(8.0, 242.0, 24.0),
            StirrupZone(242.0, 250.0, 12.0),
        ]
        beam = _beam(
            structural_beam,
            [bottom_reinforcement],
            spacing=12.0,
            zones=(first_span, [StirrupZone(250.0, 500.0, 24.0)]),
        )
        first = build_detailing_beam(beam).stirrups[0]
        assert first.zones == (StirrupZone(10.0, 235.0, 24.0),), (
            "Edge zones that end inside the pillars should be dropped (cm)"
        )

    def test_zones_not_covering_faces_raise(
        self, structural_beam: RectangularBeam, bottom_reinforcement: Reinforcement
    ) -> None:
        beam = _beam(
            structural_beam,
            [bottom_reinforcement],
            zones=([StirrupZone(50.0, 250.0, 15.0)], [StirrupZone(250.0, 500.0, 15.0)]),
        )
        with pytest.raises(ValueError, match="do not cover the stretch"):
            build_detailing_beam(beam)


class TestBuildClearSpans:
    """Each span runs between its pillars' inner faces, with the sides the slabs leave."""

    def test_extent_between_inner_faces(
        self, structural_beam: RectangularBeam, bottom_reinforcement: Reinforcement
    ) -> None:
        detailing = build_detailing_beam(_beam(structural_beam, [bottom_reinforcement]))
        first, second = detailing.clear_spans
        assert (first.start, first.end) == (10.0, 235.0), "P1's to P2's face (cm)"
        assert (second.start, second.end) == (265.0, 490.0), "P2's to P3's face (cm)"

    def test_no_slabs_leave_whole_sides(
        self, structural_beam: RectangularBeam, bottom_reinforcement: Reinforcement
    ) -> None:
        detailing = build_detailing_beam(_beam(structural_beam, [bottom_reinforcement]))
        assert detailing.clear_spans[0].side_heights == (60.0, 60.0), "Whole height"

    def test_one_slab_covers_one_side(
        self, structural_beam: RectangularBeam, bottom_reinforcement: Reinforcement
    ) -> None:
        beam = _beam(
            structural_beam, [bottom_reinforcement], slab_thicknesses=(10.0, None)
        )
        detailing = build_detailing_beam(beam)
        assert detailing.clear_spans[0].side_heights == (50.0, 60.0), (
            "The 10 cm slab covers one side"
        )
        assert detailing.clear_spans[1].side_heights == (60.0, 60.0), (
            "The other span has no slabs"
        )

    def test_two_slabs_cover_both_sides(
        self, structural_beam: RectangularBeam, bottom_reinforcement: Reinforcement
    ) -> None:
        beam = _beam(
            structural_beam, [bottom_reinforcement], slab_thicknesses=(10.0, 12.0)
        )
        assert build_detailing_beam(beam).clear_spans[0].side_heights == (50.0, 48.0), (
            "Each slab covers its own thickness"
        )


class TestBuildLeavesDesignUntouched:
    """Building and editing the detailing never changes the design objects."""

    def test_design_bars_unchanged(
        self, structural_beam: RectangularBeam, bottom_reinforcement: Reinforcement
    ) -> None:
        beam = _beam(structural_beam, [bottom_reinforcement])
        source = bottom_reinforcement.chosen_bars[0].bars[0]
        detailing = build_detailing_beam(beam)
        for bar in detailing.bars:
            bar.start -= 50.0
            bar.end += 50.0
        assert (source.left_length, source.right_length) == (100.0, 110.0), (
            "Editing the detailing should not change the design bar's lengths"
        )
        assert beam.reinforcement == [bottom_reinforcement], (
            "The beam's reinforcement list should stay the same"
        )


class TestBuildErrors:
    """The builder refuses beams it cannot detail."""

    def test_not_dimensioned_raises(
        self, structural_beam: RectangularBeam, bottom_reinforcement: Reinforcement
    ) -> None:
        beam = _beam(structural_beam, [bottom_reinforcement])
        beam.analysis = None
        with pytest.raises(ValueError, match="has not been dimensioned"):
            build_detailing_beam(beam)

    def test_stirrups_without_spacing_raise(
        self, structural_beam: RectangularBeam, bottom_reinforcement: Reinforcement
    ) -> None:
        beam = _beam(structural_beam, [bottom_reinforcement], spacing=None)
        with pytest.raises(ValueError, match="no stirrup diameter or spacing"):
            build_detailing_beam(beam)

    def test_missing_required_area_raises(
        self, structural_beam: RectangularBeam, bottom_reinforcement: Reinforcement
    ) -> None:
        bottom_reinforcement.required_area = None
        with pytest.raises(ValueError, match="no required or provided area"):
            build_detailing_beam(_beam(structural_beam, [bottom_reinforcement]))
