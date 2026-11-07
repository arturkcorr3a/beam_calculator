from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class ClearSpan:
    """The stretch of a beam between the inner faces of two pillars

    Attributes:
        start: Inner face of the start pillar (cm).
        end: Inner face of the end pillar (cm).
        side_heights: Height of each side face left visible: the section height, less the thickness of the slab on that side (cm).
    """

    start: float  # cm
    end: float  # cm
    side_heights: tuple[float, float]  # cm

    @property
    def length(self) -> float:
        """Return the clear length of the span (cm)"""
        return self.end - self.start
