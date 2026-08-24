from dataclasses import dataclass, field
from typing import Optional

from src.pavement.continuous_beam import ContinuousBeam
from src.pavement.utils import Axis
from src.pavement.pillar import Pillar


@dataclass
class Span:
    """
    One span of a ContinuousBeam — the segment between two consecutive pillars.

    supported_slab_ids is populated by Pavement.validate() after slab resolution;
    a span on an interior edge will list both adjacent slabs.
    """
    beam: ContinuousBeam
    start_pillar_id: str
    end_pillar_id: str
    supported_slab_ids: tuple[Optional[str], Optional[str]] = field(default_factory=tuple[Optional[str], Optional[str]], init=False)

    def get_length(self, pillar_registry: dict[str, Pillar]) -> float:
        """Returns the span's length (cm) from the supporting pillars."""
        axis = self.beam.axis
        start_pillar = pillar_registry[self.start_pillar_id]
        end_pillar = pillar_registry[self.end_pillar_id]
        if axis == Axis.X:
            return abs(end_pillar.x - start_pillar.x)
        elif axis == Axis.Y:
            return abs(end_pillar.y - start_pillar.y)
        else:
            raise ValueError("Invalid axis for length calculation.")

    def contains_pillar(self, pillar_id: str) -> bool:
        """Checks if the span contains a specific pillar ID."""
        return pillar_id == self.start_pillar_id or pillar_id == self.end_pillar_id

    def add_supported_slab(self, slab_id: str) -> None:
        """Adds a slab ID to the supported_slab_ids tuple."""
        if self.supported_slab_ids[0] is None:
            self.supported_slab_ids = (slab_id, self.supported_slab_ids[1])
        elif self.supported_slab_ids[1] is None:
            self.supported_slab_ids = (self.supported_slab_ids[0], slab_id)
        else:
            raise ValueError(f"Span between '{self.start_pillar_id}' and '{self.end_pillar_id}' already supports two slabs.")