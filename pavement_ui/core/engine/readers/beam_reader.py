"""Read a dimensioned continuous beam into a BeamResult."""

from typing import cast

from pavement_ui.core.engine.keys import m_from_cm
from pavement_ui.core.engine.readers.design_point_reader import read_point
from pavement_ui.core.engine.readers.diagram_sampler import sample
from pavement_ui.core.engine.readers.reinforcement_reader import read_stirrup
from pavement_ui.core.results.beam_result import BeamResult, SpanResult, SupportMark
from src.analysis.beam_analysis import BeamAnalysis
from src.pavement_elements.continuous_beam import ContinuousBeam
from src.pavement_elements.pillar import Pillar
from src.structural_elements.rectangular_beam import RectangularBeam


def _supports_cm(beam: ContinuousBeam, pillars: dict[str, Pillar]) -> list[float]:
    """Cumulative effective lengths: the analysis positions of the supports (cm)."""
    positions = [0.0]
    for span in beam.spans:
        positions.append(positions[-1] + span.get_effective_length(pillars))
    return positions


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
        )
        for index, span in enumerate(beam.spans, start=1)
    )


def read_beam(beam: ContinuousBeam, pillars: dict[str, Pillar]) -> BeamResult:
    """Build the read model of a beam after ``Pavement.resolve``

    Must run while APP_CONFIG holds the design settings (the cover reads it).
    """
    supports_cm = _supports_cm(beam, pillars)
    labels = [beam.spans[0].start_pillar_id, *(s.end_pillar_id for s in beam.spans)]
    supports = tuple(
        SupportMark(m_from_cm(x), label)
        for x, label in zip(supports_cm, labels, strict=True)
    )
    moment, shear = sample(cast(BeamAnalysis, beam.analysis), supports_cm)
    return BeamResult(
        beam_id=beam.id,
        width_cm=beam.width,
        height_cm=beam.height,
        cover_cm=RectangularBeam.nominal_covering,
        supports=supports,
        spans=_spans(beam, pillars, supports_cm),
        points=tuple(read_point(c, supports) for c in beam.rebar_calculators),
        moment=moment,
        shear=shear,
    )
