# TODO review this as it was AI-Gen
from dataclasses import dataclass, field

from src.pavement.pillar import Pillar
from src.pavement.continuous_beam import ContinuousBeam
from src.pavement.slab import Slab


@dataclass
class Pavement:
    """
    Top-level container for a floor pavement structure.

    Holds pillars, continuous beams, and slabs, and enforces all
    connectivity rules via validate(). validate() also resolves all
    derived relationships (beam axes, centerlines, spans, slab↔beam links)
    and caches them on the elements for downstream analysis.

    Attributes:
        pillars: Mapping of pillar ID → Pillar
        beams:   Mapping of beam ID → ContinuousBeam
        slabs:   Mapping of slab ID → Slab
    """
    pillars: dict[str, Pillar] = field(default_factory=dict[str, Pillar])
    beams: dict[str, ContinuousBeam] = field(default_factory=dict[str, ContinuousBeam])
    slabs: dict[str, Slab] = field(default_factory=dict[str, Slab])

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
    # Validate & resolve
    # ------------------------------------------------------------------

    def validate(self) -> None:
        """
        Validates all connectivity rules and resolves derived relationships.
        Raises ValueError on the first violated rule with a descriptive message.
        Re-running is idempotent — all resolved state is cleared and rebuilt.

        Pass order:
          1. Clear all previously resolved state.
          2. Beams: check refs → count → axis/sort/alignment → no-skip → build spans.
          3. Slabs: check refs → rectangle → resolve supporting beams/spans.

        After a successful call, the following are populated:
          - beam.axis, beam.centerline, beam.resolved_spans
          - slab.supporting_beam_ids, slab.edge_spans
          - span.supported_slab_ids (for interior beams: both adjacent slabs)
        """
        # 1. Clear resolved state
        for beam in self.beams.values():
            beam.clear_resolved()
        for slab in self.slabs.values():
            slab.clear_resolved()

        # 2. Beam pass
        for beam in self.beams.values():
            beam.resolve_and_validate(self.pillars)

        # 3. Slab pass
        for slab in self.slabs.values():
            self._check_slab_pillar_refs(slab)
            slab.validate_rectangle(self.pillars)
            slab.resolve_supporting_beams(self.pillars, self.beams)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    # FIXME move this to slab.py
    def _check_slab_pillar_refs(self, slab: Slab) -> None:
        for pid in slab.corner_pillar_ids:
            if pid not in self.pillars:
                raise ValueError(
                    f"Slab '{slab.id}' references unknown pillar '{pid}'."
                )