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
        left_hook_cm: Extra cut length of the 90° hook at the left end (cm);
            None without a hook.
        right_hook_cm: Extra cut length of the 90° hook at the right end (cm);
            None without a hook.
    """

    index: int
    y_cm: float
    groups: tuple[BarGroup, ...]
    left_clamps: ClampSpec | None = None
    right_clamps: ClampSpec | None = None
    left_hook_cm: float | None = None
    right_hook_cm: float | None = None


@dataclass(frozen=True, slots=True)
class StirrupZoneSpec:
    """Stretch of a span with a constant stirrup spacing

    Attributes:
        start_m: Zone start from the beam start (m).
        end_m: Zone end from the beam start (m).
        spacing_cm: Spacing between stirrups in the zone (cm).
    """

    start_m: float
    end_m: float
    spacing_cm: float


@dataclass(frozen=True, slots=True)
class StirrupSpec:
    """Stirrups of a span

    Attributes:
        diameter_mm: Stirrup bar diameter (mm).
        spacing_cm: Spacing at the span ends, the densest (cm).
        zones: Zones along the span, left to right; a single zone (or none)
            when the spacing is uniform.
    """

    diameter_mm: float
    spacing_cm: float
    zones: tuple[StirrupZoneSpec, ...] = ()

    @property
    def is_scaled(self) -> bool:
        """Whether the spacing changes along the span"""
        return len(self.zones) > 1

    def at(self, position_m: float) -> StirrupSpec:
        """Return the uniform stirrups of the zone containing a position from the beam start (m)

        Falls back to the span-end spacing when no zone contains the position.
        """
        spacing_cm = next(
            (
                zone.spacing_cm
                for zone in self.zones
                if zone.start_m <= position_m <= zone.end_m
            ),
            self.spacing_cm,
        )
        return StirrupSpec(self.diameter_mm, spacing_cm)
