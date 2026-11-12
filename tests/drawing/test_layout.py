"""Tests for the elevation in src/drawing/layout.py."""

from dataclasses import replace

import pytest

from src.detailing.detailing_beam import DetailingBeam
from src.drawing.config import DrawingConfig
from src.drawing.geometry import lowest_hook_point
from src.drawing.layers import CUT, DIMENSION, LAYERS, PILLAR, STIRRUP, TEXT
from src.drawing.layout import (
    beam_content,
    pillar_bottom,
)
from src.drawing.primitives import Drawing, Line, Polyline, Text
from src.pavement_elements.pavement import Pavement
from tests.drawing.helpers import close, detailings

CONFIG = DrawingConfig()


def _lines(drawing: Drawing, layer: str) -> list[Line]:
    return [
        item for item in drawing.items if isinstance(item, Line) and item.layer == layer
    ]


def _texts(drawing: Drawing, layer: str) -> list[str]:
    return [
        item.text
        for item in drawing.items
        if isinstance(item, Text) and item.layer == layer
    ]


class TestPillarExtent:
    """The pillars go down far enough for the lowest hook leg (D2)."""

    def test_v5(self, v5: DetailingBeam) -> None:
        assert pillar_bottom(v5, CONFIG) == -30.0, "N8's leg reaches −20, plus 10 cm"
        drawing = beam_content(v5, CONFIG, tables=False)
        faces = [
            line for line in _lines(drawing, PILLAR) if line.start[0] == line.end[0]
        ]
        assert len(faces) == 2 * len(v5.supports), "Two faces per pillar"
        assert {line.start[1] for line in faces} == {-30.0}, (
            "Same bottom for all pillars"
        )
        assert {line.end[1] for line in faces} == {70.0}, "h + 20 cm above"

    def test_no_leg_below(self, v5: DetailingBeam) -> None:
        beam = replace(v5, bars=[bar for bar in v5.bars if bar.mark != "N8"])
        assert pillar_bottom(beam, CONFIG) == -20.0, "The minimum stretch"

    def test_break_lines(self, v5: DetailingBeam) -> None:
        drawing = beam_content(v5, CONFIG, tables=False)
        breaks = [
            item
            for item in drawing.items
            if isinstance(item, Polyline) and item.layer == PILLAR
        ]
        assert len(breaks) == 2 * len(v5.supports), "A break line on each end"
        assert all(len(item.points) == 6 for item in breaks), "Six points each"

    def test_pillar_names(self, v5: DetailingBeam) -> None:
        names = _texts(beam_content(v5, CONFIG, tables=False), TEXT)
        assert {"P10", "P11", "P12", "P13"} <= set(names), "Every pillar is named"

    @pytest.mark.slow
    def test_t_concreto2(self, t_concreto2: Pavement) -> None:
        bottoms: list[float] = []
        for beam in detailings(t_concreto2):
            bottom = pillar_bottom(beam, CONFIG)
            assert bottom == min(-20.0, lowest_hook_point(beam) - 10.0), (
                f"{beam.beam_id}: 10 cm under the lowest leg, 20 cm at least"
            )
            bottoms.append(bottom)
        assert min(bottoms) < -50.0, "V6's frame-node leg goes about 41 cm down"


class TestElevation:
    """Beam faces, dimension rows and cut marks."""

    def test_no_stirrup_ticks(self, v5: DetailingBeam) -> None:
        stirrup_lines = _lines(beam_content(v5, CONFIG, tables=False), STIRRUP)
        assert not [
            line
            for line in stirrup_lines
            if close(line.start[0], line.end[0]) and line.start[1] < v5.height + 1
        ], "No stirrup is drawn on the elevation (D3)"
        dimension_lines = [
            line for line in stirrup_lines if line.start[1] == line.end[1]
        ]
        zones = sum(len(span.zones) for span in v5.stirrups)
        assert len(dimension_lines) == zones, "One zone dimension per stirrup zone"

    def test_zone_texts(self, v5: DetailingBeam) -> None:
        texts = _texts(beam_content(v5, CONFIG, tables=False), STIRRUP)
        assert texts == ["N9 c/17", "26 φ5", "N9 c/17", "26 φ5", "N9 c/12", "28 φ5"], (
            "Spacing over the line, count under it"
        )

    def test_span_and_axis_dimensions(self, v5: DetailingBeam) -> None:
        texts = _texts(beam_content(v5, CONFIG, tables=False), DIMENSION)
        assert texts[:6] == ["411", "411", "321", "430", "430", "340"], (
            "Clear spans, then distances between axes"
        )

    def test_faces_only_along_clear_spans(self, v5: DetailingBeam) -> None:
        faces = _lines(beam_content(v5, CONFIG, tables=False), "VIGA-FORMA")
        assert len(faces) == 2 * len(v5.clear_spans), "Top and bottom face per span"
        assert (faces[0].start[0], faces[0].end[0]) == (9.5, 420.5), "Face to face"

    def test_cut_marks(self, v5: DetailingBeam) -> None:
        drawing = beam_content(v5, CONFIG, tables=False)
        assert _texts(drawing, CUT) == ["A", "A", "B", "B", "C", "C"], (
            "Each letter above and below the beam"
        )
        ticks = [line for line in _lines(drawing, CUT) if line.start[0] == line.end[0]]
        assert sorted({line.start[0] for line in ticks}) == [215.0, 645.0, 1030.0], (
            "One cut per span"
        )

    def test_title(self, v5: DetailingBeam) -> None:
        texts = _texts(beam_content(v5, CONFIG, tables=False), TEXT)
        index = texts.index("V5")
        assert texts[index + 1] == "19/50", "Beam name and b/h"

    def test_layers_known(self, v5: DetailingBeam) -> None:
        drawing = beam_content(v5, CONFIG, tables=False)
        assert set(drawing.layers()) <= set(LAYERS), (
            "Every primitive uses a table layer"
        )


class TestHover:
    """Bars and clamps carry their tooltip."""

    def test_bar_with_laps(self, v5: DetailingBeam) -> None:
        drawing = beam_content(v5, CONFIG, tables=False)
        metas = [
            item.meta
            for item in drawing.items
            if isinstance(item, Polyline) and item.meta is not None
        ]
        n12 = next(meta for meta in metas if meta.title.startswith("N12 "))
        assert n12.title == "N12 · 2 φ10 CA-50", "Mark, count, diameter and steel"
        assert n12.lines == (
            "C = 460 cm (reta 460, ganchos 0 + 0)",
            "x = 415 → 875 · inferior · camada 0",
            "traspasse 30 com N10 e N13",
        ), "Cut length, extent and laps"

    def test_clamp(self, v5: DetailingBeam) -> None:
        drawing = beam_content(v5, CONFIG, tables=False)
        clamps = [item for item in _lines(drawing, "ARM-GRAMPO")]
        assert len(clamps) == 2, "One line per clamp row"
        assert clamps[0].meta is not None
        assert clamps[0].meta.lines[1] == "perna 40 · largura 13", "Leg and width"
