"""Tests for src/drawing/geometry.py."""

from dataclasses import replace
from math import hypot, pi

import pytest

from src.detailing.detailing_beam import DetailingBeam
from src.drawing.config import DrawingConfig
from src.drawing.geometry import (
    QUARTER_BULGE,
    arrange_row,
    bar_path,
    clamp_rows_y,
    hook_path,
    lowest_hook_point,
    overlap_pairs,
    pillar_ids,
    row_offsets,
    section_layers,
    section_positions,
    stirrup_bend,
    stirrup_positions,
    zone_labels,
)
from src.drawing.primitives import Point, arc_points
from src.pavement_elements.pavement import Pavement
from tests.drawing.helpers import close, detailings
from tests.drawing.v5 import bar


def _with_bar(beam: DetailingBeam, mark: str, **changes: float) -> DetailingBeam:
    """Return a copy of the beam with one bar run's fields changed"""
    bars = [
        replace(item, **changes) if item.mark == mark else item for item in beam.bars
    ]
    return replace(beam, bars=bars)


def _arc_middle(points: tuple[Point, ...], bulges: tuple[float, ...]) -> list[Point]:
    """Return the middle point of every arc of a polyline"""
    middles: list[Point] = []
    for index, bulge in enumerate(bulges):
        if bulge != 0.0:
            arc = arc_points(points[index], points[index + 1], bulge, 2)
            middles.append(arc[1])
    return middles


def _path_length(points: tuple[Point, ...], bulges: tuple[float, ...]) -> float:
    """Return the exact length of a polyline whose arcs are quarter circles (cm)"""
    length = 0.0
    for start, end, bulge in zip(points[:-1], points[1:], bulges[:-1], strict=True):
        chord = hypot(end[0] - start[0], end[1] - start[1])
        length += chord if bulge == 0.0 else pi / 2 * chord / 2**0.5
    return length


class TestPillarsAndStirrups:
    """Pillar names and stirrup layout, from the spans."""

    def test_pillar_ids(self, v5: DetailingBeam) -> None:
        assert pillar_ids(v5) == ["P10", "P11", "P12", "P13"], "One id per support"

    def test_stirrup_positions(self, v5: DetailingBeam) -> None:
        positions = stirrup_positions(v5.stirrups[0])
        assert len(positions) == v5.stirrups[0].quantity == 26, "26 stirrups in span 1"
        assert (positions[0], positions[-1]) == (9.5, 420.5), "Face to face (cm)"

    def test_zone_labels(self, v5: DetailingBeam) -> None:
        assert zone_labels(v5.stirrups[2]) == ["28 N9 φ5 c/12"], "Count, mark, spacing"

    def test_stirrup_bend(self, v5: DetailingBeam) -> None:
        assert close(stirrup_bend(v5.stirrups[0]), (1.5, 5.0)), (
            "φ5: D = 3φ and the 135° tip is at least 5 cm"
        )


class TestHooks:
    """Hooks bend toward the opposite face; start/end are the leg's outer face."""

    def test_frame_node_hook(self, v5: DetailingBeam) -> None:
        path = hook_path(bar(v5, "N1"), left=True)
        assert path is not None
        assert close(
            [c for point in path for c in point], [1.5, 46.5, -6.5, 38.5, -6.5, 8.5]
        ), "r = (15 + 1)/2 = 8; the tip stays inside the beam at y = 8.5"

    def test_long_leg_tip(self, v5: DetailingBeam) -> None:
        path = hook_path(bar(v5, "N8"), left=False)
        assert path is not None
        assert close(path[2], (1206.5, -19.5)), "46.5 − (8 + 58) = −19.5"

    def test_bottom_hook_goes_up(self, v5: DetailingBeam) -> None:
        path = hook_path(bar(v5, "N10"), left=True)
        assert path is not None
        assert close(path[2], (-6.5, 14.5)), "3.5 + 3 + 8 = 14.5"

    def test_no_hook(self, v5: DetailingBeam) -> None:
        assert hook_path(bar(v5, "N12"), left=True) is None, "N12 has no hook"

    def test_lowest_hook_point(self, v5: DetailingBeam) -> None:
        assert close(lowest_hook_point(v5), -20.0), "N8's leg outer face at −19.5 − 0.5"

    def test_lowest_hook_point_inside_beam(self, v5: DetailingBeam) -> None:
        beam = replace(v5, bars=[item for item in v5.bars if item.mark != "N8"])
        assert lowest_hook_point(beam) == 0.0, "No leg passes the bottom face"


