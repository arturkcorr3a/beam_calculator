"""Section 4 of the beam report: properties, points, bending, anchorage, stirrups, skin bars."""

from pavement_ui.core.results.beam_result import BeamResult
from pavement_ui.core.results.materials import MaterialsInfo
from pavement_ui.presentation.formatting.elements import fmt_point_label
from pavement_ui.presentation.formatting.numbers import fmt_number
from pavement_ui.presentation.formatting.reinforcement import (
    fmt_skin,
    fmt_stirrup,
    fmt_tension_cell,
)
from pavement_ui.presentation.report.bars_section import write_bars
from pavement_ui.presentation.report.labels import span_name
from pavement_ui.presentation.report.report_builder import ReportBuilder
from pavement_ui.presentation.text.strings import report as s

_CM2_M_PER_CM2_CM = 100.0


def _mpa(value: float, decimals: int = 2) -> str:
    return f"{fmt_number(value, decimals)} MPa"


def _ratio(value_cm2_cm: float) -> str:
    return fmt_number(value_cm2_cm * _CM2_M_PER_CM2_CM, 2)


def _write_properties(
    builder: ReportBuilder, result: BeamResult, materials: MaterialsInfo
) -> None:
    builder.heading(s.PROPERTIES, 3)
    builder.key_values(
        [
            (s.ROW_FCD, _mpa(materials.fcd_mpa)),
            (s.ROW_FCTM, _mpa(materials.fctm_mpa)),
            (s.ROW_FCTD, _mpa(materials.fctd_mpa)),
            (s.ROW_ECS, _mpa(materials.ecs_mpa, 0)),
            (s.ROW_FYD, _mpa(materials.fyd_mpa)),
            (s.ROW_FYWD, _mpa(materials.fywd_mpa)),
            (s.ROW_AS_MIN, f"{fmt_number(result.as_min_cm2, 2)} cm²"),
            (s.ROW_AS_MAX, f"{fmt_number(result.as_max_cm2, 2)} cm²"),
        ]
    )


def _write_points(builder: ReportBuilder, result: BeamResult) -> None:
    builder.heading(s.POINTS, 3)
    builder.table(
        [s.COL_POINT, s.COL_X, s.COL_VK, s.COL_MK, s.COL_D],
        [
            [
                fmt_point_label(p),
                fmt_number(p.position_m, 2),
                fmt_number(p.vk_kn, 2),
                fmt_number(p.mk_knm, 2),
                fmt_number(p.d_cm, 1),
            ]
            for p in result.points
        ],
    )


def _write_bending(builder: ReportBuilder, result: BeamResult) -> None:
    builder.heading(s.BENDING, 3)
    builder.table(
        [
            s.COL_POINT,
            s.COL_Y,
            s.COL_Y_MAX,
            s.COL_AS_REQ,
            s.COL_TENSION,
            s.COL_AS_EF,
            s.COL_COMPRESSION,
        ],
        [
            [
                fmt_point_label(p),
                fmt_number(p.y_cm, 2),
                fmt_number(p.y_max_cm, 2),
                fmt_number(p.as_required_cm2, 2),
                fmt_tension_cell(p.tension_layers),
                fmt_number(p.as_effective_cm2, 2),
                fmt_tension_cell(p.compression_layers),
            ]
            for p in result.points
        ],
    )


def _write_anchorage(builder: ReportBuilder, result: BeamResult) -> None:
    builder.heading(s.ANCHORAGE, 3)
    rows: list[list[str]] = []
    for point in result.points:
        for entry in point.anchorages:
            rows.append(
                [
                    fmt_point_label(point),
                    fmt_number(point.moment_shift_cm, 1),
                    str(entry.layer),
                    s.LEFT if entry.left else s.RIGHT,
                    fmt_number(entry.lb_cm, 1),
                    fmt_number(entry.lb_nec_cm, 1),
                ]
            )
    builder.table(
        [s.COL_POINT, s.COL_SHIFT, s.COL_LAYER, s.COL_SIDE, s.COL_LB, s.COL_LB_NEC],
        rows,
    )


def _write_stirrups(builder: ReportBuilder, result: BeamResult) -> None:
    builder.heading(s.STIRRUPS, 3)
    rows: list[list[str]] = []
    for span in result.spans:
        design = span.stirrup_design
        if design is None:
            continue
        rows.append(
            [
                span_name(span),
                fmt_number(design.d_cm, 1),
                fmt_number(design.vsd_kn, 2),
                fmt_number(design.vrd2_kn, 1),
                fmt_number(design.vc_kn, 2),
                fmt_number(design.vsw_kn, 2),
                _ratio(design.required_ratio_cm2_cm),
                _ratio(design.min_ratio_cm2_cm),
                fmt_stirrup(span.stirrup.at(span.start_m)),
                _ratio(design.provided_ratio_cm2_cm),
                fmt_number(design.max_spacing_cm, 1),
            ]
        )
    builder.table(
        [
            s.COL_SPAN,
            s.COL_D,
            s.COL_VSD,
            s.COL_VRD2,
            s.COL_VC,
            s.COL_VSW,
            s.COL_RATIO_REQ,
            s.COL_RATIO_MIN,
            s.COL_STIRRUP,
            s.COL_RATIO_EF,
            s.COL_S_MAX,
        ],
        rows,
    )
    builder.heading(s.STIRRUP_ZONES, 3)
    zone_rows = [
        [
            span_name(span),
            s.STRETCH.format(
                start=fmt_number(zone.start_m, 2), end=fmt_number(zone.end_m, 2)
            ),
            fmt_number(zone.spacing_cm, 1),
        ]
        for span in result.spans
        for zone in span.stirrup.zones
    ]
    builder.table([s.COL_SPAN, s.COL_STRETCH, s.COL_SPACING], zone_rows, 2)


def _write_skin(builder: ReportBuilder, result: BeamResult) -> None:
    builder.heading(s.SKIN, 3)
    spans = [span for span in result.spans if span.skin_design is not None]
    if not spans:
        builder.paragraph(s.SKIN_NOT_REQUIRED, muted=True)
        return
    builder.paragraph(s.SKIN_TEXT, muted=True)
    rows: list[list[str]] = []
    for span in spans:
        design = span.skin_design
        assert design is not None  # filtered above
        rows.append(
            [
                span_name(span),
                fmt_number(design.required_area_cm2, 2),
                fmt_skin(design),
                fmt_number(design.provided_area_cm2, 2),
                s.STRETCH.format(
                    start=fmt_number(design.band_start_cm, 1),
                    end=fmt_number(design.band_end_cm, 1),
                ),
            ]
        )
    builder.table(
        [
            s.COL_SPAN,
            s.COL_SKIN_REQ,
            s.COL_SKIN_BARS,
            s.COL_SKIN_EF,
            s.COL_SKIN_BAND,
        ],
        rows,
    )


def write_design(
    builder: ReportBuilder, result: BeamResult, materials: MaterialsInfo
) -> None:
    """Append the design section: final values only, no iterations"""
    builder.heading(s.DESIGN, 2)
    _write_properties(builder, result, materials)
    _write_points(builder, result)
    _write_bending(builder, result)
    _write_anchorage(builder, result)
    _write_stirrups(builder, result)
    _write_skin(builder, result)
    write_bars(builder, result.bars)
