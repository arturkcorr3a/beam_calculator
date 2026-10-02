from dataclasses import dataclass, field

from src.logger import log_element, log_general, log_iteration, logger_label
from src.pavement_elements.continuous_beam import ContinuousBeam
from src.pavement_elements.pillar import Pillar
from src.pavement_elements.slab import Slab


@logger_label("Pavement")
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

    def __post_init__(self) -> None:
        log_general("Pavement structure initialized.")

    def add_pillar(self, pillar: Pillar) -> None:
        if pillar.id in self.pillars:
            raise ValueError(f"Pillar '{pillar.id}' already exists.")
        self.pillars[pillar.id] = pillar
        log_element(f"Added pillar '{pillar.id}' at ({pillar.x}, {pillar.y})")

    def add_beam(self, beam: ContinuousBeam) -> None:
        if beam.id in self.beams:
            raise ValueError(f"Beam '{beam.id}' already exists.")
        self.beams[beam.id] = beam
        log_element(
            f"Added beam '{beam.id}' from {(beam.pillar_ids[0])} to {(beam.pillar_ids[-1])}"
        )

    def add_slab(self, slab: Slab) -> None:
        if slab.id in self.slabs:
            raise ValueError(f"Slab '{slab.id}' already exists.")
        self.slabs[slab.id] = slab
        log_element(
            f"Added slab '{slab.id}' between {', '.join(slab.corner_pillar_ids)}"
        )

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
        log_general("Resolving pavement beams...")
        for beam in self.beams.values():
            beam.resolve_and_validate(self.pillars)

        # 3. Slab pass
        log_general("Resolving pavement slabs...")
        for slab in self.slabs.values():
            slab.resolve_and_validate(self.pillars, self.beams)

    def resolve(self) -> None:
        """
        Main entry point for sizing the pavement. Validates the structure, then
        pre-sizes beams and slabs, transfers slab loads onto beams, and finally
        dimensions all beams.
        """
        self.validate()
        self.pre_size_beams()
        self.load_beam_spans()
        self.pre_size_slabs()
        self.unload_slabs_on_beams()

        log_general("Pavement pre-processing complete. Starting beam dimensioning...")
        self.dimension_beams()

    def pre_size_beams(self) -> None:
        """
        Pre-sizes all beams based on the maximum span length of their spans.
        """
        log_general("Pre-sizing beams...")
        for beam in self.beams.values():
            beam.pre_size(self.pillars)

    def pre_size_slabs(self) -> None:
        """
        Pre-sizes all slabs based on the maximum span length of their spans.
        """
        log_general("Pre-sizing slabs...")

        pass_num = 0
        stable: list[bool | None] = [None] * len(self.slabs)
        while False in stable or None in stable:
            pass_num += 1
            log_iteration(f"Passing {pass_num} starting...", "Slabs Pre-sizing")
            for i, slab in enumerate(self.slabs.values()):
                stable[i] = slab.pre_size(self.pillars)

            n_changed = sum(1 for is_stable in stable if is_stable is False)
            log_iteration(
                f"Passing {pass_num}: {n_changed} slab(s) resized", "Slabs Pre-sizing"
            )

        for slab in self.slabs.values():
            slab.validate_lowered()

    def load_beam_spans(self) -> None:
        """
        Loads all beams based on the loads applied to their spans.
        """
        log_general("Applying load to beam spans")
        for beam in self.beams.values():
            beam.load_spans()

    def unload_slabs_on_beams(self) -> None:
        """
        Unloads all slabs on their supporting beams, calculating the load and adding it to the supporting spans.
        """
        log_general("Unloading slabs onto beams...")
        for slab in self.slabs.values():
            slab.unload_on_supporting_spans(self.pillars)

    def dimension_beams(self) -> None:
        """
        Dimensions all beams based on the loads applied to their spans.
        """
        log_general("Beams' calculation process starting")
        for beam in self.beams.values():
            beam.dimension(self.pillars)
