from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

from src.pavement_elements.geometry_utils import Axis, effective_span
from src.pavement_elements.pillar import Pillar
from src.reinforcement.stirrups import Stirrups

if TYPE_CHECKING:
    from src.pavement_elements.continuous_beam import ContinuousBeam
    from src.pavement_elements.slab import Slab


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
    supported_slabs: tuple[Slab | None, Slab | None] = field(
        default_factory=lambda: (None, None), init=False
    )
    permanent_load: float = field(default=0.0, init=False)  # kN/m
    variable_load: float = field(default=0.0, init=False)  # kN/m
    characteristic_shear_force: float = field(
        default=0.0, init=False
    )  # kN, greatest |V| inside the span, set when stirrups are dimensioned
    stirrups: Stirrups = field(init=False)

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

    def get_effective_length(
        self, pillar_registry: dict[str, Pillar], height: float | None = None
    ) -> float:
        """Return the span's effective length (cm) for structural analysis

        Args:
            height: Beam height used for the 0.3 h cap (cm). Defaults to the
                beam's current height.

        References:
            ABNT NBR 6118:2014 — Section 14.6.2.4
        """
        axis = cast(Axis, self.beam.axis)
        start_pillar = pillar_registry[self.start_pillar_id]
        end_pillar = pillar_registry[self.end_pillar_id]
        return effective_span(
            self.get_length(pillar_registry),
            start_pillar.get_parallel_extent(axis),
            end_pillar.get_parallel_extent(axis),
            self.beam.height if height is None else height,
        )

    def contains_pillar(self, pillar_id: str) -> bool:
        """Checks if the span contains a specific pillar ID."""
        return pillar_id == self.start_pillar_id or pillar_id == self.end_pillar_id

    def add_supported_slab(self, slab: Slab) -> None:
        """Adds a slab to the supported_slab_ids tuple."""
        if self.supported_slabs[0] is None:
            self.supported_slabs = (slab, self.supported_slabs[1])
        elif self.supported_slabs[1] is None:
            self.supported_slabs = (self.supported_slabs[0], slab)
        else:
            raise ValueError(
                f"Span between '{self.start_pillar_id}' and '{self.end_pillar_id}' already supports two slabs."
            )

    def get_other_supported_slab(self, slab: Slab) -> Slab | None:
        """Returns the other supported slab, given one of them."""
        if self.supported_slabs[0] == slab:
            return self.supported_slabs[1]
        elif self.supported_slabs[1] == slab:
            return self.supported_slabs[0]
        else:
            raise ValueError(f"Slab '{slab.id}' is not supported by this span.")

    def add_load(self, load: float, permanent: bool = True) -> None:
        """Adds a load (kN/m) to the span's total load from slabs."""
        if permanent:
            self.permanent_load += load
        else:
            self.variable_load += load

    def set_stirrups(self, stirrups: Stirrups) -> None:
        """Sets the stirrups for this span."""
        self.stirrups = stirrups
