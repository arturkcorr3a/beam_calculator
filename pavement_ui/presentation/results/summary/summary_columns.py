"""Columns of the summary tables; the last columns hold the buttons ("Ver detalhamento", "Ver detalhes…")."""

from pavement_ui.core.results.beam_result import BeamResult
from pavement_ui.core.results.slab_result import SlabResult
from pavement_ui.presentation.formatting.elements import fmt_dims_cm, fmt_pillar_chain
from pavement_ui.presentation.formatting.numbers import fmt_length_cm
from pavement_ui.presentation.report.labels import height_raise_lines
from pavement_ui.presentation.results.slab.slab_texts import slab_type
from pavement_ui.presentation.text.option_labels import OptionKind, label
from pavement_ui.presentation.text.strings import results as s
from pavement_ui.presentation.widgets.column_table_model import ColumnSpec


def _beam_height(beam: BeamResult) -> str:
    """The height, marked when the design raised it past the pre-sizing"""
    value = fmt_length_cm(beam.height_cm)
    return s.HEIGHT_RAISED_MARK.format(value=value) if beam.height_raises else value


BEAM_SUMMARY: tuple[ColumnSpec[BeamResult], ...] = (
    ColumnSpec(s.COL_ID, lambda b: b.beam_id),
    ColumnSpec(s.COL_BW, lambda b: fmt_length_cm(b.width_cm), numeric=True),
    ColumnSpec(
        s.COL_H,
        _beam_height,
        numeric=True,
        tooltip=lambda b: "\n".join(height_raise_lines(b)),
    ),
    ColumnSpec(s.COL_PILLARS, lambda b: fmt_pillar_chain(b.pillar_ids)),
    ColumnSpec(s.COL_SPAN_COUNT, lambda b: str(len(b.spans)), numeric=True),
    ColumnSpec("", lambda b: s.VIEW_DETAILING),
    ColumnSpec("", lambda b: s.DETAILS),
)

SLAB_SUMMARY: tuple[ColumnSpec[SlabResult], ...] = (
    ColumnSpec(s.COL_ID, lambda r: r.slab_id),
    ColumnSpec(s.COL_H, lambda r: fmt_length_cm(r.thickness_cm), numeric=True),
    ColumnSpec(s.COL_DIMENSIONS, lambda r: fmt_dims_cm(r.lx_cm, r.ly_cm), numeric=True),
    ColumnSpec(s.COL_TYPE, slab_type),
    ColumnSpec(s.COL_USAGE, lambda r: label(OptionKind.USAGE, r.usage_key)),
    ColumnSpec("", lambda r: s.DETAILS),
)
