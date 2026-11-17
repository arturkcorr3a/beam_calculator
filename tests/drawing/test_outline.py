"""Tests for the beam drawings without reinforcement (src/drawing/outline.py)."""

from src.detailing.detailing_beam import DetailingBeam
from src.drawing.config import DEFAULT_CONFIG
from src.drawing.formatting import fmt_len
from src.drawing.geometry import pillar_ids
from src.drawing.layers import BEAM_OUTLINE, CUT, DIMENSION, TEXT
from src.drawing.layout import (
    dimension_rows,
    geometry_dimension_rows,
    stirrup_zone_row,
)
from src.drawing.outline import build_beam_outline, build_beam_section
from src.drawing.primitives import Drawing, Polyline, Text
from src.drawing.sections import draw_plain_section
from src.pavement_elements.pavement import Pavement
from tests.drawing.helpers import close, detailings

_GEOMETRY_LAYERS = {"VIGA-FORMA", "VIGA-PILAR", "VIGA-EIXO", "COTA", "TEXTO"}


def _texts(drawing: Drawing, layer: str) -> list[str]:
    return [
        item.text
        for item in drawing.items
        if isinstance(item, Text) and item.layer == layer
    ]


class TestDimensionRows:
    """dimension_rows is the stirrup zones followed by the geometry rows"""

    def test_split_keeps_the_rows(self, v5: DetailingBeam) -> None:
        joined = (
            stirrup_zone_row(v5, DEFAULT_CONFIG).items
            + geometry_dimension_rows(v5, DEFAULT_CONFIG).items
        )
        assert dimension_rows(v5, DEFAULT_CONFIG).items == joined

    def test_geometry_rows_hold_no_stirrup_zone(self, v5: DetailingBeam) -> None:
        layers = {
            item.layer for item in geometry_dimension_rows(v5, DEFAULT_CONFIG).items
        }
        assert layers == {DIMENSION}


class TestOutline:
    """The elevation shows the geometry only"""

    def test_only_geometry_layers(self, v5: DetailingBeam) -> None:
        assert set(build_beam_outline(v5).layers()) <= _GEOMETRY_LAYERS, (
            "the outline should hold no reinforcement, cut marks or tables"
        )

    def test_holds_the_geometry_rows_and_title(self, v5: DetailingBeam) -> None:
        outline = build_beam_outline(v5).items
        for item in geometry_dimension_rows(v5, DEFAULT_CONFIG).items:
            assert item in outline, "every span and axis dimension should be drawn"
        texts = _texts(build_beam_outline(v5), TEXT)
        assert v5.beam_id in texts, "the beam's name should be drawn"
        assert f"{fmt_len(v5.width)}/{fmt_len(v5.height)}" in texts, (
            "b/h should be drawn"
        )

    def test_names_every_pillar(self, laje_rebaixada: Pavement) -> None:
        for beam in detailings(laje_rebaixada):
            texts = _texts(build_beam_outline(beam), TEXT)
            for name in pillar_ids(beam):
                assert name in texts, f"{beam.beam_id}: pillar {name} should be named"

    def test_no_cut_layer(self, laje_rebaixada: Pavement) -> None:
        for beam in detailings(laje_rebaixada):
            assert CUT not in build_beam_outline(beam).layers()


class TestPlainSection:
    """The section without reinforcement: outline, b and h, optional title"""

    def test_outline_and_dimensions(self, v5: DetailingBeam) -> None:
        drawing = build_beam_section(v5)
        m = DEFAULT_CONFIG.section_magnification
        outlines = [
            item
            for item in drawing.items
            if isinstance(item, Polyline) and item.layer == BEAM_OUTLINE
        ]
        assert len(outlines) == 1, "one section outline"
        xs = [x for x, _ in outlines[0].points]
        ys = [y for _, y in outlines[0].points]
        assert close(max(xs) - min(xs), m * v5.width), "outline width (cm on sheet)"
        assert close(max(ys) - min(ys), m * v5.height), "outline height (cm on sheet)"
        assert sorted(_texts(drawing, DIMENSION)) == sorted(
            [fmt_len(v5.width), fmt_len(v5.height)]
        ), "b and h are dimensioned"

    def test_no_title_by_default(self, v5: DetailingBeam) -> None:
        assert _texts(build_beam_section(v5), TEXT) == []

    def test_title_when_given(self) -> None:
        drawing = draw_plain_section(20.0, 50.0, (0.0, 0.0), DEFAULT_CONFIG, "V1")
        assert _texts(drawing, TEXT) == ["V1"]
