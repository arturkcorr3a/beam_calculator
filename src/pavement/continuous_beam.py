from dataclasses import dataclass, field
from itertools import count
from typing import Optional

from src.pavement.pillar import Pillar

from src.pavement.utils import (
    TOLERANCE,
    Alignment,
    Axis,
    between,
    get_pillar_perpendicular_range,
    round_up_to_multiple_of_5,
    x_coord,
    y_coord,
)

# PAPER encontrar referência desses valores, acho que não tem na norma, mas deve ter na literatura clássica
BEAM_HEIGHT_ESTIMATION_FACTOR = 15  # for pre-dimensioning

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

# TODO merge with ContinuousBeam class in src/pavement/continuous_beam.py in some way (or reference one via the other)
@dataclass
class ContinuousBeam:

    """A structural beam spanning multiple pillars along a single axis (X or Y).

    Resolves its own axis, centerline, and width-wise pillar support from pillar_ids and reference_pillar_id via resolve_and_validate(), and exposes the resulting spans between consecutive pillars.
    """
    pillar_ids: list[str]
    reference_pillar_id: str   
    width: float
    alignment: Alignment
    height: float = 0

    id: str = field(default=None, init=False) # Auto-generated
    axis: Optional[Axis] = field(default=None, init=False)
    centerline: Optional[float] = field(default=None, init=False)
    spans: list[Span] = field(default_factory=list, init=False)

    _counter = count(1)  # Class-level counter for auto-generating IDs

    def __post_init__(self):
        self.id = f"V{next(self._counter)}"
        self.height = self.width # Start with a square section, just so it is not zero until it is calculated
        self._validate_reference_pillar()
        self._validate_pillar_count()

    
    def _validate_pillar_count(self) -> None:
        if len(self.pillar_ids) < 2:
            raise ValueError(f"Beam '{self.id}' must have at least 2 pillars.")

    def _validate_reference_pillar(self) -> None:
        """Ensures the reference pillar is included in the beam's pillar_ids."""
        if self.reference_pillar_id not in self.pillar_ids:
            raise ValueError("Reference pillar ID must be included in the beam's pillar_ids.")

    def clear_resolved(self) -> None:
        """Clears resolved attributes to force re-calculation. To be called after changes to the pavement"""
        self.axis = None
        self.centerline = None
        self.spans = []

    # PAPER encontrar referência desses valores (BEAM_HEIGHT_ESTIMATION_FACTOR), acho que não tem na norma, mas deve ter na literatura clássica (sei que é entre 12 e 15)
    def estipulate_height(self, pillar_registry: dict[str, Pillar]) -> float:
        """Pre-dimensioning height calculation."""
        max_height = 0
        for span in self.spans:
            length = span.get_length(pillar_registry)
            proposed_height = length / BEAM_HEIGHT_ESTIMATION_FACTOR
            max_height = max(max_height, proposed_height)
        self.height = round_up_to_multiple_of_5(max_height)
        return self.height

    def resolve_and_validate(self, pillar_registry: dict[str, Pillar]) -> None:
        """
        Resolves the beam's axis, centerline, and validates that all pillars support the entire beam width and no pillars are skipped.
        """
        self._validate_pillars_exist(pillar_registry)
        self._determine_axis(pillar_registry)
        self._validate_alignment()
        self._determine_centerline(pillar_registry)
        self._validate_all_pillars_support_the_whole_beam_width(pillar_registry)
        self._validate_no_skipped_pillars(pillar_registry)
        self._build_resolved_spans()

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _validate_pillars_exist(self, pillar_registry: dict[str, Pillar]) -> None:
        """Ensures all pillar_ids exist in the provided pillar_registry."""
        for pillar_id in self.pillar_ids:
            if pillar_id not in pillar_registry:
                raise ValueError(f"Beam '{self.id}': pillar '{pillar_id}' does not exist in the registry.")

    def _determine_axis(self, pillar_registry: dict[str, Pillar]) -> Axis:
        """
        Determines the axis of the beam based on the spread of its pillars and sorts the pillar IDs accordingly.
        """
        pillars = [pillar_registry[id] for id in self.pillar_ids]
        
        x_coords = [pillar.x for pillar in pillars]
        y_coords = [pillar.y for pillar in pillars]
        x_spread = max(x_coords) - min(x_coords)
        y_spread = max(y_coords) - min(y_coords)

        if x_spread >= y_spread:
            axis = Axis.X
            self.pillar_ids = [pillar.id for pillar in sorted(pillars, key=lambda pillar: pillar.x)]
        else:
            axis = Axis.Y
            self.pillar_ids = [pillar.id for pillar in sorted(pillars, key=lambda pillar: pillar.y)]

        self.axis = axis
        return axis
    
    def _validate_alignment(self) -> None:
        """Validates that the beam's alignment is compatible with its axis."""
        if self.axis is None:
            raise ValueError(f"Beam '{self.id}' has no axis set. Can't validate alignment.")
        if self.alignment is None:
            raise ValueError(f"Beam '{self.id}' has no alignment set.")
        self.alignment.validate(self.axis)

    def _determine_centerline(self, pillar_registry: dict[str, Pillar]) -> float:
        """
        Calculates the centerline coordinate (cm) of the beam based on its axis, alignment and reference pillar.
        """
        reference_pillar = pillar_registry[self.reference_pillar_id]
        if self.axis == Axis.X:
            pillar_reach = reference_pillar.get_y_range()
            match self.alignment:
                case Alignment.TOP:
                    centerline = pillar_reach[1] - self.width / 2
                case Alignment.BOTTOM:
                    centerline = pillar_reach[0] + self.width / 2
                case Alignment.CENTER:
                    centerline = reference_pillar.y
                case _:
                    raise ValueError(f"Invalid alignment for beam '{self.id}'. Alignment: '{self.alignment.value}'")
        elif self.axis == Axis.Y:
            pillar_reach = reference_pillar.get_x_range()
            match self.alignment:
                case Alignment.LEFT:
                    centerline = pillar_reach[0] + self.width / 2
                case Alignment.RIGHT:
                    centerline = pillar_reach[1] - self.width / 2
                case Alignment.CENTER:
                    centerline = reference_pillar.x
                case _:
                    raise ValueError(f"Invalid alignment for beam '{self.id}'. Alignment: '{self.alignment.value}'")
        else:
            raise ValueError(f"Beam '{self.id}' has no axis set. Can't calculate centerline.")
        self.centerline = centerline
        return centerline

    def _validate_all_pillars_support_the_whole_beam_width(self, pillar_registry: dict[str, Pillar]) -> None:
        """
        Validates that each pillar's perpendicular cross-section fully contains the beam's width band.
        """
        if self.axis is None or self.centerline is None:
            raise ValueError(f"Beam '{self.id}' has no axis or centerline set. Can't validate pillar support.")
        
        beam_low, beam_high = self._get_range()
        
        for pillar_id in self.pillar_ids:
            pillar = pillar_registry[pillar_id]
            pillar_low, pillar_high = get_pillar_perpendicular_range(pillar, self.axis)
            if pillar_low > beam_low + TOLERANCE or pillar_high < beam_high - TOLERANCE:
                raise ValueError(
                    f"Beam '{self.id}': pillar '{pillar.id}' cross-section "
                    f"[{pillar_low:.4f}, {pillar_high:.4f}] cm does not fully cover the beam "
                    f"width band [{beam_low:.4f}, {beam_high:.4f}] cm "
                )

    def _get_range(self) -> tuple[float, float]:
        """Returns the coordinates range of the beam perpendicular to its axis (min, max)."""
        beam_low = self.centerline - self.width / 2
        beam_high = self.centerline + self.width / 2
        return (beam_low, beam_high)

    def _validate_no_skipped_pillars(self, pillar_registry: dict[str, Pillar]) -> None:
        """
        Ensures no pillar on the same axis line is omitted from pillar_ids.
        """
        anchors = [pillar_registry[pillar_id] for pillar_id in self.pillar_ids]
        pillars_on_same_line = self._pillars_touching_beam(pillar_registry, axis=self.axis)

        if self.axis == Axis.X:
            pillars_on_same_line.sort(key=x_coord)
            coord_key = x_coord
            start_coord = anchors[0].x
            end_coord = anchors[-1].x
        else:
            pillars_on_same_line.sort(key=y_coord)
            coord_key = y_coord
            start_coord = anchors[0].y
            end_coord = anchors[-1].y

        beam_pillar_ids = set(self.pillar_ids)
        skipped = [
            pillar for pillar in pillars_on_same_line
            if pillar.id not in beam_pillar_ids
            and between(coord_key(pillar), start_coord, end_coord)
        ]

        if skipped:
            skipped_pillar_ids = ", ".join(f"'{pillar.id}'" for pillar in skipped)
            raise ValueError(f"Beam '{self.id}' skips pillar(s) {skipped_pillar_ids} that lie on the same  axis line between its endpoints.")

    def _pillars_touching_beam(self, pillar_registry: dict[str, Pillar], axis: Axis) -> list[Pillar]:
        """
        Finds every pillar whose position or cross-section footprint intersects the beam.
        """
        beam_low, beam_high = self._get_range()

        def touches_beam(pillar: Pillar) -> bool:
            pillar_low, pillar_high = get_pillar_perpendicular_range(pillar, axis)
            if between(pillar_low, beam_low, beam_high) or between(pillar_high, beam_low, beam_high):
                return True
            return False

        return [pillar for pillar in pillar_registry.values() if touches_beam(pillar)]

    def _build_resolved_spans(self) -> None:
        """Builds resolved_spans from the sorted pillar_ids."""
        self.spans = [
            Span(
                beam=self,
                start_pillar_id=self.pillar_ids[i],
                end_pillar_id=self.pillar_ids[i + 1],
            )
            for i in range(len(self.pillar_ids) - 1)
        ]
