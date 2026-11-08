"""Tests for src/drawing/render_dxf.py and src/drawing/render_mpl.py on hand-made drawings."""

# ezdxf leaves some parameters unannotated, so its functions are partially unknown
# pyright: reportUnknownMemberType=false

from collections.abc import Iterator
from pathlib import Path
from typing import cast

import matplotlib.pyplot as plt
import pytest
from ezdxf.entities.hatch import Hatch
from ezdxf.entities.layer import Layer
from ezdxf.entities.ltype import Linetype
from ezdxf.entities.lwpolyline import LWPolyline
from ezdxf.entities.text import Text as DxfText
from ezdxf.lldxf.types import DXFTag
from matplotlib.collections import LineCollection, PatchCollection

from src.drawing.config import DrawingConfig
from src.drawing.geometry import QUARTER_BULGE
from src.drawing.layers import LAYERS
from src.drawing.primitives import (
    Circle,
    Drawing,
    HAlign,
    Line,
    Polyline,
    Text,
    VAlign,
)
from src.drawing.render_dxf import TEXT_STYLE, write_dxf
from src.drawing.render_mpl import format_coord, make_figure, text_outline
from tests.drawing.helpers import close, read_dxf


def _sample() -> Drawing:
    """A drawing with every kind of primitive"""
    return Drawing(
        [
            Line((0.0, 0.0), (100.0, 0.0), "VIGA-FORMA"),
            Line((50.0, -20.0), (50.0, 70.0), "VIGA-EIXO"),
            Polyline(
                ((0.0, 30.0), (0.0, 10.0), (20.0, 5.0), (90.0, 5.0)),
                (0.0, QUARTER_BULGE, 0.0, 0.0),
                "ARM-PRINCIPAL",
            ),
            Polyline(
                ((10.0, 10.0), (30.0, 10.0), (30.0, 40.0), (10.0, 40.0)),
                (0.0,) * 4,
                "ARM-ESTRIBO",
                closed=True,
            ),
            Circle((15.0, 15.0), 1.0, "ARM-SECAO", filled=True),
            Circle((25.0, 15.0), 1.0, "COTA"),
            Text((50.0, 80.0), "2 N3 φ12,5 C=170", 12.5, "TEXTO", HAlign.CENTER),
            Text((-10.0, 25.0), "50", 10.0, "COTA", HAlign.CENTER, VAlign.MIDDLE, 90.0),
            Text((100.0, -5.0), "A", 15.0, "CORTE", HAlign.RIGHT, VAlign.TOP),
        ]
    )


@pytest.fixture
def figures() -> Iterator[None]:
    """Close the figures a test opens"""
    yield
    plt.close("all")


