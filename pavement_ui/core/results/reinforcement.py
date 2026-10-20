"""Read models of reinforcement: bar groups, layers, clamps and stirrups."""

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
class ClampSpec:
    """U-shaped clamps that complete a layer's anchorage at an extremity support

    Attributes:
        quantity: Number of clamps.
        diameter_mm: Clamp bar diameter (mm).
        length_cm: Total clamp length l_c (cm).
        width_cm: Clamp width, equal to the stirrup inner width (cm).
    """

    quantity: int
    diameter_mm: float
    length_cm: float
    width_cm: float


@dataclass(frozen=True, slots=True)
class BarLayer:
    """One layer of longitudinal bars

    Attributes:
        index: Layer number; 1 is the closest to the tensioned face.
        y_cm: Height of the layer centroid, measured from the bottom face (cm).
        groups: Bar groups, largest diameter first.
        left_clamps: Clamps at the left end; None when the bars anchor alone.
        right_clamps: Clamps at the right end; None when the bars anchor alone.
    """

    index: int
    y_cm: float
    groups: tuple[BarGroup, ...]
    left_clamps: ClampSpec | None = None
    right_clamps: ClampSpec | None = None


@dataclass(frozen=True, slots=True)
class StirrupSpec:
    """Stirrups of a span

    Attributes:
        diameter_mm: Stirrup bar diameter (mm).
        spacing_cm: Spacing between stirrups (cm).
    """

    diameter_mm: float
    spacing_cm: float
