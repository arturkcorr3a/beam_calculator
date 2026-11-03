from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class LapSplice:
    """A lap splice between two bar runs on the same face and layer

    Attributes:
        layer_index: Layer of the spliced bars, 0 being the closest to the face.
        start: Left end of the lap: the right-hand bars' start (cm).
        end: Right end of the lap: the left-hand bars' end (cm).
        quantity: Number of bar pairs spliced.
        diameter_mm: Diameter the lap was sized with, the smaller of the two (mm).
    """

    is_bottom: bool
    layer_index: int
    start: float  # cm
    end: float  # cm
    quantity: int
    diameter_mm: float

    @property
    def length(self) -> float:
        """Return the lap length (cm)"""
        return self.end - self.start
