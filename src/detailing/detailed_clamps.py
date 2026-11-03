from dataclasses import dataclass

from src.properties.steel import Steel


@dataclass(kw_only=True)
class DetailedClamps:
    """The U-shaped clamps completing the anchorage of one bar group's end

    The U bends at the anchored bars' end, and its two legs run from there into the beam.

    Attributes:
        diameter_mm: Clamp bar diameter φ (mm).
        quantity: Number of clamps.
        width: Width of the U, between the stirrup's inner faces (cm).
        leg_length: Length of each leg, from the bend (cm).
        left: Whether the clamps anchor the bars' left end; otherwise the right.
        position: Position of the anchored bars' end, where the U bends (cm).
        source_position: Interest point of the anchored bars (cm).
        mark: Bar mark (N1, N2, …), None until marks are assigned.
    """

    diameter_mm: float
    steel: Steel
    quantity: int
    width: float  # cm
    leg_length: float  # cm
    left: bool
    is_bottom: bool
    position: float  # cm
    source_position: float  # cm
    mark: str | None = None

    @property
    def total_length(self) -> float:
        """Return the cut length of one clamp (cm): both legs plus the width"""
        return 2 * self.leg_length + self.width
