"""Tests for src/drawing/sections.py: cross sections and shapes."""

import pytest

from src.detailing.detailing_beam import DetailingBeam
from src.drawing.config import MM_PER_CM, DrawingConfig
from src.drawing.geometry import arrange_row, row_offsets, section_layers
from src.drawing.layers import SECTION_BAR, STIRRUP, TEXT
from src.drawing.primitives import Circle, Drawing, Line, Polyline, Text
from src.drawing.sections import (
    draw_section,
    section_cuts,
    section_points,
    sections_block,
    shape_pieces,
)
from src.pavement_elements.pavement import Pavement
from tests.drawing.helpers import close, detailings

CONFIG = DrawingConfig()


def _circles(drawing: Drawing) -> list[Circle]:
    return [
        i for i in drawing.items if isinstance(i, Circle) and i.layer == SECTION_BAR
    ]


def _texts(drawing: Drawing, layer: str = TEXT) -> list[Text]:
    return [i for i in drawing.items if isinstance(i, Text) and i.layer == layer]


def _expected_circles(beam: DetailingBeam, x: float) -> int:
    """Return how many bars and clamp legs cross a section"""
    bars = sum(
        run.quantity
        for is_bottom in (False, True)
        for runs in section_layers(beam, x, is_bottom).values()
        for run in runs
    )
    legs = 0
    for clamps in beam.clamps:
        tip = clamps.position + (
            clamps.leg_length if clamps.left else -clamps.leg_length
        )
        if min(clamps.position, tip) <= x <= max(clamps.position, tip):
            legs += 2 * clamps.quantity
    return bars + legs


def _check_section_bars(beam: DetailingBeam) -> None:
    """Assert spec §11 test_section_bars on every cut of a beam"""
    for letter, x in section_cuts(beam, CONFIG):
        stirrups = next(s for s in beam.stirrups if s.start <= x <= s.end)
        inner = stirrups.outer_width - 2 * stirrups.diameter_mm / MM_PER_CM
        expected: list[tuple[float, float]] = []
        for is_bottom in (False, True):
            for _, runs in sorted(section_layers(beam, x, is_bottom).items()):
                row = arrange_row(runs)
                expected += [
                    (u, bar.y)
                    for bar, u in zip(row, row_offsets(row, inner), strict=True)
                ]
        points = [(p.u, p.y) for p in section_points(beam, x) if p.source in beam.bars]
        assert points == expected, (
            f"{beam.beam_id} {letter}: bars as arrange_row places them"
        )
        drawing = draw_section(beam, x, letter, (0.0, 0.0), CONFIG)
        assert len(_circles(drawing)) == _expected_circles(beam, x), (
            f"{beam.beam_id} {letter}: one circle per bar and clamp leg"
        )
        labels = [
            t for t in _texts(drawing) if not t.text.startswith(("CORTE", "ESC."))
        ]
        top = CONFIG.section_magnification * beam.height
        assert all(t.position[1] <= top + 1e-9 for t in labels), (
            f"{beam.beam_id} {letter}: no label above the section, under the title"
        )


