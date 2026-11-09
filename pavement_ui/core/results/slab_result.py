"""Read models of a dimensioned slab and its deflection check (ELS-DEF)."""

from dataclasses import dataclass

from pavement_ui.core.results.vector_drawing import VectorDrawing


@dataclass(frozen=True, slots=True)
class EdgeSupport:
    """Support of one slab edge

    Attributes:
        edge_key: "top", "bottom", "left" or "right".
        fixed: Whether the edge is fixed (otherwise pinned).
        beam_id: Supporting beam.
        neighbor_slab_id: Slab on the other side of the edge, if any.
        influence_area_m2: Area carried by the edge, from the yield lines (m²).
        g_kn_m: Permanent load passed on to the beam (kN/m).
        q_kn_m: Variable load passed on to the beam (kN/m).
    """

    edge_key: str
    fixed: bool
    beam_id: str
    neighbor_slab_id: str | None
    influence_area_m2: float = 0.0
    g_kn_m: float = 0.0
    q_kn_m: float = 0.0


@dataclass(frozen=True, slots=True)
class FinishLoad:
    """A permanent load on the slab besides its own weight

    Attributes:
        kind: "top" (floor finish), "ceiling" or "infill".
        description: Engine description of the material.
        kn_m2: Load (kN/m²).
    """

    kind: str
    description: str
    kn_m2: float


@dataclass(frozen=True, slots=True)
class DeflectionCheck:
    """Excessive deformation verification at the final thickness

    Attributes:
        h_cm: Slab thickness (cm).
        d_cm: Effective depth (cm).
        support_case: Carvalho Quadro 7.2 support case (1–9).
        ms_knm_m: Service moment Ms (kN·m/m).
        mr_knm_m: Cracking moment Mr (kN·m/m).
        cracked: Whether Ms exceeds Mr (stage II).
        inertia_eq_cm4_m: Equivalent moment of inertia (cm⁴/m).
        immediate_deflection_cm: Immediate deflection (cm).
        long_term_deflection_cm: Total deflection at t = ∞ (cm).
        limit_cm: Limit l/250 (cm).
        passes: Whether the long-term deflection is within the limit.

    References:
        ABNT NBR 6118:2014 — Section 17.3.2
    """

    h_cm: float
    d_cm: float
    support_case: int
    ms_knm_m: float
    mr_knm_m: float
    cracked: bool
    inertia_eq_cm4_m: float
    immediate_deflection_cm: float
    long_term_deflection_cm: float
    limit_cm: float
    passes: bool


@dataclass(frozen=True, slots=True)
class SlabResult:
    """Everything shown for a dimensioned slab

    Attributes:
        thickness_cm: Pre-sized thickness h (cm).
        lx_cm: Center-to-center dimension along X between edge beams (cm).
        ly_cm: Center-to-center dimension along Y between edge beams (cm).
        lx_ef_cm: Effective span along X (cm).
        ly_ef_cm: Effective span along Y (cm).
        two_way: Whether the slab spans in two directions.
        one_way_ratio_limit: Span ratio above which a slab is one-way.
        usage_key: Engine usage description.
        governing_span_cm: Span used in the deflection check (cm).
        edges: Edge supports, in the order top, bottom, left, right.
        g_kn_m2: Permanent load, including own weight (kN/m²).
        q_kn_m2: Variable load (kN/m²).
        service_kn_m2: Quasi-permanent service load (kN/m²).
        own_weight_kn_m2: Own weight at the final thickness (kN/m²).
        finishes: Permanent loads besides the own weight; empty ones left out.
        plan: Plan with the edge beams and pillars; None when not drawn.
        supports: Supports and yield lines; None when not drawn.
    """

    slab_id: str
    thickness_cm: float
    lx_cm: float
    ly_cm: float
    lx_ef_cm: float
    ly_ef_cm: float
    two_way: bool
    one_way_ratio_limit: float
    usage_key: str
    governing_span_cm: float
    edges: tuple[EdgeSupport, ...]
    g_kn_m2: float
    q_kn_m2: float
    service_kn_m2: float
    deflection: DeflectionCheck
    own_weight_kn_m2: float = 0.0
    finishes: tuple[FinishLoad, ...] = ()
    plan: VectorDrawing | None = None
    supports: VectorDrawing | None = None
