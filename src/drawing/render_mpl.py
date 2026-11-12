"""Matplotlib renderer: draws a Drawing on axes in model space (cm), texts scaling with the zoom"""

# matplotlib leaves **kwargs unannotated, so many of its methods are partially unknown
# pyright: reportUnknownMemberType=false

from functools import lru_cache
from weakref import WeakKeyDictionary

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.backend_bases import Event, MouseEvent
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D
from matplotlib.offsetbox import AnnotationBbox, TextArea, VPacker
from matplotlib.patches import Circle as CirclePatch
from matplotlib.patches import Patch, PathPatch
from matplotlib.path import Path as MplPath
from matplotlib.textpath import TextPath
from matplotlib.transforms import Affine2D
from matplotlib.typing import LineStyleType

from src.drawing.config import DEFAULT_CONFIG, DrawingConfig
from src.drawing.formatting import fmt_dec
from src.drawing.layers import CONTINUOUS, LINETYPE_PATTERNS_MM, LayerStyle, layer_style
from src.drawing.primitives import (
    Circle,
    Drawing,
    HAlign,
    HoverInfo,
    Image,
    Line,
    Point,
    Polyline,
    Text,
    VAlign,
)

FONT_FAMILY = "DejaVu Sans"
FIGURE_SIZE = (16.0, 9.0)  # in
MM_PER_INCH = 25.4
_POINTS_PER_MM = 72 / MM_PER_INCH
_CAP_HEIGHT_RATIO = 0.72  # cap height over font size, DejaVu Sans
_DOT_MM = 0.2  # length of a linetype's dot on screen (mm)
_MARGIN_MM = 10.0  # paper margin around the drawing (mm)
_LEGEND_ANCHOR = (1.0, 1.0)
_AXES_RIGHT = 0.80  # room on the right for the legend
# Draw order: lines under circles under texts
_Z_LINES, _Z_CIRCLES, _Z_TEXTS = 1.0, 2.0, 3.0
_HIT_PX = 6.0  # how close the cursor must pass to a bar to hit it
_TOOLTIP_OFFSET_PX = 16.0
_TOOLTIP_SIZE = 9.0  # points
_HIGHLIGHT_COLOR = "#f9a825"
_HIGHLIGHT_ALPHA = 0.45
_HIGHLIGHT_WIDTH = 9.0  # points


def linewidth(style: LayerStyle) -> float:
    """Return a layer's line width on screen (points)"""
    return style.lineweight_mm * _POINTS_PER_MM


def dash_style(style: LayerStyle) -> LineStyleType:
    """Return a layer's matplotlib linestyle: solid, or the paper pattern in points

    Matplotlib scales dashes by the line width, so the pattern is divided by it to keep the paper lengths.
    """
    if style.linetype == CONTINUOUS:
        return "solid"
    width = linewidth(style)
    pattern = tuple(
        max(abs(length), _DOT_MM) * _POINTS_PER_MM / width
        for length in LINETYPE_PATTERNS_MM[style.linetype]
    )
    return (0.0, pattern)


@lru_cache(maxsize=4096)
def _text_path(text: str, size: float) -> MplPath:
    """Return the outline of a text at a font size, from its origin"""
    return TextPath(
        (0.0, 0.0), text, size=size, prop=FontProperties(family=FONT_FAMILY)
    )


def text_outline(item: Text) -> MplPath:
    """Return a text's outline placed in model space (cm), aligned by its extents"""
    path = _text_path(item.text, item.height / _CAP_HEIGHT_RATIO)
    extents = path.get_extents()
    dx = {
        HAlign.LEFT: -extents.x0,
        HAlign.CENTER: -(extents.x0 + extents.x1) / 2,
        HAlign.RIGHT: -extents.x1,
    }[item.halign]
    dy = {
        VAlign.BASELINE: 0.0,
        VAlign.MIDDLE: -item.height / 2,
        VAlign.TOP: -item.height,
    }[item.valign]
    transform = (
        Affine2D()
        .translate(dx, dy)
        .rotate_deg(item.rotation)
        .translate(item.position[0], item.position[1])
    )
    return path.transformed(transform)


def _segments(item: Line | Polyline, config: DrawingConfig) -> list[list[Point]]:
    """Return the polylines that draw a line or polyline, arcs flattened"""
    if isinstance(item, Line):
        return [[item.start, item.end]]
    points = item.flattened(config.arc_segments)
    return [points]


