"""Serialize pavement domain objects into plain, YAML-ready dicts.

Only construction inputs are emitted;
"""

from __future__ import annotations

from src.config import AppConfig
from src.pavement.continuous_beam import ContinuousBeam, WallDefinition
from src.pavement.pavement import Pavement
from src.pavement.pillar import Pillar
from src.pavement.slab import Slab
from src.persistency.schema import (
    BeamDict,
    ConfigDict,
    PavementDict,
    PillarDict,
    SlabDict,
    WallDict,
)


def _wall_to_dict(wall: WallDefinition) -> WallDict:
    """Serializes a wall definition to a plain dict.

    Args:
        wall: The wall definition to serialize.

    Returns:
        A dict with the wall's structural flag, masonry type, nominal thickness (cm) and coating thickness (cm).
    """
    return {
        "structural": wall.structural,
        "masonry_type": wall.masonry_type,
        "nominal_thickness": wall.nominal_thickness,
        "coating_thickness": wall.coating_thickness,
    }


def _pillar_to_dict(pillar: Pillar) -> PillarDict:
    """Serializes a pillar to a plain dict.

    Args:
        pillar: The pillar to serialize.

    Returns:
        A dict with the pillar's id and its position/section dimensions (cm).
    """
    return {
        "id": pillar.id,
        "x": pillar.x,
        "y": pillar.y,
        "width": pillar.width,
        "depth": pillar.depth,
    }


def _beam_to_dict(beam: ContinuousBeam) -> BeamDict:
    """Serializes a continuous beam to a plain dict.

    Only construction inputs are emitted; the resolved height, axis, centerline
    and spans are omitted because they are recomputed on resolve.

    Args:
        beam: The continuous beam to serialize.

    Returns:
        A dict with the beam's pillar ids, reference pillar id, width (cm), alignment value and nested wall.
    """
    return {
        "pillar_ids": list(beam.pillar_ids),
        "reference_pillar_id": beam.reference_pillar_id,
        "width": beam.width,
        "alignment": beam.alignment.value,
        "wall": _wall_to_dict(beam.wall),
    }


def _slab_to_dict(slab: Slab) -> SlabDict:
    """Serializes a slab to a plain dict.

    The variable load and thickness are omitted because they are derived from
    the usage and resolved during sizing.

    Args:
        slab: The slab to serialize.

    Returns:
        A dict with the slab's corner pillar ids, usage local and permanent load (kN/m²).
    """
    return {
        "corner_pillar_ids": list(slab.corner_pillar_ids),
        "local": slab.local,
        "permanent_load": slab.permanent_load,
    }


def pavement_to_dict(pavement: Pavement) -> PavementDict:
    """Serializes a pavement to a plain, YAML-ready dict.

    Elements are emitted in insertion order, which is the order they are
    replayed on load.

    Args:
        pavement: The pavement to serialize.

    Returns:
        A dict holding the pavement's pillars, beams and slabs.
    """
    return {
        "pillars": [_pillar_to_dict(p) for p in pavement.pillars.values()],
        "beams": [_beam_to_dict(b) for b in pavement.beams.values()],
        "slabs": [_slab_to_dict(s) for s in pavement.slabs.values()],
    }


def config_to_dict(config: AppConfig) -> ConfigDict:
    """Serializes an AppConfig to a plain, YAML-ready dict.

    Args:
        config: The config to serialize.

    Returns:
        A dict holding all AppConfig fields.
    """
    return {
        "steel": config.steel,
        "default_concrete": config.default_concrete,
        "max_aggregate_size": config.max_aggregate_size,
        "max_bar_types": config.max_bar_types,
        "max_layers": config.max_layers,
        "pavement_concrete": config.pavement_concrete,
        "pavement_steel": config.pavement_steel,
        "building_category": config.building_category,
        "ceiling_height": config.ceiling_height,
        "exposure_class": config.exposure_class,
        "aggregate": config.aggregate,
    }
