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


def _beam_uses(beam: BeamRecord, pillar_id: str) -> bool:
    """Whether the beam rests on or is aligned to the pillar."""
    return pillar_id in beam.pillar_ids or beam.reference_id == pillar_id


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
    Removing a pillar also removes the beams and slabs that reference it;
    removing a beam or a slab removes nothing else.
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
        """Return the records without the pillar and the elements that reference it"""
        return PavementRecords(
            _without(self.pillars, pillar_id),
            tuple(b for b in self.beams if not _beam_uses(b, pillar_id)),
            tuple(s for s in self.slabs if pillar_id not in s.corner_ids),
        )

    def pillar_dependents(self, pillar_id: str) -> tuple[str, ...]:
        """Return the IDs of the beams, then the slabs, that reference the pillar"""
        beams = (b.id for b in self.beams if _beam_uses(b, pillar_id))
        slabs = (s.id for s in self.slabs if pillar_id in s.corner_ids)
        return (*beams, *slabs)

    def without_beam(self, beam_id: str) -> PavementRecords:
        return PavementRecords(self.pillars, _without(self.beams, beam_id), self.slabs)

    def without_slab(self, slab_id: str) -> PavementRecords:
        return PavementRecords(self.pillars, self.beams, _without(self.slabs, slab_id))

    def ids_of(self, kind: ElementKind) -> frozenset[str]:
        """Return the registered IDs of one element kind"""
        match kind:
            case ElementKind.PILLAR:
                items: tuple[_Identified, ...] = self.pillars
            case ElementKind.BEAM:
                items = self.beams
            case ElementKind.SLAB:
                items = self.slabs
        return frozenset(item.id for item in items)

    def counts(self) -> ElementCounts:
        return ElementCounts(len(self.pillars), len(self.beams), len(self.slabs))

    @property
    def is_empty(self) -> bool:
        return self.counts().is_empty
