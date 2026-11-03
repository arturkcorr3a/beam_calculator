from dataclasses import dataclass

from src.properties.steel import Steel
from src.reinforcement.stirrups import StirrupZone

_CONTIGUITY_TOLERANCE = 1e-6  # cm


@dataclass(kw_only=True)
class SpanStirrups:
    """The stirrups of one span, spread in zones between the inner faces of its pillars

    Each zone keeps one spacing, and neighboring zones touch: together they cover the span from the start pillar's inner face to the end pillar's.

    Attributes:
        zones: Stretches with a constant spacing, left to right (cm).
        diameter_mm: Stirrup bar diameter φ_t (mm).
        mark: Bar mark (N1, N2, …), None until marks are assigned.
    """

    start_pillar_id: str
    end_pillar_id: str
    zones: tuple[StirrupZone, ...]
    diameter_mm: float
    steel: Steel
    mark: str | None = None

    def __post_init__(self) -> None:
        """Validate that the zones are ordered, have length and touch each other

        Raises:
            ValueError: If there are no zones, a zone has no length, or two neighboring zones leave a gap or overlap.
        """
        if not self.zones:
            raise ValueError("Span stirrups need at least one zone.")
        for zone in self.zones:
            if zone.end <= zone.start:
                raise ValueError(
                    f"A stirrup zone must end after it starts. Got start={zone.start}, end={zone.end} cm."
                )
        for left, right in zip(self.zones, self.zones[1:], strict=False):
            if abs(right.start - left.end) > _CONTIGUITY_TOLERANCE:
                raise ValueError(
                    f"Stirrup zones must touch. Got one ending at {left.end} cm and the next starting at {right.start} cm."
                )

    @property
    def start(self) -> float:
        """Return the start of the stirrups: the start pillar's inner face (cm)"""
        return self.zones[0].start

    @property
    def end(self) -> float:
        """Return the end of the stirrups: the end pillar's inner face (cm)"""
        return self.zones[-1].end
