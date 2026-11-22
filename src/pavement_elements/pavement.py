from dataclasses import dataclass, field

from src.config import APP_CONFIG
from src.detailing.bar_schedule import ScheduleRow, build_schedule, schedule_table
from src.detailing.detailing_beam import DetailingBeam
from src.detailing.mark_registry import MarkRegistry
from src.detailing.quantities import (
    PavementQuantities,
    build_quantities,
    quantities_table,
)
from src.errors import DuplicateElementError, SlabPreSizingDivergedError
from src.logger import log_element, log_general, log_iteration, logger_label
from src.pavement_elements.continuous_beam import ContinuousBeam
from src.pavement_elements.pillar import Pillar
from src.pavement_elements.slab import Slab

MAX_SLAB_PRE_SIZE_PASSES = 10_000  # slab pre-sizing passes before giving up


def reset_element_id_counters() -> None:
    """Restart the auto-generated pillar, beam and slab ids at P1, V1 and L1"""
    Pillar.reset_id_counter()
    ContinuousBeam.reset_id_counter()
    Slab.reset_id_counter()


@logger_label("Pavement")
@dataclass(repr=False)
class Pavement:
    """
    Top-level container for a floor pavement structure.

    Holds pillars, continuous beams, and slabs, and enforces all connectivity rules via validate(). validate() also resolves all derived relationships (beam axes, centerlines, spans, slab↔beam links) and caches them on the elements for downstream analysis.

    Building a pavement restarts the auto-generated element ids (P1, V1, L1), so each pavement numbers its own elements independently of earlier ones.

    Attributes:
        pillars: Mapping of pillar ID → Pillar
        beams:   Mapping of beam ID → ContinuousBeam
        slabs:   Mapping of slab ID → Slab
        mark_registry: Bar marks of the last detailing, shared by all the beams
    """

    pillars: dict[str, Pillar] = field(default_factory=dict[str, Pillar])
    beams: dict[str, ContinuousBeam] = field(default_factory=dict[str, ContinuousBeam])
    slabs: dict[str, Slab] = field(default_factory=dict[str, Slab])
    mark_registry: MarkRegistry = field(default_factory=MarkRegistry, init=False)

    def __repr__(self) -> str:
        """Counts only: the elements reference each other and their results, so the
        full dataclass repr of a resolved pavement runs into gigabytes"""
        return (
            f"Pavement(pillars={len(self.pillars)}, beams={len(self.beams)}, "
            f"slabs={len(self.slabs)})"
        )

    def __post_init__(self) -> None:
        reset_element_id_counters()
        log_general("Pavement structure initialized.")

    def add_pillar(self, pillar: Pillar) -> None:
        if pillar.id in self.pillars:
            raise DuplicateElementError(kind="Pillar", element_id=pillar.id)
        self.pillars[pillar.id] = pillar
        log_element(f"Added pillar '{pillar.id}' at ({pillar.x}, {pillar.y})")

    def add_beam(self, beam: ContinuousBeam) -> None:
        if beam.id in self.beams:
            raise DuplicateElementError(kind="Beam", element_id=beam.id)
        self.beams[beam.id] = beam
        log_element(
            f"Added beam '{beam.id}' from {(beam.pillar_ids[0])} to {(beam.pillar_ids[-1])}"
        )

    def add_slab(self, slab: Slab) -> None:
        if slab.id in self.slabs:
            raise DuplicateElementError(kind="Slab", element_id=slab.id)
        self.slabs[slab.id] = slab
        log_element(
            f"Added slab '{slab.id}' between {', '.join(slab.corner_pillar_ids)}"
        )

    def validate(self) -> None:
        """
        Performs validations and resolutions for its elements (pillars, beams, slabs). Raises an InputError on any validation failure, including a pavement concrete below the minimum for the configured exposure class.
        """

        APP_CONFIG.validate_concrete_class()

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
        pre-sizes beams and slabs, transfers slab loads onto beams, dimensions
        all beams (raising the height of a beam that fails where that helps) and
        finally post-processes their bars into the detailing.
        """
        self.validate()
        self.pre_size_beams()
        self.load_beam_spans()
        self.pre_size_slabs()
        self.unload_slabs_on_beams()

        log_general("Pavement pre-processing complete. Starting beam dimensioning...")
        self.dimension_beams()
        self.detail_beams()

    def pre_size_beams(self) -> None:
        """
        Pre-sizes all beams based on the maximum span length of their spans.
        """
        log_general("Pre-sizing beams...")
        for beam in self.beams.values():
            beam.pre_size(self.pillars)

    def pre_size_slabs(self) -> None:
        """Pre-size all slabs until a full pass leaves every thickness unchanged

        A slab's thickness depends on its neighbors' (through the support conditions), so passes repeat until no slab is resized.

        Raises:
            SlabPreSizingDivergedError: If slabs are still being resized after MAX_SLAB_PRE_SIZE_PASSES passes (the sizing does not converge).
        """
        log_general("Pre-sizing slabs...")

        pass_num = 0
        stable: list[bool | None] = [None] * len(self.slabs)
        while False in stable or None in stable:
            if pass_num >= MAX_SLAB_PRE_SIZE_PASSES:
                unstable_ids = [
                    slab.id
                    for slab, is_stable in zip(self.slabs.values(), stable, strict=True)
                    if is_stable is not True
                ]
                raise SlabPreSizingDivergedError(passes=pass_num, slab_ids=unstable_ids)
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
        """Dimension every beam, raising a beam's height where a taller section solves a design failure

        See ``ContinuousBeam.dimension_raising_height``.
        """
        log_general("Beams' calculation process starting")
        for beam in self.beams.values():
            beam.dimension_raising_height(self.pillars)

    def detail_beams(self) -> None:
        """Post-process every dimensioned beam's bars into its detailing, then mark them

        The marks are numbered from N1 across the whole pavement, beam by beam, once every beam is detailed: identical bars get the same mark in any beam.

        Raises:
            BeamCalculatorError: Propagated from ContinuousBeam.detail if a beam has not been dimensioned or its post-processing fails.
        """
        log_general("Beams' detailing starting")
        detailings = [beam.detail() for beam in self.beams.values()]
        self.mark_registry = MarkRegistry()
        for detailing in detailings:
            self.mark_registry.assign(detailing)

    def bar_schedule(self) -> list[ScheduleRow]:
        """List the bar schedule of the detailed beams, one row per mark"""
        return build_schedule(self._detailings())

    def quantities(self) -> PavementQuantities:
        """Measure the net steel, concrete and formwork of the detailed beams

        The slabs and pillars are not included.
        """
        return build_quantities(self._detailings())

    def _detailings(self) -> list[DetailingBeam]:
        """Return the detailing of every detailed beam, in pavement order"""
        return [
            beam.detailing for beam in self.beams.values() if beam.detailing is not None
        ]

    def print_beam_reports(self) -> None:
        """Print the final-state report of every beam to the console, separated by a blank line

        A detailed beam's report is followed by its detailing report, and the last one by the pavement's bar schedule and quantities.

        Raises:
            EnginePreconditionError: If any beam has not been dimensioned (propagated from ContinuousBeam.report).
        """
        for beam in self.beams.values():
            print(beam.report(self.pillars))
            print()
            if beam.detailing is not None:
                print(beam.detailing.report())
                print()
        rows = self.bar_schedule()
        if rows:
            print("Bar schedule — pavement")
            print("\n".join(schedule_table(rows)))
            print()
            print("Quantities — beams only, net")
            print("\n".join(quantities_table(self.quantities())))
            print()
