"""Tests for src/drawing/primitives.py and src/drawing/layers.py."""

from math import hypot, tan

import pytest

from src.drawing.layers import LAYERS, LINETYPE_PATTERNS_MM, layer_style
from src.drawing.primitives import (
    Circle,
    Drawing,
    HAlign,
    HoverInfo,
    Line,
    Polyline,
    Text,
    VAlign,
    arc_center,
    arc_points,
)
from tests.drawing.helpers import close

_QUARTER_BULGE = tan(3.141592653589793 / 8)


class TestArcs:
    """A bulge is the tangent of a quarter of the central angle, positive counterclockwise."""

    def test_quarter_circle_center(self) -> None:
        center, radius = arc_center((1.0, 0.0), (0.0, 1.0), _QUARTER_BULGE)
        assert close(center, (0.0, 0.0)), "CCW quarter from (1,0) to (0,1)"
        assert close(radius, 1.0), "Unit radius"

    def test_clockwise_center(self) -> None:
        center, _ = arc_center((1.0, 0.0), (0.0, 1.0), -_QUARTER_BULGE)
        assert close(center, (1.0, 1.0)), "A negative bulge turns clockwise"

    def test_points_on_arc(self) -> None:
        points = arc_points((1.0, 0.0), (0.0, 1.0), _QUARTER_BULGE, 8)
        assert len(points) == 9, "8 pieces per quarter circle"
        assert points[-1] == (0.0, 1.0), "The end is kept exactly"
        for x, y in points:
            assert close(hypot(x, y), 1.0), "Every point lies on the arc"

    def test_straight_segment(self) -> None:
        assert arc_points((0.0, 0.0), (5.0, 0.0), 0.0, 8) == [(0.0, 0.0), (5.0, 0.0)], (
            "A straight segment keeps only its ends"
        )

    def test_zero_bulge_has_no_center(self) -> None:
        with pytest.raises(ValueError, match="bulge"):
            arc_center((0.0, 0.0), (1.0, 0.0), 0.0)


class TestPolyline:
    """A polyline has one bulge per point."""

    def test_bulge_count_checked(self) -> None:
        with pytest.raises(ValueError, match="one bulge per point"):
            Polyline(((0.0, 0.0), (1.0, 0.0)), (0.0,), "COTA")

    def test_closed_segments(self) -> None:
        square = Polyline(
            ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)), (0.0,) * 4, "COTA", True
        )
        assert len(square.segments()) == 4, "A closed polyline joins the last point"


class TestDrawing:
    """Bounds and translation of a drawing."""

    def test_bounds_with_arc_and_circle(self) -> None:
        drawing = Drawing()
        drawing.add(
            Line((0.0, 0.0), (10.0, 0.0), "COTA"),
            Polyline(((10.0, 0.0), (10.0, 10.0)), (1.0, 0.0), "COTA"),
            Circle((0.0, 0.0), 2.0, "ARM-SECAO", filled=True),
        )
        x_min, y_min, x_max, y_max = drawing.bounds()
        assert close((x_min, y_min), (-2.0, -2.0)), "The circle sets the minimum"
        assert close(x_max, 15.0), "The half circle bulges out to x = 15"
        assert close(y_max, 10.0), "The arc ends at y = 10"

    def test_text_box(self) -> None:
        text = Text((0.0, 0.0), "AB", 2.0, "TEXTO", HAlign.CENTER, VAlign.TOP)
        drawing = Drawing([text])
        assert close(drawing.bounds(), (-1.8, -2.0, 1.8, 0.0)), (
            "Width 2 × 0.9 × 2, centered, hanging from the anchor"
        )

    def test_rotated_text_box(self) -> None:
        text = Text((0.0, 0.0), "AB", 2.0, "TEXTO", rotation=90.0)
        assert close(Drawing([text]).bounds(), (-2.0, 0.0, 0.0, 3.6)), (
            "A text turned 90° runs up, with its top to the left"
        )

    def test_translated_keeps_meta(self) -> None:
        meta = HoverInfo("N1", ("C = 100",))
        drawing = Drawing([Line((0.0, 0.0), (1.0, 0.0), "ARM-PRINCIPAL", meta)])
        moved = drawing.translated(5.0, -2.0)
        item = moved.items[0]
        assert isinstance(item, Line)
        assert (item.start, item.end) == ((5.0, -2.0), (6.0, -2.0)), "Moved by (5, −2)"
        assert item.meta is meta, "The tooltip data travels with the primitive"
        assert drawing.items[0] != item, "The original is left alone"

    def test_empty_bounds(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            Drawing().bounds()

    def test_layers_in_order(self) -> None:
        drawing = Drawing(
            [
                Line((0.0, 0.0), (1.0, 0.0), "COTA"),
                Line((0.0, 0.0), (1.0, 0.0), "TEXTO"),
                Line((0.0, 0.0), (1.0, 0.0), "COTA"),
            ]
        )
        assert drawing.layers() == ["COTA", "TEXTO"], "Each layer once, first use first"


class TestLayers:
    """The layer table of spec §3."""

    def test_layer_count(self) -> None:
        assert len(LAYERS) == 21, "16 drawing layers plus 5 of the frame and the block"

    def test_linetypes_defined(self) -> None:
        for style in LAYERS.values():
            assert (
                style.linetype == "CONTINUOUS" or style.linetype in LINETYPE_PATTERNS_MM
            ), f"{style.name} uses an undefined linetype"

    def test_main_bar_style(self) -> None:
        style = layer_style("ARM-PRINCIPAL")
        assert (style.aci, style.lineweight_mm, style.screen_color) == (
            1,
            0.5,
            "#c62828",
        ), "Main bars are red, 0.50 mm"

    def test_unknown_layer(self) -> None:
        with pytest.raises(KeyError, match="NOPE"):
            layer_style("NOPE")
