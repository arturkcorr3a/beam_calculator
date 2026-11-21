"""Drawing primitives in model space (cm), each on a named layer

The layout builds a ``Drawing`` out of these; the renderers only draw them.
"""

from dataclasses import dataclass, field, replace
from enum import Enum
from math import atan, atan2, ceil, cos, hypot, pi, radians, sin, tan

from src.drawing.formatting import text_width
from src.errors import EnginePreconditionError

Point = tuple[float, float]

_QUARTER = pi / 2
_BULGE_TOLERANCE = 1e-12


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


@dataclass(frozen=True)
class HoverInfo:
    """What the tooltip shows for a bar or a clamp

    Attributes:
        title: First line, in bold (N12 · 2 φ10 CA-50).
        lines: The other lines.
    """

    title: str
    lines: tuple[str, ...] = ()


@dataclass(frozen=True)
class Line:
    """A straight segment (cm)"""

    start: Point
    end: Point
    layer: str
    meta: HoverInfo | None = None


@dataclass(frozen=True)
class Polyline:
    """A chain of segments and circular arcs (cm)

    Attributes:
        points: Vertices, in order.
        bulges: One per vertex: the bulge of the segment leaving it, zero for a straight one. The bulge is the tangent of a quarter of the arc's central angle, positive counterclockwise.
        closed: Whether the last vertex joins the first.
    """

    points: tuple[Point, ...]
    bulges: tuple[float, ...]
    layer: str
    closed: bool = False
    meta: HoverInfo | None = None

    def __post_init__(self) -> None:
        """Validate the vertices and the bulges

        Raises:
            EnginePreconditionError: If there are fewer than two vertices or the bulges do not match them.
        """
        if len(self.points) < 2:
            raise EnginePreconditionError(
                f"A polyline needs at least 2 points. Got {len(self.points)}."
            )
        if len(self.bulges) != len(self.points):
            raise EnginePreconditionError(
                f"A polyline needs one bulge per point. Got {len(self.bulges)} "
                f"bulges for {len(self.points)} points."
            )

    def segments(self) -> list[tuple[Point, Point, float]]:
        """Return each segment as its start, end and bulge, closing segment included"""
        count = len(self.points) if self.closed else len(self.points) - 1
        return [
            (
                self.points[index],
                self.points[(index + 1) % len(self.points)],
                self.bulges[index],
            )
            for index in range(count)
        ]

    def flattened(self, segments_per_quarter: int) -> list[Point]:
        """Return the vertices with every arc replaced by straight pieces

        Args:
            segments_per_quarter: Straight pieces per quarter circle of arc.
        """
        points: list[Point] = [self.points[0]]
        for start, end, bulge in self.segments():
            points += arc_points(start, end, bulge, segments_per_quarter)[1:]
        return points


@dataclass(frozen=True)
class Circle:
    """A circle (cm), drawn solid when filled"""

    center: Point
    radius: float
    layer: str
    filled: bool = False


@dataclass(frozen=True)
class Text:
    """A single-line text

    Attributes:
        position: Anchor point (cm).
        height: Cap height in model space (cm), already converted from paper.
        rotation: Counterclockwise angle (degrees).
    """

    position: Point
    text: str
    height: float
    layer: str
    halign: HAlign = HAlign.LEFT
    valign: VAlign = VAlign.BASELINE
    rotation: float = 0.0

    def corners(self) -> tuple[Point, Point, Point, Point]:
        """Return the corners of the text's estimated box, rotated (cm)

        The width is the layout's estimate (``text_width``) and the height is the cap height, so descenders are left out.
        """
        width = text_width(self.text, self.height)
        left = {HAlign.LEFT: 0.0, HAlign.CENTER: -width / 2, HAlign.RIGHT: -width}[
            self.halign
        ]
        bottom = {
            VAlign.BASELINE: 0.0,
            VAlign.MIDDLE: -self.height / 2,
            VAlign.TOP: -self.height,
        }[self.valign]
        angle = radians(self.rotation)
        x0, y0 = self.position

        def place(u: float, v: float) -> Point:
            return (
                x0 + u * cos(angle) - v * sin(angle),
                y0 + u * sin(angle) + v * cos(angle),
            )

        right, top = left + width, bottom + self.height
        return (
            place(left, bottom),
            place(right, bottom),
            place(right, top),
            place(left, top),
        )


@dataclass(frozen=True)
class Image:
    """A raster image placed in a rectangle, fitted inside it without distortion

    Attributes:
        position: Lower left corner of the rectangle (cm).
        width: Width of the rectangle (cm).
        height: Height of the rectangle (cm).
        path: Image file; renderers that cannot draw it show the rectangle only.
    """

    position: Point
    width: float
    height: float
    path: str
    layer: str


