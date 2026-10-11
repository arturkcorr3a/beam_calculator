"""Screen geometry of an internal-force diagram — pure, no Qt.

Brazilian convention: the bending moment is drawn positive (sagging) below the
axis; the shear force positive above it.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto

from pavement_ui.core.results.beam_result import DiagramSeries, SpanResult, SupportMark

_SIDE_MARGIN_PX = 40.0
_VERTICAL_MARGIN_PX = 22.0
_HEADROOM = 1.15
_AT_SUPPORT_M = 0.011  # samples within this distance belong to the support
_NEGLIGIBLE = 0.05  # kN·m or kN: values this small get no label


class DiagramKind(Enum):
    MOMENT = auto()
    SHEAR = auto()


@dataclass(frozen=True, slots=True)
class ValueLabel:
    """A value to print at (x, y) px; outward is the side away from the axis"""

    x: float
    y: float
    value: float
    below_axis: bool


@dataclass(frozen=True, slots=True)
class DiagramGeometry:
    axis_y: float
    left: float
    right: float
    polyline: tuple[tuple[float, float], ...]
    supports: tuple[tuple[float, str], ...]
    labels: tuple[ValueLabel, ...]


def _moment_labels(
    series: DiagramSeries, spans: Sequence[SpanResult], supports: Sequence[SupportMark]
) -> list[tuple[float, float]]:
    """Greatest sagging moment of each span and hogging moment at each support (x m, value)."""
    samples = list(zip(series.x_m, series.values, strict=True))
    found: list[tuple[float, float]] = []
    for span in spans:
        inside = [(x, v) for x, v in samples if span.start_m < x < span.end_m]
        if inside:
            x, v = max(inside, key=lambda s: s[1])
            if v > _NEGLIGIBLE:
                found.append((x, v))
    for support in supports:
        near = [v for x, v in samples if abs(x - support.position_m) <= _AT_SUPPORT_M]
        if near and min(near) < -_NEGLIGIBLE:
            found.append((support.position_m, min(near)))
    return found


def _shear_labels(
    series: DiagramSeries, spans: Sequence[SpanResult]
) -> list[tuple[float, float]]:
    """Shear just inside each end of each span (x m, value)."""
    samples = list(zip(series.x_m, series.values, strict=True))
    found: list[tuple[float, float]] = []
    for span in spans:
        start = [
            (x, v)
            for x, v in samples
            if span.start_m <= x <= span.start_m + _AT_SUPPORT_M
        ]
        end = [
            (x, v) for x, v in samples if span.end_m - _AT_SUPPORT_M <= x <= span.end_m
        ]
        if start:
            found.append(
                (span.start_m, start[-1][1])
            )  # right-hand value at the support
        if end:
            found.append((span.end_m, end[0][1]))  # left-hand value at the support
    return [(x, v) for x, v in found if abs(v) > _NEGLIGIBLE]


def diagram_geometry(  # noqa: PLR0913 — every input shapes the drawing
    series: DiagramSeries,
    supports: Sequence[SupportMark],
    spans: Sequence[SpanResult],
    kind: DiagramKind,
    width_px: float,
    height_px: float,
) -> DiagramGeometry:
    """Scale the diagram into a width × height pixel area"""
    length = (
        max((s.position_m for s in supports), default=max(series.x_m, default=1.0))
        or 1.0
    )
    left, right = _SIDE_MARGIN_PX, width_px - _SIDE_MARGIN_PX
    axis_y = height_px / 2
    peak = max((abs(v) for v in series.values), default=0.0) * _HEADROOM or 1.0
    half = height_px / 2 - _VERTICAL_MARGIN_PX
    sign = 1.0 if kind is DiagramKind.MOMENT else -1.0  # moment positive goes down

    def px(x_m: float) -> float:
        return left + x_m / length * (right - left)

    def py(value: float) -> float:
        return axis_y + sign * value / peak * half

    polyline = tuple(
        (px(x), py(v)) for x, v in zip(series.x_m, series.values, strict=True)
    )
    raw = (
        _moment_labels(series, spans, supports)
        if kind is DiagramKind.MOMENT
        else _shear_labels(series, spans)
    )
    labels = tuple(ValueLabel(px(x), py(v), v, py(v) > axis_y) for x, v in raw)
    return DiagramGeometry(
        axis_y=axis_y,
        left=left,
        right=right,
        polyline=polyline,
        supports=tuple((px(s.position_m), s.label) for s in supports),
        labels=labels,
    )
