"""Read a dimensioned continuous beam into a BeamResult."""

from typing import cast

from pavement_ui.core.engine.keys import m_from_cm
from pavement_ui.core.engine.readers.bar_reader import read_bars
from pavement_ui.core.engine.readers.design_point_reader import read_point
from pavement_ui.core.engine.readers.diagram_sampler import sample
from pavement_ui.core.engine.readers.drawing_reader import read_drawing, report_config
from pavement_ui.core.engine.readers.reinforcement_reader import read_stirrup
from pavement_ui.core.engine.readers.skin_design_reader import read_skin_design
from pavement_ui.core.engine.readers.stirrup_design_reader import read_stirrup_design
from pavement_ui.core.results.beam_design import LoadEntry, LoadSource
from pavement_ui.core.results.beam_result import BeamResult, SpanResult, SupportMark
from pavement_ui.core.results.vector_drawing import VectorDrawing
from src.analysis.beam_analysis import BeamAnalysis
from src.drawing.layout import build_beam_drawing
from src.drawing.outline import build_beam_outline, build_beam_section
from src.drawing.sheet_info import read_sheet_info
from src.pavement_elements.beam_span import Span
from src.pavement_elements.continuous_beam import ContinuousBeam
from src.pavement_elements.pillar import Pillar
from src.structural_elements.rectangular_beam import RectangularBeam


def _supports_cm(beam: ContinuousBeam, pillars: dict[str, Pillar]) -> list[float]:
    """Cumulative effective lengths: the analysis positions of the supports (cm)."""
    positions = [0.0]
    for span in beam.spans:
        positions.append(positions[-1] + span.get_effective_length(pillars))
    return positions


def _loads(span: Span) -> tuple[LoadEntry, ...]:
    """Return the span's loads by source, in the order they were applied."""
    return tuple(
        LoadEntry(
            LoadSource(component.kind.value),
            component.source_id,
            component.permanent,
            component.variable,
        )
        for component in span.load_components
    )


ELEVATION_FIGURE_MM = (125.0, 55.0)  # size of the elevation in the report


def _drawings(
    beam: ContinuousBeam,
) -> tuple[VectorDrawing | None, VectorDrawing | None]:
    """Return the elevation and section without reinforcement; None before detailing."""
    detailing = beam.detailing
    if detailing is None:
        return None, None
    config = report_config(
        detailing.end - detailing.start, detailing.height, *ELEVATION_FIGURE_MM
    )
    return (
        read_drawing(build_beam_outline(detailing, config), config.sheet_scale),
        read_drawing(build_beam_section(detailing)),
    )


def _sheet(
    beam: ContinuousBeam, name: str | None, number: int, total: int
) -> VectorDrawing | None:
    """Return the beam's detailing sheet at 1:50 on its paper; None before detailing."""
    if beam.detailing is None:
        return None
    info = read_sheet_info(name, number, total)
    return read_drawing(build_beam_drawing(beam.detailing, sheet=info))


def _spans(
    beam: ContinuousBeam, pillars: dict[str, Pillar], supports_cm: list[float]
) -> tuple[SpanResult, ...]:
    return tuple(
        SpanResult(
            index=index,
            start_label=span.start_pillar_id,
            end_label=span.end_pillar_id,
            length_m=m_from_cm(span.get_length(pillars)),
            effective_length_m=m_from_cm(span.get_effective_length(pillars)),
            start_m=m_from_cm(supports_cm[index - 1]),
            end_m=m_from_cm(supports_cm[index]),
            g_kn_m=span.permanent_load,
            q_kn_m=span.variable_load,
            vk_kn=span.characteristic_shear_force,
            vsd_kn=span.stirrups.calculator.design_shear_force,
            stirrup=read_stirrup(span.stirrups),
            loads=_loads(span),
            stirrup_design=read_stirrup_design(span.stirrups),
            skin_design=read_skin_design(span.skin_reinforcement),
        )
        for index, span in enumerate(beam.spans, start=1)
    )


def read_beam(
    beam: ContinuousBeam,
    pillars: dict[str, Pillar],
    name: str | None = None,
    sheet_number: int = 1,
    sheet_total: int = 1,
) -> BeamResult:
    """Build the read model of a beam after ``Pavement.resolve``

    Must run while APP_CONFIG holds the design settings (the cover and the
    sheet's notes read it).

    Args:
        name: Pavement name for the detailing sheet's title block.
        sheet_number: Number of the beam's sheet among the pavement's, from 1.
        sheet_total: Number of sheets of the pavement.
    """
    supports_cm = _supports_cm(beam, pillars)
    labels = [beam.spans[0].start_pillar_id, *(s.end_pillar_id for s in beam.spans)]
    analysis = cast(BeamAnalysis, beam.analysis)
    supports = tuple(
        SupportMark(m_from_cm(x), label, analysis.reaction(x))
        for x, label in zip(supports_cm, labels, strict=True)
    )
    moment, shear = sample(analysis, supports_cm)
    first = beam.rebar_calculators[0] if beam.rebar_calculators else None
    outline, section = _drawings(beam)
    return BeamResult(
        beam_id=beam.id,
        width_cm=beam.width,
        height_cm=beam.height,
        cover_cm=RectangularBeam.nominal_covering,
        supports=supports,
        spans=_spans(beam, pillars, supports_cm),
        points=tuple(read_point(c, supports, analysis) for c in beam.rebar_calculators),
        moment=moment,
        shear=shear,
        as_min_cm2=first.min_tension_rebar_area if first else 0.0,
        as_max_cm2=first.max_rebar_area if first else 0.0,
        outline=outline,
        section=section,
        bars=read_bars(beam.detailing) if beam.detailing is not None else (),
        sheet=_sheet(beam, name, sheet_number, sheet_total),
    )
