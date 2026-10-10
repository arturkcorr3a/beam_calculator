"""Read models of reinforcement: bar groups, layers and stirrups."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BarGroup:
    """Bars of one diameter within a layer

    Attributes:
        count: Number of bars.
        diameter_mm: Bar diameter (mm).
    """

    count: int
    diameter_mm: float


@dataclass(frozen=True, slots=True)
class BarLayer:
    """One layer of longitudinal bars

    Attributes:
        index: Layer number; 1 is the closest to the tensioned face.
        y_cm: Height of the layer centroid, measured from the bottom face (cm).
        groups: Bar groups, largest diameter first.
    """

    index: int
    y_cm: float
    groups: tuple[BarGroup, ...]


@dataclass(frozen=True, slots=True)
class StirrupSpec:
    """Stirrups of a span

    Attributes:
        diameter_mm: Stirrup bar diameter (mm).
        spacing_cm: Spacing between stirrups (cm).
    """

    diameter_mm: float
    spacing_cm: float