def draw(drawing: Drawing, ax: Axes, config: DrawingConfig = DEFAULT_CONFIG) -> None:
    """Draw the primitives on the axes, one collection per layer and kind

    Also adds a legend with one entry per layer in use, and shows the cursor's position with a decimal comma.
    """
    lines: dict[str, list[list[Point]]] = {}
    circles: dict[str, list[Circle]] = {}
    texts: dict[str, list[MplPath]] = {}
    for item in drawing.items:
        match item:
            case Line() | Polyline():
                lines.setdefault(item.layer, []).extend(_segments(item, config))
            case Circle():
                circles.setdefault(item.layer, []).append(item)
            case Text():
                if item.text.strip():
                    texts.setdefault(item.layer, []).append(text_outline(item))
            case Image():
                _draw_image(item, ax)
    for layer, segments in lines.items():
        style = layer_style(layer)
        ax.add_collection(
            LineCollection(
                segments,
                colors=style.screen_color,
                linewidths=linewidth(style),
                linestyles=dash_style(style),
                capstyle="round",
                joinstyle="round",
                zorder=_Z_LINES,
                label=layer,
            )
        )
    for layer, items in circles.items():
        style = layer_style(layer)
        patches = [CirclePatch(c.center, c.radius, fill=c.filled) for c in items]
        ax.add_collection(
            PatchCollection(
                patches,
                facecolors=[style.screen_color if c.filled else "none" for c in items],
                edgecolors=style.screen_color,
                linewidths=linewidth(style),
                zorder=_Z_CIRCLES,
            )
        )
    for layer, paths in texts.items():
        style = layer_style(layer)
        ax.add_collection(
            PatchCollection(
                [PathPatch(path) for path in paths],
                facecolors=style.screen_color,
                edgecolors="none",
                linewidths=0.0,
                zorder=_Z_TEXTS,
            )
        )
    if drawing.paper_mm is None:
        _add_legend(drawing, ax)  # a sheet has its own legend block
    ax.format_coord = format_coord  # type: ignore[method-assign]


def _draw_image(item: Image, ax: Axes) -> None:
    """Draw an image fitted inside its rectangle, centered and undistorted; skipped when the file is unreadable"""
    try:
        picture = plt.imread(item.path)
    except OSError:
        return
    rows, columns = picture.shape[:2]
    scale = min(item.width / columns, item.height / rows)
    width, height = columns * scale, rows * scale
    left = item.position[0] + (item.width - width) / 2
    bottom = item.position[1] + (item.height - height) / 2
    ax.imshow(
        picture,
        extent=(left, left + width, bottom, bottom + height),
        aspect="auto",
        interpolation="antialiased",
        zorder=_Z_TEXTS,
    )


def format_coord(x: float, y: float) -> str:
    """Return the cursor's position for the toolbar, with a decimal comma"""
    return f"x = {fmt_dec(x)} cm   y = {fmt_dec(y)} cm"


def _add_legend(drawing: Drawing, ax: Axes) -> None:
    """Add one legend entry per layer in use, with a sample of its line"""
    handles: list[Line2D | Patch] = []
    for name in drawing.layers():
        style = layer_style(name)
        handles.append(
            Line2D(
                [],
                [],
                color=style.screen_color,
                linewidth=max(linewidth(style), 1.0),
                linestyle=dash_style(style),
                label=f"{name} · {style.description}",
            )
        )
    if handles:
        ax.legend(
            handles=handles,
            loc="upper left",
            bbox_to_anchor=_LEGEND_ANCHOR,
            fontsize="small",
            frameon=False,
        )


def make_figure(drawing: Drawing, config: DrawingConfig = DEFAULT_CONFIG) -> Figure:
    """Return a pyplot figure showing the drawing, white, with equal axes and no frame

    A drawing on a sheet gives a figure of the sheet's size in true scale, the axes filling it, so a PDF or a PNG prints at the sheet's scale. Any other drawing is shown with a 10 mm paper margin around its bounds.
    """
    if drawing.paper_mm is not None:
        return _sheet_figure(drawing, drawing.paper_mm, config)
    figure = plt.figure(figsize=FIGURE_SIZE, facecolor="white")
    ax = figure.add_subplot()
    figure.subplots_adjust(left=0.01, right=_AXES_RIGHT, bottom=0.01, top=0.99)
    ax.set_facecolor("white")
    ax.set_aspect("equal", adjustable="datalim")
    ax.axis("off")
    draw(drawing, ax, config)
    if drawing.items:
        # Set the data limits instead of fixing both axis limits, so the equal
        # aspect can widen whichever axis it needs to
        x_min, y_min, x_max, y_max = drawing.bounds()
        margin = config.paper(_MARGIN_MM)
        ax.dataLim.set_points(
            np.array(
                [[x_min - margin, y_min - margin], [x_max + margin, y_max + margin]]
            )
        )
        ax.margins(0.0)
        ax.autoscale_view()
    attach_tooltip(figure, ax, drawing, config)
    return figure


def _sheet_figure(
    drawing: Drawing, paper_mm: tuple[float, float], config: DrawingConfig
) -> Figure:
    """Return the figure of a sheet: its paper size in inches, the axes covering the whole of it"""
    width_mm, height_mm = paper_mm
    figure = plt.figure(
        figsize=(width_mm / MM_PER_INCH, height_mm / MM_PER_INCH), facecolor="white"
    )
    ax = figure.add_axes((0.0, 0.0, 1.0, 1.0))
    ax.set_facecolor("white")
    ax.axis("off")
    draw(drawing, ax, config)
    ax.set_xlim(0.0, config.paper(width_mm))
    ax.set_ylim(0.0, config.paper(height_mm))
    ax.set_aspect("equal")
    attach_tooltip(figure, ax, drawing, config)
    return figure


