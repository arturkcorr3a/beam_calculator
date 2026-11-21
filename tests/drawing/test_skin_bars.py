"""Skin bars on the detailing sheet: elevation, bar rows, sections, layer and legend."""

import pytest

from src.detailing.detailed_skin_bars import DetailedSkinBars
from src.detailing.detailing_beam import DetailingBeam
from src.drawing.api import DrawingError, check_detailing
from src.drawing.bar_rows import bar_rows
from src.drawing.config import MM_PER_CM, DrawingConfig
from src.drawing.formatting import SKIN_MARK
from src.drawing.layers import LAYERS, SKIN_BAR
from src.drawing.layout import bars, pillar_bottom
from src.drawing.primitives import Drawing, Line, Text
from src.drawing.schedule_layout import LEGEND_LAYERS
from src.drawing.sections import section_labels, section_points
from src.properties.steel import Steel
from tests.helpers import assert_approx

CONFIG = DrawingConfig()
_START = 9.5  # cm, inner face of P10
_END = 420.5  # cm, inner face of P11


@pytest.fixture
def skinned(v5: DetailingBeam) -> DetailingBeam:
    """V5 with 2 rows of φ6.3 skin bars, at 20 and 30 cm, on its first span"""
    v5.skin_bars = [
        DetailedSkinBars(
            start_pillar_id="P10",
            end_pillar_id="P11",
            diameter_mm=6.3,
            steel=Steel.CA50,
            heights=(20.0, 30.0),
            start=_START,
            end=_END,
            mark="N20",
        )
    ]
    return v5


def _skin_lines(drawing: Drawing) -> list[Line]:
    """Return the lines on the skin layer"""
    return [
        item
        for item in drawing.items
        if isinstance(item, Line) and item.layer == SKIN_BAR
    ]


class TestLayer:
    """The skin bars have a layer of their own, in the legend."""

    def test_layer_and_legend(self) -> None:
        assert LAYERS[SKIN_BAR].description == "Armadura de pele", "layer table"
        assert SKIN_BAR in LEGEND_LAYERS, "shown in the legend"

    def test_paper_mark(self) -> None:
        assert SKIN_MARK == "(PELE)", "note under the skin bars' label"


class TestElevation:
    """Each row of skin bars is a line at its height over its span."""

    def test_one_line_per_row(self, skinned: DetailingBeam) -> None:
        lines = _skin_lines(bars(skinned))
        assert [line.start[1] for line in lines] == [20.0, 30.0], "row heights (cm)"
        for line in lines:
            assert (line.start[0], line.end[0]) == (_START, _END), "span extent (cm)"
            assert line.meta is not None, "hover with mark and extent"
            assert line.meta.title.startswith("N20 · 4"), "mark and bar count"

    def test_no_skin_no_lines(self, v5: DetailingBeam) -> None:
        assert _skin_lines(bars(v5)) == [], "a beam without skin bars"


class TestBarRows:
    """The skin bars get their own block, under the bottom face."""

    def test_block_under_bottom(self, skinned: DetailingBeam) -> None:
        rows = bar_rows(skinned, pillar_bottom(skinned, CONFIG), CONFIG)
        assert len(rows.skin) == 1, "one row item per skin bar set"
        lowest_bottom = min(item.y for item in rows.bottom)
        assert rows.skin[0].y < lowest_bottom, "skin rows under the bottom face"
        assert rows.lowest <= rows.skin[0].y, "the rows reach the skin block"

    def test_label_and_mark(self, skinned: DetailingBeam) -> None:
        rows = bar_rows(skinned, pillar_bottom(skinned, CONFIG), CONFIG)
        texts = [
            item.text for item in rows.skin[0].drawing.items if isinstance(item, Text)
        ]
        assert any("N20" in text for text in texts), "labelled with the mark"
        assert SKIN_MARK in texts, "noted (PELE)"
        legends = [item.text for item in rows.drawing.items if isinstance(item, Text)]
        assert "PELE" in legends, "block named PELE"

    def test_no_skin_no_block(self, v5: DetailingBeam) -> None:
        rows = bar_rows(v5, pillar_bottom(v5, CONFIG), CONFIG)
        assert rows.skin == (), "no skin block without skin bars"


class TestSections:
    """A cut through the span shows a skin bar against each side of the stirrup, per row."""

    def test_points_on_both_sides(self, skinned: DetailingBeam) -> None:
        points = [
            point
            for point in section_points(skinned, 200.0)
            if isinstance(point.source, DetailedSkinBars)
        ]
        stirrups = skinned.stirrups[0]
        inner = stirrups.outer_width - 2 * stirrups.diameter_mm / MM_PER_CM
        offset = (inner - 0.63) / 2
        assert len(points) == 4, "2 rows x 2 sides"
        assert sorted({p.y for p in points}) == [20.0, 30.0], "row heights (cm)"
        for point in points:
            assert_approx(abs(point.u), offset, "against the stirrup's side (cm)")

    def test_label(self, skinned: DetailingBeam) -> None:
        assert "4 N20 φ6,3" in section_labels(skinned, 200.0, CONFIG), (
            "one label for the set"
        )

    def test_other_span_has_none(self, skinned: DetailingBeam) -> None:
        points = section_points(skinned, 600.0)
        assert not any(isinstance(p.source, DetailedSkinBars) for p in points), (
            "skin bars stay in their span"
        )


class TestCheckDetailing:
    def test_unmarked_skin_raises(self, skinned: DetailingBeam) -> None:
        skinned.skin_bars[0].mark = None
        with pytest.raises(DrawingError):
            check_detailing(skinned)
