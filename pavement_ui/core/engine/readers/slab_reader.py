"""Read a pre-sized slab into a SlabResult."""

from typing import cast

from pavement_ui.core.engine.readers.drawing_reader import read_drawing, report_config
from pavement_ui.core.results.slab_result import (
    DeflectionCheck,
    EdgeSupport,
    FinishLoad,
    SlabResult,
)
from src.checkers.deformation_check_result import DeformationCheckResult
from src.drawing.slab_plan import build_slab_plan, build_slab_supports
from src.loading.superficial_loads import SuperficialLoads
from src.pavement_elements.pillar import Pillar
from src.pavement_elements.slab import ONE_WAY_SLAB_THRESHOLD_RATIO, Slab
from src.pavement_elements.slab_edge import Edges, SlabEdge

SLAB_FIGURE_MM = (170.0, 95.0)  # size of the slab drawings in the report
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
        influence_area_m2=edge.influence_area,
        g_kn_m=edge.permanent_linear_load,
        q_kn_m=edge.variable_linear_load,
    )


def _finishes(slab: Slab) -> tuple[FinishLoad, ...]:
    """Return the slab's permanent loads besides its own weight, leaving out empty ones."""
    loads = (
        FinishLoad(
            "top",
            slab.top_finish.material_description,
            SuperficialLoads.get_top_finish_weight(*slab.top_finish),
        ),
        FinishLoad(
            "ceiling",
            slab.ceiling_finish,
            SuperficialLoads.get_ceiling_weight(slab.ceiling_finish),
        ),
        FinishLoad(
            "infill",
            slab.infill.material_description,
            SuperficialLoads.get_infill_weight(*slab.infill),
        ),
    )
    return tuple(load for load in loads if load.kn_m2 > 0)


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


def read_slab(slab: Slab, pillars: dict[str, Pillar]) -> SlabResult:
    """Build the read model of a slab after ``Pavement.resolve``

    Args:
        pillars: The pavement's pillars, for the plan.
    """
    check = cast(DeformationCheckResult, slab.deflection_check)
    lx, ly = slab.dimensions
    lx_ef, ly_ef = slab.effective_dimensions
    config = report_config(lx, ly, *SLAB_FIGURE_MM)
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
        own_weight_kn_m2=slab.total_permanent_load - slab.permanent_load,
        finishes=_finishes(slab),
        plan=read_drawing(build_slab_plan(slab, pillars, config)),
        supports=read_drawing(build_slab_supports(slab, config)),
    )
