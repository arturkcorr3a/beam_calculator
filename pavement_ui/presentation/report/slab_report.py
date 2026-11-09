"""The slab report: geometry, loads, supports and yield lines, deflection check."""

from pavement_ui.core.results.slab_result import DeflectionCheck, FinishLoad, SlabResult
from pavement_ui.presentation.formatting.elements import fmt_dims_cm
from pavement_ui.presentation.formatting.numbers import fmt_number
from pavement_ui.presentation.report.painters.vector_painter import vector_figure
from pavement_ui.presentation.report.report_builder import ReportBuilder
from pavement_ui.presentation.results.slab.slab_texts import (
    cm,
    condition,
    slab_type_with_ratio,
)
from pavement_ui.presentation.text.option_labels import OptionKind, label
from pavement_ui.presentation.text.strings import report as s
from pavement_ui.presentation.text.strings import results as r

_PLAN_MM = 95.0
_SUPPORTS_MM = 95.0
_FINISH_NAMES = {
    "top": s.FINISH_TOP,
    "ceiling": s.FINISH_CEILING,
    "infill": s.FINISH_INFILL,
}


def _kn_m2(value: float) -> str:
    return fmt_number(value, 2)


def _finish_row(finish: FinishLoad) -> list[str]:
    return [
        _FINISH_NAMES.get(finish.kind, finish.kind),
        finish.description,
        _kn_m2(finish.kn_m2),
    ]


def _write_geometry(builder: ReportBuilder, result: SlabResult) -> None:
    builder.heading(s.SLAB_GEOMETRY, 2)
    if result.plan is not None:
        builder.figure(vector_figure(result.plan), _PLAN_MM, s.FIG_PLAN)
    builder.key_values(
        [
            (s.ROW_DIMENSIONS, cm_dims(result.lx_cm, result.ly_cm)),
            (s.ROW_EFFECTIVE, cm_dims(result.lx_ef_cm, result.ly_ef_cm)),
            (s.ROW_THICKNESS, cm(result.thickness_cm)),
            (s.ROW_TYPE, slab_type_with_ratio(result)),
        ]
    )


def cm_dims(lx_cm: float, ly_cm: float) -> str:
    return r.CM_VALUE.format(value=fmt_dims_cm(lx_cm, ly_cm))


def _write_loads(builder: ReportBuilder, result: SlabResult) -> None:
    builder.heading(s.SLAB_LOADS, 2)
    rows = [
        [
            s.ROW_OWN_WEIGHT,
            s.OWN_WEIGHT_DESCRIPTION.format(h=fmt_number(result.thickness_cm, 0)),
            _kn_m2(result.own_weight_kn_m2),
        ],
        *(_finish_row(finish) for finish in result.finishes),
        [s.ROW_G_TOTAL, "", _kn_m2(result.g_kn_m2)],
        [
            s.ROW_Q_USAGE,
            label(OptionKind.USAGE, result.usage_key),
            _kn_m2(result.q_kn_m2),
        ],
        [s.ROW_SERVICE, "", _kn_m2(result.service_kn_m2)],
    ]
    total_row = 1 + len(result.finishes)
    builder.table([s.COL_LOAD, s.COL_DESCRIPTION, s.COL_KN_M2], rows, 2, (total_row,))


def _write_analysis(builder: ReportBuilder, result: SlabResult) -> None:
    builder.heading(s.SLAB_ANALYSIS, 2)
    if result.supports is not None:
        builder.figure(vector_figure(result.supports), _SUPPORTS_MM, s.FIG_SUPPORTS)
    builder.paragraph(s.REACTIONS_TEXT, muted=True)
    builder.table(
        [s.COL_EDGE, s.COL_BEAM, s.COL_CONDITION, s.COL_AREA, s.COL_G, s.COL_Q],
        [
            [
                label(OptionKind.EDGE, edge.edge_key),
                edge.beam_id,
                condition(edge),
                fmt_number(edge.influence_area_m2, 2),
                fmt_number(edge.g_kn_m, 2),
                fmt_number(edge.q_kn_m, 2),
            ]
            for edge in result.edges
        ],
        3,
    )


def _write_deflection(builder: ReportBuilder, check: DeflectionCheck) -> None:
    builder.heading(s.SLAB_DEFLECTION, 2)
    moment = r.KNM_M_VALUE
    builder.key_values(
        [
            (r.ROW_H, cm(check.h_cm)),
            (r.ROW_D, cm(check.d_cm, 1)),
            (r.ROW_CASE, str(check.support_case)),
            (r.ROW_MS, moment.format(value=fmt_number(check.ms_knm_m, 2))),
            (r.ROW_MR, moment.format(value=fmt_number(check.mr_knm_m, 2))),
            (r.ROW_STAGE, r.STAGE_II if check.cracked else r.STAGE_I),
            (
                r.ROW_INERTIA,
                r.CM4_M_VALUE.format(value=fmt_number(check.inertia_eq_cm4_m, 0)),
            ),
            (r.ROW_IMMEDIATE, cm(check.immediate_deflection_cm, 2)),
            (r.ROW_LONG_TERM, cm(check.long_term_deflection_cm, 2)),
            (r.ROW_LIMIT, cm(check.limit_cm, 2)),
            (r.ROW_VERDICT, r.PASSES if check.passes else r.FAILS),
        ]
    )


def write_slab_report(
    builder: ReportBuilder, result: SlabResult, page_break: bool = False
) -> None:
    """Append a slab's report to the builder

    Args:
        page_break: Whether the report starts on a new page.
    """
    builder.heading(s.SLAB_REPORT_TITLE.format(id=result.slab_id), 1, page_break)
    _write_geometry(builder, result)
    _write_loads(builder, result)
    _write_analysis(builder, result)
    _write_deflection(builder, result.deflection)
