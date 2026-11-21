from dataclasses import dataclass
from enum import Enum

from src.errors import EnginePreconditionError
from src.properties.steel import Steel
from src.structural_elements.rebar import HookGeometry


class BarRole(Enum):
    """Why a detailed bar is in the beam"""

    MAIN = "main"  # designed at an interest point
    CONSTRUCTION = "construction"  # holds the stirrups' corners


@dataclass(kw_only=True)
class DetailedBar:
    """A run of identical longitudinal bars, side by side in one layer

    Positions follow the beam's analysis axis. The straight segment runs from the outer face of the left end to the outer face of the right end; a hook adds its extra cut length beyond that.

    Attributes:
        diameter_mm: Bar diameter φ (mm).
        quantity: Number of identical bars in the run.
        is_tensioned: Whether the bars were designed as tensioned; False for the compressed reinforcement.
        layer_index: Layer of the bars, 0 being the closest to the face.
        y: Height of the bars' axis, from the bottom face of the section (cm).
        start: Left end of the straight segment (cm).
        end: Right end of the straight segment (cm).
        left_hook: Geometry of the left hook, or None without one.
        right_hook: Geometry of the right hook, or None without one.
        left_hook_length: Extra cut length of the left hook, zero without one (cm).
        right_hook_length: Extra cut length of the right hook, zero without one (cm).
        source_positions: Interest points the bars were designed at, left to right (cm); two or more after a merge, none for construction bars.
        good_adherence: Whether the bars sit in the good bond zone.
        area_ratio: Required over provided steel area of the source reinforcement, used to size laps.
        mark: Bar mark (N1, N2, …), None until marks are assigned.
    """

    diameter_mm: float
    steel: Steel
    quantity: int
    is_bottom: bool
    is_tensioned: bool
    layer_index: int
    y: float  # cm
    start: float  # cm
    end: float  # cm
    left_hook: HookGeometry | None = None
    right_hook: HookGeometry | None = None
    left_hook_length: float = 0.0  # cm
    right_hook_length: float = 0.0  # cm
    role: BarRole = BarRole.MAIN
    source_positions: tuple[float, ...] = ()  # cm
    good_adherence: bool = True
    area_ratio: float = 1.0
    mark: str | None = None

    def __post_init__(self) -> None:
        """Validate the quantity and the extent

        Raises:
            EnginePreconditionError: If the quantity is below 1 or the bar ends before it starts.
        """
        if self.quantity < 1:
            raise EnginePreconditionError(
                f"A bar run needs at least 1 bar. Got {self.quantity}."
            )
        if self.end < self.start:
            raise EnginePreconditionError(
                f"A bar cannot end before it starts. Got start={self.start}, end={self.end} cm."
            )

    @property
    def straight_length(self) -> float:
        """Return the length of the straight segment (cm)"""
        return self.end - self.start

    @property
    def total_length(self) -> float:
        """Return the cut length of one bar (cm): straight segment plus hooks"""
        return self.straight_length + self.left_hook_length + self.right_hook_length
