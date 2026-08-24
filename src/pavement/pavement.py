from dataclasses import dataclass, field

from src.pavement.pillar import Pillar
from src.pavement.continuous_beam import ContinuousBeam
from src.pavement.slab import Slab


@dataclass
class Pavement:
    """
    Top-level container for a floor pavement structure.

    Holds pillars, continuous beams, and slabs, and enforces all connectivity rules via validate(). validate() also resolves all derived relationships (beam axes, centerlines, spans, slab↔beam links) and caches them on the elements for downstream analysis.

    Attributes:
        pillars: Mapping of pillar ID → Pillar
        beams:   Mapping of beam ID → ContinuousBeam
        slabs:   Mapping of slab ID → Slab
    """
    pillars: dict[str, Pillar] = field(default_factory=dict[str, Pillar])
    beams: dict[str, ContinuousBeam] = field(default_factory=dict[str, ContinuousBeam])
    slabs: dict[str, Slab] = field(default_factory=dict[str, Slab])

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

    def validate(self) -> None:
        """
        Performs validations and resolutions for its elements (pillars, beams, slabs). Raises ValueError on any validation failure.
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
            slab.resolve_and_validate(self.pillars, self.beams)