class TestSection:
    """One cross section (§6.7.2)."""

    def test_section_bars(self, v5: DetailingBeam) -> None:
        _check_section_bars(v5)

    def test_first_cut(self, v5: DetailingBeam) -> None:
        drawing = draw_section(v5, 215.0, "A", (0.0, 0.0), CONFIG)
        centers = sorted(c.center for c in _circles(drawing))
        assert close(
            [c for point in centers for c in point],
            [
                6.5,
                93.5,
                6.8,
                12.8,
                7.0,
                7.0,
                31.0,
                7.0,
                31.2,
                12.8,
                31.5,
                93.5,
            ],
        ), "Bars touching the stirrup's inner faces, magnified twice from the left face"
        labels = [t.text for t in _texts(drawing)]
        assert labels[:4] == ["2 N10 φ10", "2 N11 φ8", "N9 c/17", "2 N2 φ5"], (
            "One label per run and the stirrups', from the bottom up"
        )
        assert labels[4:] == ["CORTE A-A", "ESC. 1:25"], "Title and scale"

    def test_labels_spaced(self, v5: DetailingBeam) -> None:
        drawing = draw_section(v5, 215.0, "A", (0.0, 0.0), CONFIG)
        heights = [t.position[1] for t in _texts(drawing)][:4]
        pitch = 1.6 * CONFIG.paper(2.0)
        assert all(
            b - a >= pitch - 1e-9 for a, b in zip(heights, heights[1:], strict=False)
        ), "Labels pushed up to 1.6 text heights apart"

    def test_stirrup(self, v5: DetailingBeam) -> None:
        drawing = draw_section(v5, 215.0, "A", (0.0, 0.0), CONFIG)
        stirrup = next(
            i for i in drawing.items if isinstance(i, Polyline) and i.layer == STIRRUP
        )
        assert stirrup.closed, "A closed loop"
        assert close(stirrup.points[0], (2 * 2.75, 2 * 2.75)), (
            "Axis of the 14 × 45 stirrup: φ5/2 inside its outer corner"
        )
        hooks = [i for i in drawing.items if isinstance(i, Line) and i.layer == STIRRUP]
        assert len(hooks) == 2, "Two closing strokes"
        length = (
            (hooks[0].end[0] - hooks[0].start[0]) ** 2
            + (hooks[0].end[1] - hooks[0].start[1]) ** 2
        ) ** 0.5
        assert close(length, 2 * 5.0), "As long as the 135° hook tip, magnified"

    def test_clamp_legs(self, v5: DetailingBeam) -> None:
        points = section_points(v5, 1190.0)
        legs = [p for p in points if p.source is v5.clamps[0]]
        assert len(legs) == 4, "Two clamps, a leg in each inner corner"
        assert close(sorted({round(p.u, 6) for p in legs}), (-6.185, 6.185)), (
            "±(13 − 0.63)/2"
        )

    @pytest.mark.slow
    def test_laje_rebaixada(self, laje_rebaixada: Pavement) -> None:
        for beam in detailings(laje_rebaixada):
            _check_section_bars(beam)


class TestBlock:
    """Sections side by side and the shapes under them (§6.7.3, §6.8)."""

    def test_tops_aligned(self, v5: DetailingBeam) -> None:
        drawing = sections_block(v5, CONFIG).drawing
        outlines = [
            i
            for i in drawing.items
            if isinstance(i, Polyline) and i.layer == "VIGA-FORMA"
        ]
        assert len(outlines) == 3, "One section per span"
        assert {max(y for _, y in o.points) for o in outlines} == {50.0 + 95.0}, (
            "Tops at h + 19 mm of paper"
        )
        lefts = [min(x for x, _ in o.points) for o in outlines]
        assert close(lefts[0], v5.end + CONFIG.paper(19.0)), (
            "First section 15 + 4 mm of paper right of the beam"
        )
        assert lefts == sorted(lefts), "Left to right"

    def test_shapes(self, v5: DetailingBeam) -> None:
        texts = [t.text for piece in shape_pieces(v5, CONFIG) for t in _texts(piece)]
        assert texts == ["80 N9 φ5", "C=130", "2 N14 φ6,3", "C=93"], (
            "One stirrup shape with the quantity of all spans, one clamp shape"
        )

    def test_shapes_under_sections(self, v5: DetailingBeam) -> None:
        drawing = sections_block(v5, CONFIG).drawing
        title = next(t for t in _texts(drawing) if t.text == "FORMAS")
        sections_low = min(
            y
            for i in drawing.items
            if isinstance(i, Polyline) and i.layer == "VIGA-FORMA"
            for _, y in i.points
        )
        assert title.position[1] < sections_low - CONFIG.paper(18.0), (
            "18 mm under the sections"
        )
