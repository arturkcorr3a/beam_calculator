"""Type definitions for the persisted pavement document."""

from __future__ import annotations

from typing import TypedDict


class WallDict(TypedDict):
    structural: bool
    masonry_type: str
    nominal_thickness: float
    coating_thickness: int


class PillarDict(TypedDict):
    id: str  # original id, used only as the remap key on load
    x: float
    y: float
    width: float
    depth: float


class BeamDict(TypedDict):
    pillar_ids: list[str]
    reference_pillar_id: str
    width: float
    alignment: str  # Alignment value, e.g. "bottom"
    wall: WallDict


class SlabDict(TypedDict):
    corner_pillar_ids: list[str]
    local: str
    permanent_load: float


class ConfigDict(TypedDict):
    steel: str
    default_concrete: str
    max_aggregate_size: float
    max_bar_types: int
    max_layers: int
    pavement_concrete: str
    pavement_steel: str
    building_category: str
    ceiling_height: float
    exposure_class: int
    aggregate: str


class PavementDict(TypedDict):
    pillars: list[PillarDict]
    beams: list[BeamDict]
    slabs: list[SlabDict]