DrawingItem = Line | Polyline | Circle | Text | Image


def arc_points(
    start: Point, end: Point, bulge: float, segments_per_quarter: int
) -> list[Point]:
    """Return points along a segment with a bulge, both ends included

    A straight segment gives just its ends.

    Args:
        bulge: Tangent of a quarter of the central angle, positive counterclockwise.
        segments_per_quarter: Straight pieces per quarter circle of arc.
    """
    if abs(bulge) < _BULGE_TOLERANCE:
        return [start, end]
    center, radius = arc_center(start, end, bulge)
    angle = 4 * atan(bulge)
    pieces = max(1, ceil(abs(angle) / _QUARTER * segments_per_quarter - 1e-9))
    first = atan2(start[1] - center[1], start[0] - center[0])
    points = [
        (
            center[0] + radius * cos(first + angle * piece / pieces),
            center[1] + radius * sin(first + angle * piece / pieces),
        )
        for piece in range(pieces)
    ]
    return [*points, end]


def arc_center(start: Point, end: Point, bulge: float) -> tuple[Point, float]:
    """Return the center and the radius of the arc of a segment with a bulge (cm)

    Raises:
        EnginePreconditionError: If the bulge is zero or the segment has no length.
    """
    chord = hypot(end[0] - start[0], end[1] - start[1])
    if abs(bulge) < _BULGE_TOLERANCE or chord == 0:
        raise EnginePreconditionError(
            "Only a segment with a bulge and a length has an arc."
        )
    angle = 4 * atan(bulge)
    offset = (chord / 2) / tan(angle / 2)  # from the chord's middle, to its left
    normal = (-(end[1] - start[1]) / chord, (end[0] - start[0]) / chord)
    middle = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
    center = (middle[0] + normal[0] * offset, middle[1] + normal[1] * offset)
    return center, hypot(start[0] - center[0], start[1] - center[1])


def translate(item: DrawingItem, dx: float, dy: float) -> DrawingItem:
    """Return a copy of a primitive moved by (dx, dy) (cm)"""
    match item:
        case Line():
            return replace(
                item,
                start=(item.start[0] + dx, item.start[1] + dy),
                end=(item.end[0] + dx, item.end[1] + dy),
            )
        case Polyline():
            return replace(item, points=tuple((x + dx, y + dy) for x, y in item.points))
        case Circle():
            return replace(item, center=(item.center[0] + dx, item.center[1] + dy))
        case Text() | Image():
            return replace(
                item, position=(item.position[0] + dx, item.position[1] + dy)
            )


def item_points(item: DrawingItem, segments_per_quarter: int = 8) -> list[Point]:
    """Return points whose bounding box is the primitive's (cm)

    Arcs are sampled, and texts use their estimated box.
    """
    match item:
        case Line():
            return [item.start, item.end]
        case Polyline():
            return item.flattened(segments_per_quarter)
        case Circle():
            x, y = item.center
            r = item.radius
            return [(x - r, y - r), (x + r, y + r)]
        case Text():
            return list(item.corners())
        case Image():
            x, y = item.position
            return [(x, y), (x + item.width, y + item.height)]


@dataclass
class Drawing:
    """A set of primitives in model space (cm)

    Attributes:
        paper_mm: Width and height of the sheet of paper, its lower left corner at the origin; None when the drawing is not on a sheet.
    """

    items: list[DrawingItem] = field(default_factory=list[DrawingItem])
    paper_mm: tuple[float, float] | None = None

    def add(self, *items: DrawingItem) -> None:
        """Append primitives"""
        self.items.extend(items)

    def extend(self, other: Drawing) -> None:
        """Append all the primitives of another drawing"""
        self.items.extend(other.items)

    def translated(self, dx: float, dy: float) -> Drawing:
        """Return a copy moved by (dx, dy) (cm)"""
        return Drawing([translate(item, dx, dy) for item in self.items], self.paper_mm)

    def bounds(self) -> tuple[float, float, float, float]:
        """Return the bounding box as x min, y min, x max, y max (cm)

        Raises:
            EnginePreconditionError: If the drawing is empty.
        """
        if not self.items:
            raise EnginePreconditionError("An empty drawing has no bounds.")
        points = [point for item in self.items for point in item_points(item)]
        xs = [x for x, _ in points]
        ys = [y for _, y in points]
        return min(xs), min(ys), max(xs), max(ys)

    def layers(self) -> list[str]:
        """Return the layers in use, in order of first appearance"""
        return list(dict.fromkeys(item.layer for item in self.items))