class TestDxf:
    """The DXF has the sheet's units, layers, linetypes and one entity per primitive."""

    @pytest.fixture
    def dxf_path(self, tmp_path: Path) -> Path:
        return write_dxf(_sample(), tmp_path / "out" / "sample.dxf")

    def test_audit_and_units(self, dxf_path: Path) -> None:
        doc = read_dxf(dxf_path)
        assert not doc.audit().has_errors, "The written file passes the audit"
        assert doc.header["$INSUNITS"] == 5, "Units in cm"
        assert doc.header["$MEASUREMENT"] == 1, "Metric"

    def test_layers(self, dxf_path: Path) -> None:
        doc = read_dxf(dxf_path)
        for style in LAYERS.values():
            layer = doc.layers.get(style.name)
            assert isinstance(layer, Layer), f"Layer {style.name} exists"
            assert layer.color == style.aci, f"{style.name}: ACI color"
            assert layer.dxf.linetype.upper() == style.linetype, (
                f"{style.name}: linetype"
            )
            assert layer.dxf.lineweight == round(style.lineweight_mm * 100), (
                f"{style.name}: line weight in 1/100 mm"
            )

    def test_linetype_on_paper(self, dxf_path: Path) -> None:
        linetype = read_dxf(dxf_path).linetypes.get("EIXO")
        assert isinstance(linetype, Linetype)
        tags = cast(list[DXFTag], linetype.pattern_tags.tags)
        pattern = [float(str(t.value)) for t in tags if t.code in (40, 49)]
        assert close(pattern, (40.0, 30.0, -5.0, 0.0, -5.0)), (
            "6, 1, 0, 1 mm of paper at 1:50 are 30, 5, 0, 5 cm"
        )

    def test_entities(self, dxf_path: Path) -> None:
        msp = read_dxf(dxf_path).modelspace()
        kinds = sorted(entity.dxftype() for entity in msp)
        assert kinds == sorted(
            ["LINE"] * 2
            + ["LWPOLYLINE"] * 2
            + ["CIRCLE"] * 2
            + ["HATCH"]
            + ["TEXT"] * 3
        ), "One entity per primitive, plus the hatch of the filled circle"
        for entity in msp:
            assert entity.dxf.color == 256, "Every entity is BYLAYER"

    def test_bulge_and_closed(self, dxf_path: Path) -> None:
        polylines = [
            e for e in read_dxf(dxf_path).modelspace() if isinstance(e, LWPolyline)
        ]
        bars = [p for p in polylines if p.dxf.layer == "ARM-PRINCIPAL"]
        stirrups = [p for p in polylines if p.dxf.layer == "ARM-ESTRIBO"]
        assert close(
            [b for *_, b in bars[0].get_points("xyb")], (0.0, QUARTER_BULGE, 0.0, 0.0)
        ), "The bulges are kept"
        assert stirrups[0].closed, "The stirrup is closed"

    def test_filled_circle(self, dxf_path: Path) -> None:
        hatch = next(e for e in read_dxf(dxf_path).modelspace() if isinstance(e, Hatch))
        assert hatch.dxf.solid_fill == 1, "Solid fill"
        assert hatch.dxf.layer == "ARM-SECAO", "On the circle's layer"

    def test_texts(self, dxf_path: Path) -> None:
        texts = {
            e.dxf.text: e
            for e in read_dxf(dxf_path).modelspace()
            if isinstance(e, DxfText)
        }
        label = texts["2 N3 φ12,5 C=170"]
        assert label.dxf.style == TEXT_STYLE, "Arial style"
        assert close(label.dxf.height, 12.5), "Cap height in cm"
        assert close(texts["50"].dxf.rotation, 90.0), "Rotation kept"
        assert texts["A"].get_align_enum().name == "TOP_RIGHT", "Alignment kept"


class TestMpl:
    """The figure draws one collection per layer and kind, with a legend."""

    @pytest.mark.usefixtures("figures")
    def test_collections_and_legend(self) -> None:
        drawing = _sample()
        figure = make_figure(drawing, DrawingConfig())
        ax = figure.axes[0]
        line_layers = {
            c.get_label() for c in ax.collections if isinstance(c, LineCollection)
        }
        assert line_layers == {
            "VIGA-FORMA",
            "VIGA-EIXO",
            "ARM-PRINCIPAL",
            "ARM-ESTRIBO",
        }, "One line collection per layer"
        patches = [c for c in ax.collections if isinstance(c, PatchCollection)]
        assert len(patches) == 2 + 3, "Circles of 2 layers and texts of 3 layers"
        legend = ax.get_legend()
        assert legend is not None
        assert len(legend.get_texts()) == len(drawing.layers()), "One entry per layer"

    @pytest.mark.usefixtures("figures")
    def test_view_and_save(self, tmp_path: Path) -> None:
        figure = make_figure(_sample(), DrawingConfig())
        ax = figure.axes[0]
        x_min, x_max = ax.get_xlim()
        assert x_min <= -10.0 - 50.0 and x_max >= 100.0 + 50.0, (
            "Bounds plus 10 mm of paper"
        )
        path = tmp_path / "sample.png"
        figure.savefig(path)
        assert path.stat().st_size > 0, "The figure renders to PNG"

    def test_format_coord(self) -> None:
        assert format_coord(1.25, -3.0) == "x = 1,2 cm   y = -3,0 cm", "Decimal comma"

    def test_text_cap_height(self) -> None:
        outline = text_outline(Text((0.0, 0.0), "H", 10.0, "TEXTO"))
        extents = outline.get_extents()
        assert abs(extents.height - 10.0) < 0.5, "The cap height is the text height"
        assert abs(extents.y0) < 1e-6, "Baseline at the anchor"

    def test_text_centered_and_rotated(self) -> None:
        item = Text(
            (50.0, 20.0), "ABC", 10.0, "TEXTO", HAlign.CENTER, VAlign.MIDDLE, 90.0
        )
        extents = text_outline(item).get_extents()
        center = ((extents.x0 + extents.x1) / 2, (extents.y0 + extents.y1) / 2)
        assert close(center, (50.0, 20.0), tol=0.5), "Centered on the anchor"
        assert extents.height > extents.width, "Turned 90°, the text runs upward"
