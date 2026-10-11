"""Turn a pavement loaded from a file back into input records.

The engine's file format does not store beam and slab IDs, so every element is
renumbered P1…, V1…, L1… in file order and pillar references are remapped
(docs/UI_SPEC.md §6.7).
"""

from pavement_ui.core.engine.keys import m_from_cm, to_key
from pavement_ui.core.model.pavement_records import PavementRecords
from pavement_ui.core.model.records import (
    BeamRecord,
    PillarRecord,
    SlabRecord,
    WallRecord,
)
from src.pavement_elements.continuous_beam import ContinuousBeam
from src.pavement_elements.pavement import Pavement
from src.pavement_elements.pillar import Pillar
from src.pavement_elements.slab import Slab


def _pillar(pillar: Pillar, new_id: str) -> PillarRecord:
    return PillarRecord(
        new_id, m_from_cm(pillar.x), m_from_cm(pillar.y), pillar.width, pillar.depth
    )


def _beam(beam: ContinuousBeam, new_id: str, ids: dict[str, str]) -> BeamRecord:
    wall = WallRecord(
        structural=beam.wall.structural,
        masonry_key=beam.wall.masonry_type,
        nominal_thickness_cm=beam.wall.nominal_thickness,
        coating_cm=beam.wall.coating_thickness,
    )
    return BeamRecord(
        id=new_id,
        pillar_ids=tuple(ids[pid] for pid in beam.pillar_ids),
        reference_id=ids[beam.reference_pillar_id],
        width_cm=beam.width,
        alignment_key=to_key(beam.alignment),
        wall=wall,
    )


def _slab(slab: Slab, new_id: str, ids: dict[str, str]) -> SlabRecord:
    corners = tuple(ids[pid] for pid in slab.corner_pillar_ids)
    return SlabRecord(new_id, corners, slab.local, slab.lowered)


def records_from(pavement: Pavement) -> PavementRecords:
    """Build renumbered records from an unresolved, freshly loaded pavement"""
    ids = {old: f"P{n}" for n, old in enumerate(pavement.pillars, start=1)}
    return PavementRecords(
        pillars=tuple(_pillar(p, ids[p.id]) for p in pavement.pillars.values()),
        beams=tuple(
            _beam(b, f"V{n}", ids)
            for n, b in enumerate(pavement.beams.values(), start=1)
        ),
        slabs=tuple(
            _slab(s, f"L{n}", ids)
            for n, s in enumerate(pavement.slabs.values(), start=1)
        ),
    )
