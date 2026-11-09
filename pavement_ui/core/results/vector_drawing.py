"""A renderer-neutral vector drawing resolved by the engine (model space in cm)."""

from dataclasses import dataclass
from enum import Enum

type Point = tuple[float, float]


class HAlign(Enum):
    """Horizontal anchor of a text"""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class VAlign(Enum):
    """Vertical anchor of a text"""

    BASELINE = "baseline"
    MIDDLE = "middle"
    TOP = "top"


@dataclass(frozen=True, slots=True)
class LayerLook:
    """How one layer is drawn

    Attributes:
        name: Layer name, as used by the items.
        color: Screen color over a white background ("#rrggbb").
        width_mm: Plotted line weight (mm).
        dashed: Whether the lines are dashed (axes and hidden lines).
    """

    name: str
    color: str
    width_mm: float
    dashed: bool


@dataclass(frozen=True, slots=True)
class LineShape:
    """A straight segment (cm)"""

    start: Point
    end: Point
    layer: str


@dataclass(frozen=True, slots=True)
class PolylineShape:
    """A chain of segments and circular arcs (cm)

    Attributes:
        points: Vertices with every arc flattened into straight pieces, to paint.
        closed: Whether the last vertex joins the first.
        vertices: The original vertices, to export.
        bulges: One per original vertex: the bulge of the segment leaving it,
            zero for a straight one (tangent of a quarter of the arc's angle).
    """

    points: tuple[Point, ...]
    closed: bool
    layer: str
    vertices: tuple[Point, ...] = ()
    bulges: tuple[float, ...] = ()


@dataclass(frozen=True, slots=True)
class CircleShape:
    """A circle (cm), solid when filled"""

    center: Point
    radius: float
    filled: bool
    layer: str


@dataclass(frozen=True, slots=True)
class TextShape:
    """A single-line text

    Attributes:
        position: Anchor point (cm).
        height: Cap height (cm).
        rotation: Counterclockwise angle (degrees).
    """

    position: Point
    text: str
    height: float
    layer: str
    h_align: HAlign = HAlign.LEFT
    v_align: VAlign = VAlign.BASELINE
    rotation: float = 0.0


@dataclass(frozen=True, slots=True)
class VectorDrawing:
    """A drawing to paint: items by kind, the looks of their layers and the bounds

    Attributes:
        bounds: (x_min, y_min, x_max, y_max) of every item, texts included (cm).
        scale: Scale denominator the drawing's texts and offsets were laid out
            for (50 for 1:50); printing at it gives the texts their paper size.
    """

    lines: tuple[LineShape, ...]
    polylines: tuple[PolylineShape, ...]
    circles: tuple[CircleShape, ...]
    texts: tuple[TextShape, ...]
    layers: tuple[LayerLook, ...]
    bounds: tuple[float, float, float, float]
    scale: float = 50.0
