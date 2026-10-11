"""Geometry of the dimensioned cross-section, in cm with y up from the bottom face — pure.

Layer heights come from the engine (``BarLayer.y_cm``); only the horizontal
placement of the bars inside a layer is decided here, for drawing.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from pavement_ui.core.results.beam_result import DesignPoint
from pavement_ui.core.results.reinforcement import BarLayer

_MM_PER_CM = 10.0


@dataclass(frozen=True, slots=True)
class Rect:
    """Axis-aligned rectangle (cm), y up"""

    x0: float
    y0: float
    x1: float
    y1: float


@dataclass(frozen=True, slots=True)
class Bar:
    """One bar: center (cm) and diameter (cm)"""

    x: float
    y: float
    diameter: float


@dataclass(frozen=True, slots=True)
class SectionLayout:
    """Everything the section drawing needs

    Attributes:
        stirrup: Centerline of the stirrup bar.
        stirrup_diameter: Stirrup bar diameter (cm).
        layers: Each layer's bars, with the layer (for its callout).
    """

    concrete: Rect
    stirrup: Rect
    stirrup_diameter: float
    layers: tuple[tuple[BarLayer, tuple[Bar, ...]], ...]


def _diameters_corners_first(layer: BarLayer) -> list[float]:
    """Bar diameters (cm) ordered so the largest bars go to the layer's ends."""
    diameters = [
        group.diameter_mm / _MM_PER_CM
        for group in layer.groups
        for _ in range(group.count)
    ]
    diameters.sort(reverse=True)
    left = diameters[0::2]
    right = diameters[1::2]
    return left + right[::-1]


def _layer_bars(layer: BarLayer, x_min: float, x_max: float) -> tuple[Bar, ...]:
    """Spread the bars evenly between the stirrup's inner faces."""
    diameters = _diameters_corners_first(layer)
    if not diameters:
        return ()
    first = x_min + diameters[0] / 2
    last = x_max - diameters[-1] / 2
    if len(diameters) == 1:
        return (Bar((x_min + x_max) / 2, layer.y_cm, diameters[0]),)
    step = (last - first) / (len(diameters) - 1)
    return tuple(Bar(first + i * step, layer.y_cm, d) for i, d in enumerate(diameters))


def section_layout(
    point: DesignPoint,
    width_cm: float,
    height_cm: float,
    cover_cm: float,
    stirrup_diameter_mm: float,
) -> SectionLayout:
    """Lay out the section of one design point"""
    stirrup_d = stirrup_diameter_mm / _MM_PER_CM
    inset = cover_cm + stirrup_d / 2
    inner_left, inner_right = cover_cm + stirrup_d, width_cm - cover_cm - stirrup_d
    layers: Sequence[BarLayer] = (*point.tension_layers, *point.compression_layers)
    return SectionLayout(
        concrete=Rect(0.0, 0.0, width_cm, height_cm),
        stirrup=Rect(inset, inset, width_cm - inset, height_cm - inset),
        stirrup_diameter=stirrup_d,
        layers=tuple(
            (layer, _layer_bars(layer, inner_left, inner_right)) for layer in layers
        ),
    )
