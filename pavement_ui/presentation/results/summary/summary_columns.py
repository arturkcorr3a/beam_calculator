"""Columns of the summary tables; the last column holds the "Ver detalhes…" button."""

from pavement_ui.core.results.beam_result import BeamResult
from pavement_ui.core.results.slab_result import SlabResult
from pavement_ui.presentation.formatting.elements import fmt_dims_cm, fmt_pillar_chain
from pavement_ui.presentation.formatting.numbers import fmt_length_cm
from pavement_ui.presentation.results.slab.slab_texts import slab_type
from pavement_ui.presentation.text.option_labels import OptionKind, label
from pavement_ui.presentation.text.strings import results as s
from pavement_ui.presentation.widgets.column_table_model import ColumnSpec

BEAM_SUMMARY: tuple[ColumnSpec[BeamResult], ...] = (
    ColumnSpec(s.COL_ID, lambda b: b.beam_id),
    ColumnSpec(s.COL_BW, lambda b: fmt_length_cm(b.width_cm), numeric=True),
    ColumnSpec(s.COL_H, lambda b: fmt_length_cm(b.height_cm), numeric=True),
    ColumnSpec(s.COL_PILLARS, lambda b: fmt_pillar_chain(b.pillar_ids)),
    ColumnSpec(s.COL_SPAN_COUNT, lambda b: str(len(b.spans)), numeric=True),
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
