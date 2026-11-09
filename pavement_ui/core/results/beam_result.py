"""Read models of a dimensioned beam (pavement beam or isolated beam).

The engine dimensions stirrups per span and longitudinal bars per design point
(moment extremes), so spans and points are separate (docs/UI_SPEC.md §6.5).
"""

from dataclasses import dataclass
from enum import Enum

from pavement_ui.core.results.beam_design import (
    AnchorageEntry,
    BarEntry,
    LoadEntry,
    StirrupDesign,
)
from pavement_ui.core.results.reinforcement import BarLayer, StirrupSpec
from pavement_ui.core.results.vector_drawing import VectorDrawing


@dataclass(frozen=True, slots=True)
class SupportMark:
    """A support along the beam

    Attributes:
        position_m: Position from the beam start (m).
        label: Pillar ID, or "A"/"B" for the isolated beam.
        reaction_kn: Characteristic vertical reaction, upward positive (kN).
    """

    position_m: float
    label: str
    reaction_kn: float = 0.0


@dataclass(frozen=True, slots=True)
class SpanResult:
    """Loads, shear and stirrups of one span

    Attributes:
        index: Span number, 1…n from the beam start.
        start_label: Label of the starting support.
        end_label: Label of the ending support.
        length_m: Center-to-center length (m).
        effective_length_m: Effective (analysis) length (m).
        start_m: Span start along the beam (m).
        end_m: Span end along the beam (m).
        g_kn_m: Permanent load (kN/m).
        q_kn_m: Variable load (kN/m).
        vk_kn: Greatest characteristic shear in the span (kN).
        vsd_kn: Design shear the stirrups were dimensioned for (kN).
        loads: The loads making up g and q, by source.
        stirrup_design: Shear design of the stirrups; None when not read.
    """

    index: int
    start_label: str
    end_label: str
    length_m: float
    effective_length_m: float
    start_m: float
    end_m: float
    g_kn_m: float
    q_kn_m: float
    vk_kn: float
    vsd_kn: float
    stirrup: StirrupSpec
    loads: tuple[LoadEntry, ...] = ()
    stirrup_design: StirrupDesign | None = None


class PointKind(Enum):
    """Where a design point lies"""

    SPAN = "span"
    SUPPORT = "support"


@dataclass(frozen=True, slots=True)
class DesignPoint:
    """Longitudinal reinforcement at one design point (moment extreme)

    Attributes:
        ref: Span number ("1"…) for SPAN points; pillar ID for SUPPORT points.
        span_index: Number of the span whose stirrups apply at the point.
        position_m: Position from the beam start (m).
        mk_knm: Characteristic bending moment, positive when sagging (kN·m).
        d_cm: Effective depth (cm).
        bottom_tensioned: Whether the tensioned face is the bottom one.
        as_required_cm2: Required tensioned steel area (cm²).
        as_effective_cm2: Provided tensioned steel area (cm²).
        tension_layers: Tensioned bar layers, layer 1 first.
        compression_layers: Compressed bar layers; empty when singly reinforced.
        moment_shift_cm: Moment diagram shift a_l (cm).
        vk_kn: Characteristic shear force at the point (kN).
        y_cm: Depth of the equivalent stress block y (cm).
        y_max_cm: Largest y allowed by the ductility limit (cm).
        anchorages: Anchorage lengths of each tensioned layer, both sides.
    """

    kind: PointKind
    ref: str
    span_index: int
    position_m: float
    mk_knm: float
    d_cm: float
    bottom_tensioned: bool
    as_required_cm2: float
    as_effective_cm2: float
    tension_layers: tuple[BarLayer, ...]
    compression_layers: tuple[BarLayer, ...]
    moment_shift_cm: float
    vk_kn: float = 0.0
    y_cm: float = 0.0
    y_max_cm: float = 0.0
    anchorages: tuple[AnchorageEntry, ...] = ()


@dataclass(frozen=True, slots=True)
class DiagramSeries:
    """A sampled internal-force diagram; a repeated x marks a discontinuity

    Attributes:
        x_m: Positions from the beam start (m), non-decreasing.
        values: Force at each position (kN·m for moments, kN for shear).
    """

    x_m: tuple[float, ...]
    values: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class BeamResult:
    """Everything shown for a dimensioned beam

    Attributes:
        width_cm: Section width bw (cm).
        height_cm: Section height h (cm).
        cover_cm: Nominal concrete cover (cm).
        moment: Bending moment diagram, positive when sagging (kN·m).
        shear: Shear force diagram (kN).
        as_min_cm2: Minimum tensioned steel area of the section (cm²).
        as_max_cm2: Maximum total steel area of the section (cm²).
        outline: Elevation without reinforcement; None when not drawn.
        section: Cross section without reinforcement; None when not drawn.
        bars: Detailed longitudinal bar runs, in mark order; empty before detailing.
    """

    beam_id: str
    width_cm: float
    height_cm: float
    cover_cm: float
    supports: tuple[SupportMark, ...]
    spans: tuple[SpanResult, ...]
    points: tuple[DesignPoint, ...]
    moment: DiagramSeries
    shear: DiagramSeries
    as_min_cm2: float = 0.0
    as_max_cm2: float = 0.0
    outline: VectorDrawing | None = None
    section: VectorDrawing | None = None
    bars: tuple[BarEntry, ...] = ()

    @property
    def pillar_ids(self) -> tuple[str, ...]:
        """Support labels in order along the beam"""
        return tuple(support.label for support in self.supports)
