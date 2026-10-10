"""The immutable collection of everything registered in the pavement."""

from dataclasses import dataclass
from typing import Protocol

from pavement_ui.core.model.element_kind import ElementKind
from pavement_ui.core.model.records import BeamRecord, PillarRecord, SlabRecord


class _Identified(Protocol):
    @property
    def id(self) -> str: ...


def _without[R: _Identified](items: tuple[R, ...], element_id: str) -> tuple[R, ...]:
    """Return items without the one whose id is element_id (unchanged if absent)."""
    return tuple(item for item in items if item.id != element_id)


@dataclass(frozen=True, slots=True)
class ElementCounts:
    """How many elements of each kind are registered"""

    pillars: int
    beams: int
    slabs: int

    def of(self, kind: ElementKind) -> int:
        """Return the count of one element kind"""
        match kind:
            case ElementKind.PILLAR:
                return self.pillars
            case ElementKind.BEAM:
                return self.beams
            case ElementKind.SLAB:
                return self.slabs

    @property
    def is_empty(self) -> bool:
        return self.pillars == self.beams == self.slabs == 0


@dataclass(frozen=True, slots=True)
class PavementRecords:
    """All registered records, each tuple in registration order

    Registration order is kept everywhere (listings and engine assembly), so
    the engine validates elements in the order the user entered them.
    Removing an element never removes its dependents [Manual].
    """

    pillars: tuple[PillarRecord, ...] = ()
    beams: tuple[BeamRecord, ...] = ()
    slabs: tuple[SlabRecord, ...] = ()

    def with_pillar(self, record: PillarRecord) -> PavementRecords:
        return PavementRecords((*self.pillars, record), self.beams, self.slabs)

    def with_beam(self, record: BeamRecord) -> PavementRecords:
        return PavementRecords(self.pillars, (*self.beams, record), self.slabs)

    def with_slab(self, record: SlabRecord) -> PavementRecords:
        return PavementRecords(self.pillars, self.beams, (*self.slabs, record))

    def without_pillar(self, pillar_id: str) -> PavementRecords:
        return PavementRecords(
            _without(self.pillars, pillar_id), self.beams, self.slabs
        )

    def without_beam(self, beam_id: str) -> PavementRecords:
        return PavementRecords(self.pillars, _without(self.beams, beam_id), self.slabs)

    def without_slab(self, slab_id: str) -> PavementRecords:
        return PavementRecords(self.pillars, self.beams, _without(self.slabs, slab_id))

    def counts(self) -> ElementCounts:
        return ElementCounts(len(self.pillars), len(self.beams), len(self.slabs))

    @property
    def is_empty(self) -> bool:
        return self.counts().is_empty
