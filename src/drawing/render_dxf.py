"""DXF renderer: writes a Drawing to a model-space DXF file in cm, with the sheet's layers"""

# ezdxf leaves its dxfattribs parameters unannotated, so its methods are partially unknown
# pyright: reportUnknownMemberType=false

from pathlib import Path

from ezdxf import units, zoom
from ezdxf.document import Drawing as DxfDocument
from ezdxf.enums import TextEntityAlignment
from ezdxf.filemanagement import new
from ezdxf.layouts.layout import Modelspace

from src.drawing.config import DEFAULT_CONFIG, DrawingConfig
from src.drawing.layers import (
    CONTINUOUS,
    LAYERS,
    LINETYPE_DESCRIPTIONS,
    LINETYPE_PATTERNS_MM,
)
from src.drawing.primitives import (
    Circle,
    Drawing,
    DrawingItem,
    HAlign,
    Image,
    Line,
    Polyline,
    Text,
    VAlign,
)

TEXT_STYLE = "ARIAL"
_TEXT_FONT = "arial.ttf"
_DXF_VERSION = "R2018"
_BYLAYER = 256
_LINEWEIGHT_PER_MM = 100  # DXF line weights are in 1/100 mm
_INSUNITS_CM = 5
_MEASUREMENT_METRIC = 1

_ALIGNMENTS: dict[tuple[VAlign, HAlign], TextEntityAlignment] = {
    (VAlign.BASELINE, HAlign.LEFT): TextEntityAlignment.LEFT,
    (VAlign.BASELINE, HAlign.CENTER): TextEntityAlignment.CENTER,
    (VAlign.BASELINE, HAlign.RIGHT): TextEntityAlignment.RIGHT,
    (VAlign.MIDDLE, HAlign.LEFT): TextEntityAlignment.MIDDLE_LEFT,
    (VAlign.MIDDLE, HAlign.CENTER): TextEntityAlignment.MIDDLE_CENTER,
    (VAlign.MIDDLE, HAlign.RIGHT): TextEntityAlignment.MIDDLE_RIGHT,
    (VAlign.TOP, HAlign.LEFT): TextEntityAlignment.TOP_LEFT,
    (VAlign.TOP, HAlign.CENTER): TextEntityAlignment.TOP_CENTER,
    (VAlign.TOP, HAlign.RIGHT): TextEntityAlignment.TOP_RIGHT,
}


class DxfAuditError(RuntimeError):
    """The DXF document failed ezdxf's audit"""


def new_document(config: DrawingConfig = DEFAULT_CONFIG) -> DxfDocument:
    """Return an empty DXF document in cm, with the text style, linetypes and layers of the sheet

    The linetype patterns are converted from paper to model lengths at the sheet's scale, so ``$LTSCALE`` stays at 1.
    """
    doc = new(_DXF_VERSION)
    doc.units = units.CM
    doc.header["$INSUNITS"] = _INSUNITS_CM
    doc.header["$MEASUREMENT"] = _MEASUREMENT_METRIC
    doc.header["$LWDISPLAY"] = 1
    doc.styles.add(TEXT_STYLE, font=_TEXT_FONT)
    for name, pattern_mm in LINETYPE_PATTERNS_MM.items():
        pattern = [config.paper(length) for length in pattern_mm]
        doc.linetypes.add(
            name,
            pattern=[sum(abs(length) for length in pattern), *pattern],
            description=LINETYPE_DESCRIPTIONS[name],
        )
    for style in LAYERS.values():
        doc.layers.add(
            style.name,
            color=style.aci,
            linetype="Continuous" if style.linetype == CONTINUOUS else style.linetype,
            lineweight=round(style.lineweight_mm * _LINEWEIGHT_PER_MM),
        )
    return doc


def add_item(msp: Modelspace, item: DrawingItem) -> None:
    """Add one primitive to the model space; color, linetype and weight come from its layer"""
    attribs = {"layer": item.layer}
    match item:
        case Line():
            msp.add_line(item.start, item.end, dxfattribs=attribs)
        case Polyline():
            msp.add_lwpolyline(
                [
                    (x, y, bulge)
                    for (x, y), bulge in zip(item.points, item.bulges, strict=True)
                ],
                format="xyb",
                close=item.closed,
                dxfattribs=attribs,
            )
        case Circle():
            msp.add_circle(item.center, item.radius, dxfattribs=attribs)
            if item.filled:
                hatch = msp.add_hatch(dxfattribs=attribs)
                hatch.set_solid_fill(color=_BYLAYER)
                path = hatch.paths.add_edge_path()
                path.add_arc(item.center, item.radius, 0.0, 360.0)
        case Text():
            text = msp.add_text(
                item.text,
                height=item.height,
                rotation=item.rotation,
                dxfattribs={**attribs, "style": TEXT_STYLE},
            )
            text.set_placement(
                item.position, align=_ALIGNMENTS[item.valign, item.halign]
            )
        case Image():
            # A DXF holds no image here; its rectangle marks where the logo goes
            x, y = item.position
            msp.add_lwpolyline(
                [
                    (x, y),
                    (x + item.width, y),
                    (x + item.width, y + item.height),
                    (x, y + item.height),
                ],
                close=True,
                dxfattribs=attribs,
            )


def write_dxf(
    drawing: Drawing, path: Path, config: DrawingConfig = DEFAULT_CONFIG
) -> Path:
    """Write a drawing to a DXF file, creating its folder if needed

    Args:
        path: The file to write.

    Returns:
        The path written.

    Raises:
        DxfAuditError: If ezdxf's audit finds errors in the document.
    """
    doc = new_document(config)
    msp = doc.modelspace()
    for item in drawing.items:
        add_item(msp, item)
    auditor = doc.audit()
    if auditor.has_errors:
        messages = "; ".join(str(error.message) for error in auditor.errors)
        raise DxfAuditError(f"The DXF of {path.name} has errors: {messages}")
    zoom.extents(msp)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(path)
    return path
