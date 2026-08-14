from __future__ import annotations

from dataclasses import dataclass, field

from src.pavement.pillar import Pillar
from src.pavement.continuous_beam import ContinuousBeam
from src.pavement.slab import Slab

# FIXME This was AI-generated code to make the UI work, improve it
@dataclass
class Pavement:
    """
    Top-level container for a floor pavement structure.

    Holds pillars, continuous beams, and slabs, and enforces all
    connectivity rules via validate().

    Attributes:
        pillars: Mapping of pillar ID → Pillar
        beams: Mapping of beam ID → ContinuousBeam
        slabs: Mapping of slab ID → Slab
    """
    pillars: dict[str, Pillar] = field(default_factory=dict)
    beams: dict[str, ContinuousBeam] = field(default_factory=dict)
    slabs: dict[str, Slab] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Builder helpers
    # ------------------------------------------------------------------

    def add_pillar(self, pillar: Pillar) -> None:
        if pillar.id in self.pillars:
            raise ValueError(f"Pillar '{pillar.id}' already exists.")
        self.pillars[pillar.id] = pillar

    def add_beam(self, beam: ContinuousBeam) -> None:
        if beam.id in self.beams:
            raise ValueError(f"Beam '{beam.id}' already exists.")
        self.beams[beam.id] = beam

    def add_slab(self, slab: Slab) -> None:
        if slab.id in self.slabs:
            raise ValueError(f"Slab '{slab.id}' already exists.")
        self.slabs[slab.id] = slab

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> None:
        """
        Validates all connectivity rules for the pavement. Raises ValueError
        on the first violated rule with a descriptive message.

        Rules enforced:
          1. Every pillar ID referenced by a beam exists.
          2. Every beam has ≥2 pillars.
          3. All pillars in a beam are collinear (same x or same y).
             pillar_ids are sorted by coordinate as a side effect.
          4. No intermediate pillar on the axis line is skipped.
          5. Every pillar ID referenced by a slab exists.
          6. The 4 slab corners form an axis-aligned rectangle.
          7. All 4 perimeter beams of each slab exist.
        """
        for beam in self.beams.values():
            self._check_beam_pillar_refs(beam)
            beam.validate_pillar_count()
            beam.sort_and_validate_collinearity(self.pillars)
            beam.validate_no_skipped_pillars(self.pillars)

        for slab in self.slabs.values():
            self._check_slab_pillar_refs(slab)
            slab.validate_rectangle(self.pillars)
            slab.validate_perimeter_beams(self.pillars, self.beams)

    def _check_beam_pillar_refs(self, beam: ContinuousBeam) -> None:
        for pid in beam.pillar_ids:
            if pid not in self.pillars:
                raise ValueError(
                    f"Beam '{beam.id}' references unknown pillar '{pid}'."
                )

    def _check_slab_pillar_refs(self, slab: Slab) -> None:
        for pid in slab.corner_pillar_ids:
            if pid not in self.pillars:
                raise ValueError(
                    f"Slab '{slab.id}' references unknown pillar '{pid}'."
                )
