"""The beam report: geometry, loads, analysis, design and consumption."""

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter

from pavement_ui.core.results.beam_design import LoadEntry, LoadSource
from pavement_ui.core.results.beam_result import BeamResult
from pavement_ui.core.results.materials import MaterialsInfo
from pavement_ui.core.results.outcomes import DesignSuccess
from pavement_ui.core.results.quantities import BeamQuantity
from pavement_ui.presentation.formatting.elements import fmt_pillar_chain
from pavement_ui.presentation.formatting.numbers import fmt_length_cm, fmt_number
from pavement_ui.presentation.report.beam_design_section import write_design
from pavement_ui.presentation.report.labels import span_name
from pavement_ui.presentation.report.painters.load_painter import paint_loads
from pavement_ui.presentation.report.painters.vector_painter import vector_figure
from pavement_ui.presentation.report.report_builder import Paint, ReportBuilder
from pavement_ui.presentation.results.beam.diagram_layout import (
    DiagramKind,
    diagram_geometry,
)
from pavement_ui.presentation.results.beam.diagram_painter import paint_diagram
from pavement_ui.presentation.text.option_labels import OptionKind, label
from pavement_ui.presentation.text.strings import report as s

_GEOMETRY_HEIGHT_MM = 55.0
_ELEVATION_WIDTH_MM = 125.0
_SECTION_WIDTH_MM = 40.0
_LOADS_MM = 45.0
_DIAGRAM_MM = 55.0


def _diagram(result: BeamResult, kind: DiagramKind) -> Paint:
    series = result.moment if kind is DiagramKind.MOMENT else result.shear

    def paint(painter: QPainter, rect: QRectF) -> None:
        geometry = diagram_geometry(
            series, result.supports, result.spans, kind, rect.width(), rect.height()
        )
        paint_diagram(painter, geometry, kind)

    return paint


def _loads(result: BeamResult) -> Paint:
    def paint(painter: QPainter, rect: QRectF) -> None:
        paint_loads(painter, result, rect)

    return paint


def _source(entry: LoadEntry) -> str:
    match entry.source:
        case LoadSource.OWN_WEIGHT:
            return s.SOURCE_OWN_WEIGHT
        case LoadSource.WALL:
            return s.SOURCE_WALL
        case LoadSource.SLAB:
            return s.SOURCE_SLAB.format(id=entry.source_id or "")
        case LoadSource.CUSTOM:
            return entry.source_id or s.SOURCE_CUSTOM


def _materials(materials: MaterialsInfo) -> list[tuple[str, str]]:
    return [
        (
            s.ROW_CONCRETE,
            s.CONCRETE_VALUE.format(
                name=label(OptionKind.CONCRETE, materials.concrete),
                fck=fmt_number(materials.fck_mpa, 0),
            ),
        ),
        (
            s.ROW_STEEL,
            s.STEEL_VALUE.format(
                name=label(OptionKind.STEEL, materials.steel),
                fyk=fmt_number(materials.fyk_mpa, 0),
            ),
        ),
    ]


def _write_geometry(
    builder: ReportBuilder, result: BeamResult, materials: MaterialsInfo
) -> None:
    builder.heading(s.GEOMETRY, 2)
    figures = [
        (vector_figure(drawing), width)
        for drawing, width in (
            (result.outline, _ELEVATION_WIDTH_MM),
            (result.section, _SECTION_WIDTH_MM),
        )
        if drawing is not None
    ]
    if figures:
        builder.figure_row(figures, _GEOMETRY_HEIGHT_MM, s.FIG_GEOMETRY)
    section = f"{fmt_length_cm(result.width_cm)} × {fmt_length_cm(result.height_cm)} cm"
    builder.key_values(
        [
            (s.ROW_SECTION, section),
            (s.ROW_PILLARS, fmt_pillar_chain(result.pillar_ids)),
            (s.ROW_COVER, f"{fmt_number(result.cover_cm, 1)} cm"),
            *_materials(materials),
        ]
    )


def _write_loads(builder: ReportBuilder, result: BeamResult) -> None:
    builder.heading(s.LOADS, 2)
    builder.paragraph(s.LOADS_TEXT, muted=True)
    rows: list[list[str]] = []
    totals: list[int] = []
    for span in result.spans:
        for entry in span.loads:
            rows.append(
                [
                    span_name(span),
                    _source(entry),
                    fmt_number(entry.g_kn_m, 2),
                    fmt_number(entry.q_kn_m, 2),
                ]
            )
        totals.append(len(rows))
        rows.append(
            [
                span_name(span),
                s.TOTAL,
                fmt_number(span.g_kn_m, 2),
                fmt_number(span.q_kn_m, 2),
            ]
        )
    builder.table([s.COL_SPAN, s.COL_SOURCE, s.COL_G, s.COL_Q], rows, 2, totals)
    builder.figure(_loads(result), _LOADS_MM, s.FIG_LOADS)


def _write_analysis(builder: ReportBuilder, result: BeamResult) -> None:
    builder.heading(s.ANALYSIS, 2)
    builder.paragraph(s.ANALYSIS_TEXT, muted=True)
    builder.heading(s.REACTIONS, 3)
    builder.table(
        [s.COL_SUPPORT, s.COL_X, s.COL_REACTION],
        [
            [
                support.label,
                fmt_number(support.position_m, 2),
                fmt_number(support.reaction_kn, 2),
            ]
            for support in result.supports
        ],
    )
    builder.figure(_diagram(result, DiagramKind.SHEAR), _DIAGRAM_MM, s.FIG_SHEAR)
    builder.figure(_diagram(result, DiagramKind.MOMENT), _DIAGRAM_MM, s.FIG_MOMENT)


def _write_consumption(builder: ReportBuilder, quantity: BeamQuantity) -> None:
    builder.heading(s.CONSUMPTION, 2)
    builder.paragraph(s.CONSUMPTION_TEXT, muted=True)
    builder.key_values(
        [
            (s.ROW_CONCRETE_VOLUME, f"{fmt_number(quantity.concrete_m3, 3)} m³"),
            (s.ROW_FORMWORK, f"{fmt_number(quantity.formwork_m2, 2)} m²"),
            (s.ROW_STEEL_MASS, f"{fmt_number(quantity.steel_kg, 1)} kg"),
        ]
    )


def write_beam_report(
    builder: ReportBuilder,
    result: BeamResult,
    materials: MaterialsInfo,
    quantity: BeamQuantity | None,
    page_break: bool = False,
) -> None:
    """Append a beam's report to the builder

    Args:
        quantity: The beam's net quantities; the consumption section is left
            out when None.
        page_break: Whether the report starts on a new page.
    """
    builder.heading(s.BEAM_REPORT_TITLE.format(id=result.beam_id), 1, page_break)
    _write_geometry(builder, result, materials)
    _write_loads(builder, result)
    _write_analysis(builder, result)
    write_design(builder, result, materials)
    if quantity is not None:
        _write_consumption(builder, quantity)


def beam_quantity(success: DesignSuccess, beam_id: str) -> BeamQuantity | None:
    """Return a pavement beam's net quantities, if it was detailed"""
    return next((q for q in success.quantities.beams if q.beam_id == beam_id), None)
