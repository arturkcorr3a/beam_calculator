from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Literal

from src.logger import log_interaction, log_property, logger_label

if TYPE_CHECKING:
    from src.pavement.continuous_beam import ContinuousBeam, Span
    from src.pavement.pillar import Pillar
    from src.pavement.slab import Slab

type SupportCondition = Literal["pinned", "fixed"]

# PAPER get reference for this method of resolving support
THICKNESS_DIFFERENCE_FIXED_THRESHOLD = 2.0  # cm
FIXED_RATIO_THRESHOLD = 0.8


class Edges(str, Enum):
    BOTTOM = "bottom"
    TOP = "top"
    LEFT = "left"
    RIGHT = "right"


@logger_label("{label}")
@dataclass
class SlabEdge:
    edge: Edges
    _beam: ContinuousBeam | None = field(default=None, init=False)
    slab: Slab
    spans: list[Span] = field(default_factory=list, init=False)  # type: ignore
    support_condition: SupportCondition = field(default="pinned", init=False)
    influence_area: float = field(default=0.0, init=False)

    @property
    def label(self) -> str:
        return self.slab.id

    @property
    def beam(self) -> ContinuousBeam:
        """Returns the supporting beam for this edge."""
        if self._beam is None:
            raise ValueError(
                f"Slab edge '{self.edge}' has no resolved supporting beam."
            )
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

    # PAPER get reference for this method of resolving support
    def resolve_support_condition(self, pillar_registry: dict[str, Pillar]) -> None:
        """Resolves the support condition for this edge, based on the thickness difference between adjacent slabs."""
        supported_length = 0
        fixed_length = 0
        for span in self.spans:
            other_slab = span.get_other_supported_slab(self.slab)
            if other_slab is None:
                supported_length += span.get_length(pillar_registry)
            elif (
                other_slab.thickness > self.slab.thickness
                or abs(other_slab.thickness - self.slab.thickness)
                <= THICKNESS_DIFFERENCE_FIXED_THRESHOLD
            ):
                fixed_length += span.get_length(pillar_registry)
            else:
                supported_length += span.get_length(pillar_registry)

        total_length = supported_length + fixed_length
        if fixed_length / total_length > 0.8:
            self.support_condition = "fixed"
        log_property(f"{self.edge.value}: {self.support_condition} ({fixed_length:.0f} / {total_length:.0f} cm fixed)")

    def unload_on_spans(self, pillar_registry: dict[str, Pillar]) -> None:
        """Distributes the slab's tributary load along this edge's supporting spans (kN/m)."""
        edge_length_m = (
            sum(span.get_length(pillar_registry) for span in self.spans) / 100
        )
        permanent_linear_load = (
            self.slab.permanent_load * self.influence_area / edge_length_m
        )  # kN/m
        variable_linear_load = (
            self.slab.variable_load * self.influence_area / edge_length_m
        )  # kN/m
        log_interaction(f"{self.edge.value}: permanent {permanent_linear_load:.2f} kN/m, variable {variable_linear_load:.2f} kN/m")
        for span in self.spans:
            span.add_load(permanent_linear_load, permanent=True)
            span.add_load(variable_linear_load, permanent=False)