class HoverTooltip:
    """Tooltip and highlight of the bar or clamp under the cursor

    Every line and polyline with a ``meta`` is a candidate. The cursor hits one when it passes within 6 px of one of its segments; the closest hit is highlighted and its ``HoverInfo`` shown in a box 16 px from the cursor.
    """

    def __init__(self, ax: Axes, drawing: Drawing, config: DrawingConfig) -> None:
        self.ax = ax
        self.items: list[tuple[HoverInfo, list[Point]]] = []
        segments: list[tuple[float, float, float, float]] = []
        owners: list[int] = []
        for item in drawing.items:
            if isinstance(item, (Line, Polyline)) and item.meta is not None:
                points = _segments(item, config)[0]
                for start, end in zip(points[:-1], points[1:], strict=True):
                    segments.append((*start, *end))
                    owners.append(len(self.items))
                self.items.append((item.meta, points))
        self.segments = np.array(segments, dtype=float).reshape(-1, 4)
        self.owners = np.array(owners, dtype=int)
        self.current: int | None = None
        self.title = TextArea("", textprops={"weight": "bold", "size": _TOOLTIP_SIZE})
        self.body = TextArea("", textprops={"size": _TOOLTIP_SIZE})
        self.box = AnnotationBbox(
            VPacker(children=[self.title, self.body], align="left", pad=0, sep=2),
            (0.0, 0.0),
            xybox=(_TOOLTIP_OFFSET_PX, _TOOLTIP_OFFSET_PX),
            boxcoords="offset pixels",
            box_alignment=(0.0, 0.0),
            bboxprops={"facecolor": "white", "edgecolor": "#9e9e9e"},
            zorder=10,
        )
        self.box.set_visible(False)
        ax.add_artist(self.box)
        (self.highlight,) = ax.plot(
            [],
            [],
            color=_HIGHLIGHT_COLOR,
            alpha=_HIGHLIGHT_ALPHA,
            linewidth=_HIGHLIGHT_WIDTH,
            solid_capstyle="round",
            zorder=_Z_LINES - 0.5,
        )
        self.highlight.set_visible(False)

    def hit(self, x: float, y: float) -> int | None:
        """Return the index of the item whose segments pass within 6 px of a point, or None

        Args:
            x, y: The point in data coordinates (cm).
        """
        if not len(self.segments):
            return None
        origin = self.ax.transData.transform((0.0, 0.0))
        unit = self.ax.transData.transform((1.0, 0.0))
        pixels_per_cm = float(abs(unit[0] - origin[0]))
        if pixels_per_cm <= 0:
            return None
        x0, y0, x1, y1 = self.segments.T
        dx, dy = x1 - x0, y1 - y0
        length2 = dx * dx + dy * dy
        safe = np.where(length2 > 0, length2, 1.0)
        t = np.clip(((x - x0) * dx + (y - y0) * dy) / safe, 0.0, 1.0)
        distance = np.hypot(x0 + t * dx - x, y0 + t * dy - y) * pixels_per_cm
        nearest = int(np.argmin(distance))
        if distance[nearest] >= _HIT_PX:
            return None
        return int(self.owners[nearest])

    def on_move(self, event: Event) -> None:
        """Update the tooltip for a mouse move; redraw only when its state changes"""
        index: int | None = None
        x = y = 0.0
        if (
            isinstance(event, MouseEvent)
            and event.inaxes is self.ax
            and event.xdata is not None
            and event.ydata is not None
        ):
            x, y = float(event.xdata), float(event.ydata)
            index = self.hit(x, y)
        if index is None:
            if self.current is None:
                return
            self.current = None
            self.box.set_visible(False)
            self.highlight.set_visible(False)
        else:
            meta, points = self.items[index]
            if index != self.current:
                self.current = index
                self.title.set_text(meta.title)
                self.body.set_text("\n".join(meta.lines))
                self.highlight.set_data([p[0] for p in points], [p[1] for p in points])
                self.highlight.set_visible(True)
                self.box.set_visible(True)
            self.box.xy = (x, y)
        self.ax.figure.canvas.draw_idle()


TOOLTIPS: WeakKeyDictionary[Figure, HoverTooltip] = WeakKeyDictionary()


def attach_tooltip(
    figure: Figure, ax: Axes, drawing: Drawing, config: DrawingConfig
) -> HoverTooltip:
    """Show a tooltip for the bars and clamps under the cursor, and return it

    The tooltip is also kept in ``TOOLTIPS`` under its figure.
    """
    tooltip = HoverTooltip(ax, drawing, config)

    def on_move(event: Event) -> None:
        tooltip.on_move(event)

    figure.canvas.mpl_connect("motion_notify_event", on_move)
    TOOLTIPS[figure] = tooltip
    return tooltip
