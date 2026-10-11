"""Read a pre-sized slab into a SlabResult."""

from typing import cast

from pavement_ui.core.results.slab_result import (
    DeflectionCheck,
    EdgeSupport,
    SlabResult,
)
from src.checkers.deformation_check_result import DeformationCheckResult
from src.pavement_elements.slab import ONE_WAY_SLAB_THRESHOLD_RATIO, Slab
from src.pavement_elements.slab_edge import Edges, SlabEdge

_EDGE_ORDER = (Edges.TOP, Edges.BOTTOM, Edges.LEFT, Edges.RIGHT)
_KNCM_TO_KNM = 0.01  # kN·cm on the 100 cm strip → kN·m per meter
_KN_CM2_TO_KN_M2 = 10_000.0


def _neighbor_id(slab: Slab, edge: SlabEdge) -> str | None:
    """Return the slab on the other side of the edge, if any."""
    for span in edge.spans:
        other = span.get_other_supported_slab(slab)
        if other is not None:
            return other.id
    return None


def _edge(slab: Slab, edge_key: Edges) -> EdgeSupport:
    edge = slab.edges[edge_key]
    return EdgeSupport(
        edge_key=edge_key.value,
        fixed=edge.support_condition == "fixed",
        beam_id=edge.beam.id,
        neighbor_slab_id=_neighbor_id(slab, edge),
    )


def _deflection(check: DeformationCheckResult, support_case: int) -> DeflectionCheck:
    return DeflectionCheck(
        h_cm=check.height,
        d_cm=check.effective_depth,
        support_case=support_case,
        ms_knm_m=check.service_moment * _KNCM_TO_KNM,
        mr_knm_m=check.cracking_moment * _KNCM_TO_KNM,
        cracked=check.is_cracked,
        inertia_eq_cm4_m=check.equivalent_moment_of_inertia,
        immediate_deflection_cm=check.immediate_deflection,
        long_term_deflection_cm=check.long_term_deflection,
        limit_cm=check.acceptable_deflection,
        passes=check.passes,
    )


def read_slab(slab: Slab) -> SlabResult:
    """Build the read model of a slab after ``Pavement.resolve``"""
    check = cast(DeformationCheckResult, slab.deflection_check)
    lx, ly = slab.dimensions
    lx_ef, ly_ef = slab.effective_dimensions
    return SlabResult(
        slab_id=slab.id,
        thickness_cm=slab.thickness,
        lx_cm=lx,
        ly_cm=ly,
        lx_ef_cm=lx_ef,
        ly_ef_cm=ly_ef,
        two_way=not slab.is_one_way,
        one_way_ratio_limit=ONE_WAY_SLAB_THRESHOLD_RATIO,
        usage_key=slab.local,
        governing_span_cm=check.span,
        edges=tuple(_edge(slab, e) for e in _EDGE_ORDER),
        g_kn_m2=check.permanent_load,
        q_kn_m2=check.variable_load,
        service_kn_m2=check.design_load * _KN_CM2_TO_KN_M2,
        deflection=_deflection(check, cast(int, slab.deflection_support_case)),
    )
