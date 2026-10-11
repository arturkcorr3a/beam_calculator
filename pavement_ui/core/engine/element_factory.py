"""Build engine elements from input records.

Construction applies the engine's inclusion rules (``__post_init__``), so these
functions raise the engine's ValueError for a refused record.
"""

from pavement_ui.core.engine.keys import cm_from_m, from_key
from pavement_ui.core.model.records import (
    BeamRecord,
    PillarRecord,
    SlabRecord,
    WallRecord,
)
from src.pavement_elements.continuous_beam import ContinuousBeam, WallDefinition
from src.pavement_elements.geometry_utils import Alignment
from src.pavement_elements.pillar import Pillar
from src.pavement_elements.slab import Slab


def pillar(record: PillarRecord) -> Pillar:
    """Build a pillar, converting its center from m to cm"""
    return Pillar(
        cm_from_m(record.x_m),
        cm_from_m(record.y_m),
        record.width_cm,
        record.depth_cm,
        id=record.id,
    )


def wall(record: WallRecord) -> WallDefinition:
    """Build the wall definition of a beam"""
    return WallDefinition(
        structural=record.structural,
        masonry_type=record.masonry_key,
        nominal_thickness=record.nominal_thickness_cm,
        coating_thickness=record.coating_cm,
    )


def beam(record: BeamRecord) -> ContinuousBeam:
    """Build a continuous beam"""
    return ContinuousBeam(
        pillar_ids=list(record.pillar_ids),
        reference_pillar_id=record.reference_id,
        width=record.width_cm,
        alignment=from_key(Alignment, record.alignment_key),
        wall=wall(record.wall),
        id=record.id,
    )


def slab(record: SlabRecord) -> Slab:
    """Build a slab; the engine itself rejects a corner count other than 4"""
    return Slab(
        corner_pillar_ids=record.corner_ids,  # pyright: ignore[reportArgumentType]  # length is the engine's rule
        local=record.usage_key,
        lowered=record.lowered_cm,
        id=record.id,
    )