class TestBarPath:
    """The axis polyline from the left tip to the right tip."""

    def test_straight_bar(self, v5: DetailingBeam) -> None:
        assert bar_path(bar(v5, "N12")) == (((415, 3.5), (875, 3.5)), (0.0, 0.0)), (
            "A bar without hooks is one segment"
        )

    @pytest.mark.parametrize("mark", ["N1", "N8", "N10", "N13"])
    def test_hook_ends_and_arc(self, v5: DetailingBeam, mark: str) -> None:
        run = bar(v5, mark)
        points, bulges = bar_path(run)
        hooks = [hook_path(run, left) for left in (True, False)]
        if hooks[0] is not None:
            assert points[0] == hooks[0][2], "The path starts at the left tip"
        if hooks[1] is not None:
            assert points[-1] == hooks[1][2], "The path ends at the right tip"
        assert sorted(abs(b) for b in bulges if b) == [QUARTER_BULGE], "One quarter arc"
        hook = next(path for path in hooks if path is not None)
        center = (hook[0][0], hook[1][1])
        radius = abs(hook[0][0] - hook[1][0])
        for middle in _arc_middle(points, bulges):
            assert close(hypot(middle[0] - center[0], middle[1] - center[1]), radius), (
                "The arc bends around the hook's pin"
            )

    @pytest.mark.slow
    def test_t_concreto2_hooks(self, t_concreto2: Pavement) -> None:
        hooks = 0
        for beam in detailings(t_concreto2):
            for run in beam.bars:
                count = (run.left_hook is not None) + (run.right_hook is not None)
                if not count:
                    continue
                hooks += count
                points, bulges = bar_path(run)
                left, right = hook_path(run, True), hook_path(run, False)
                if left is not None:
                    assert points[0] == left[2], f"{run.mark}: left tip"
                if right is not None:
                    assert points[-1] == right[2], f"{run.mark}: right tip"
                for path in (left, right):
                    if path is None:
                        continue
                    center = (path[0][0], path[1][1])
                    radius = abs(path[0][0] - path[1][0])
                    assert any(
                        close(hypot(m[0] - center[0], m[1] - center[1]), radius)
                        for m in _arc_middle(points, bulges)
                    ), f"{run.mark}: arc around the pin"
                difference = abs(_path_length(points, bulges) - run.total_length)
                assert difference < count, (
                    f"{run.mark}: drawn {difference:.2f} cm off the cut length"
                )
        assert hooks == 68, (
            "t_concreto2 has 68 hooks (66 in ED §9, before the span bars were "
            "carried to the supports; 72 before the support moments were rounded, "
            "NBR 6118 14.6.3; 70 before the wall load discounted the beam height; "
            "69 before the bars were staggered by layer; 68 after that; 69 again "
            "once φ22 and φ40 left the available sizes, patch 27; 68 once the span "
            "bars ran up to the end pillar's outer face, patch 30)"
        )


class TestOverlaps:
    """End-to-end overlaps of a layer, read from the geometry."""

    def test_bottom_laps(self, v5: DetailingBeam) -> None:
        pairs = [(a.mark, b.mark, s, e) for a, b, s, e in overlap_pairs(v5, True)]
        assert pairs == [("N10", "N12", 415, 445), ("N12", "N13", 845, 875)], (
            "Two 30 cm laps on the bottom face"
        )

    def test_top_laps_include_construction(self, v5: DetailingBeam) -> None:
        pairs = [(a.mark, b.mark) for a, b, _, _ in overlap_pairs(v5, False)]
        assert pairs == [
            ("N1", "N2"),
            ("N2", "N3"),
            ("N3", "N5"),
            ("N5", "N6"),
            ("N6", "N7"),
            ("N7", "N8"),
        ], "Construction bars lap with their neighbors; N4 is alone in layer 1"


class TestSectionPositions:
    """One cut per span, moved out of the laps."""

    def test_v5(self, v5: DetailingBeam) -> None:
        assert section_positions(v5, DrawingConfig()) == [215.0, 645.0, 1030.0], (
            "The spans' centers are all free"
        )

    def test_shifted_out_of_lap(self, v5: DetailingBeam) -> None:
        beam = _with_bar(v5, "N12", start=200.0)  # lap from 200 to 445
        assert section_positions(beam, DrawingConfig())[0] == 199.0, (
            "The first free point, searching both ways from 215"
        )

    def test_no_free_point_keeps_center(self, v5: DetailingBeam) -> None:
        beam = _with_bar(v5, "N12", start=0.0)  # lap over the whole first span
        assert section_positions(beam, DrawingConfig())[0] == 215.0, "Center kept"


class TestSection:
    """Bars and clamps crossing a cross section."""

    def test_section_layers(self, v5: DetailingBeam) -> None:
        layers = section_layers(v5, 215.0, True)
        assert {k: [b.mark for b in v] for k, v in layers.items()} == {
            0: ["N10"],
            1: ["N11"],
        }, "N10 in layer 0 and N11 in layer 1 at the first cut"

    def test_row_offsets(self, v5: DetailingBeam) -> None:
        row = arrange_row(section_layers(v5, 215.0, True)[0])
        assert close(row_offsets(row, 14.0 - 2 * 0.5), (-6.0, 6.0)), (
            "The outer bars touch the stirrup's inner faces"
        )

    def test_arrange_row_largest_outside(self, v5: DetailingBeam) -> None:
        big = replace(bar(v5, "N3"), quantity=2)
        small = replace(bar(v5, "N4"), quantity=1, layer_index=0)
        row = arrange_row([small, big])
        assert [b.diameter_mm for b in row] == [12.5, 10, 12.5], "Symmetric order"

    def test_clamp_rows(self, v5: DetailingBeam) -> None:
        rows = clamp_rows_y(v5, v5.clamps[0])
        assert close(rows, (6.315, 8.945)), (
            "Past N13 (y 3.5, φ10) with a 2 cm gap, then one φ6.3 row every 2.63 cm"
        )
