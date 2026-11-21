"""Input records: what the user registered, exactly as typed — no rules.

Rules (minimum sizes, pillar existence, alignment…) belong to the engine and are
checked by the engine adapters. Option keys (``*_key``) are stable engine keys:
enum member names (e.g. "CENTER") or, for masonry and usage, the engine's full
description.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PillarRecord:
    """A registered pillar

    Attributes:
        x_m: X of the section center (m).
        y_m: Y of the section center (m).
        width_cm: Section dimension along X (cm).
        depth_cm: Section dimension along Y (cm).
    """

    id: str
    x_m: float
    y_m: float
    width_cm: float
    depth_cm: float


@dataclass(frozen=True, slots=True)
class WallRecord:
    """The wall standing on a beam

    Attributes:
        masonry_key: Engine description of the masonry type.
        nominal_thickness_cm: Nominal wall thickness (cm), one of the masonry's values.
        coating_cm: Coating thickness per face (cm), one of the thickness' values.
    """

    masonry_key: str
    nominal_thickness_cm: float
    coating_cm: int


@dataclass(frozen=True, slots=True)
class BeamRecord:
    """A registered continuous beam

    Attributes:
        pillar_ids: Supporting pillar IDs, in the order typed.
        reference_id: Pillar the alignment refers to.
        width_cm: Beam width bw (cm).
        alignment_key: Engine alignment key (e.g. "CENTER").
        wall: The wall on the beam; None for a beam without wall (zero wall load).
    """

    id: str
    pillar_ids: tuple[str, ...]
    reference_id: str
    width_cm: float
    alignment_key: str
    wall: WallRecord | None


@dataclass(frozen=True, slots=True)
class SlabRecord:
    """A registered slab

    Attributes:
        corner_ids: Corner pillar IDs, in the order typed (the engine requires 4).
        usage_key: Engine description of the usage (NBR 6120 Table 10 location).
        lowered_cm: How far the slab is lowered below the floor level (cm).
    """

    id: str
    corner_ids: tuple[str, ...]
    usage_key: str
    lowered_cm: int
