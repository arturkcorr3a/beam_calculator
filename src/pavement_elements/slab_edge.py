from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Literal

from src.loading.combination_factors import almost_permanent_reduction_factor
from src.logger import log_interaction, log_property, logger_label

if TYPE_CHECKING:
    from src.pavement_elements.continuous_beam import ContinuousBeam, Span
    from src.pavement_elements.pillar import Pillar
    from src.pavement_elements.slab import Slab

type SupportCondition = Literal["pinned", "fixed"]

# PAPER get reference for this method of resolving support
THICKNESS_DIFFERENCE_FIXED_THRESHOLD = 2.0  # cm
FIXED_RATIO_THRESHOLD = 0.8


class Edges(StrEnum):
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
                f"Slab edge '{self.edge.value}' has no resolved supporting beam."
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
        """Resolve the support condition for this edge from the adjacent slabs

        The edge is fixed when more than 80% of its length borders a slab that is thicker, or whose thickness differs by at most 2 cm. A lowered slab is always pinned, and a lowered neighbor counts as no slab at all.

        Args:
            pillar_registry: Mapping of pillar ID to Pillar, used to measure
                span lengths.

        Raises:
            ValueError: If the edge has no supporting spans.
        """
        self.support_condition = "pinned"
        if self.slab.is_lowered:
            log_property(f"{self.edge.value}: pinned (slab lowered)")
            return

        total_length = self._length(pillar_registry)  # cm
        fixed_length = 0.0  # cm
        for span in self.spans:
            other_slab = span.get_other_supported_slab(self.slab)
            if other_slab is None or other_slab.is_lowered:
                continue
            if (
                other_slab.thickness > self.slab.thickness
                or abs(other_slab.thickness - self.slab.thickness)
                <= THICKNESS_DIFFERENCE_FIXED_THRESHOLD
            ):
                fixed_length += span.get_length(pillar_registry)

        if fixed_length / total_length > 0.8:
            self.support_condition = "fixed"
        log_property(
            f"{self.edge.value}: {self.support_condition} ({fixed_length:.0f} / {total_length:.0f} cm fixed)"
        )

    def _length(self, pillar_registry: dict[str, Pillar]) -> float:
        """Total length (cm) of the spans along this edge

        Raises:
            ValueError: If the edge has no supporting spans.
        """
        length = sum(span.get_length(pillar_registry) for span in self.spans)
        if length <= 0:
            raise ValueError(
                f"{self.label} {self.edge.value} edge has no supporting spans."
            )
        return length

    def unload_on_spans(self, pillar_registry: dict[str, Pillar]) -> None:
        """Distribute the slab's tributary load along this edge's supporting spans (kN/m)

        Raises:
            ValueError: If the edge has no supporting spans.
        """
        edge_length_m = self._length(pillar_registry) / 100
        permanent_linear_load = (
            self.slab.total_permanent_load * self.influence_area / edge_length_m
        )  # kN/m
        variable_linear_load = (
            self.slab.variable_load * self.influence_area / edge_length_m
        )  # kN/m
        psi_2 = almost_permanent_reduction_factor(self.slab.local)
        log_interaction(
            f"Unloading on {len(self.spans)} spans: permanent {permanent_linear_load:.2f} kN/m, variable {variable_linear_load:.2f} kN/m",
            f"{self.label} → {self.beam.id}",
        )
        for span in self.spans:
            span.add_load(permanent_linear_load, permanent=True)
            span.add_load(variable_linear_load, permanent=False, psi_2=psi_2)
