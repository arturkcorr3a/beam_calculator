
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional

from src.pavement.continuous_beam import ContinuousBeam, Span

type SupportCondition = Literal["pinned", "fixed"]

class Edges(str, Enum):
    BOTTOM = "bottom"
    TOP = "top"
    LEFT = "left"
    RIGHT = "right"

@dataclass
class SlabEdge:
    edge: Edges
    _beam: Optional[ContinuousBeam] = field(default=None, init=False)
    spans: list[Span] = field(default_factory=list[Span], init=False)
    support_condition: SupportCondition = field(default="pinned", init=False)

    @property
    def beam(self) -> ContinuousBeam:
        """Returns the supporting beam for this edge."""
        if self._beam is None:
            raise ValueError(f"Slab edge '{self.edge}' has no resolved supporting beam.")
        return self._beam

    def clear_resolved(self) -> None:
        """Clears the resolved state of the edge."""
        self._beam = None
        self.spans = []
        self.support_condition = "pinned"

    def resolve_beam(self, beam: ContinuousBeam) -> None:
        """Resolves the supporting beam for this edge."""
        self._beam = beam

    def resolve_spans(self, spans: list[Span]) -> None:
        """Resolves the spans along this edge."""
        self.spans = spans