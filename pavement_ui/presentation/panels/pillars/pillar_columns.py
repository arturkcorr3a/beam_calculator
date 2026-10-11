"""Columns of the registered pillars table."""

from pavement_ui.core.model.records import PillarRecord
from pavement_ui.presentation.formatting.numbers import fmt_length_cm, fmt_number
from pavement_ui.presentation.text.strings import panels as s
from pavement_ui.presentation.widgets.column_table_model import ColumnSpec

PILLAR_COLUMNS: tuple[ColumnSpec[PillarRecord], ...] = (
    ColumnSpec(s.COL_ID, lambda r: r.id),
    ColumnSpec(s.COL_X, lambda r: fmt_number(r.x_m, 2), numeric=True),
    ColumnSpec(s.COL_Y, lambda r: fmt_number(r.y_m, 2), numeric=True),
    ColumnSpec(s.COL_WIDTH, lambda r: fmt_length_cm(r.width_cm), numeric=True),
    ColumnSpec(s.COL_DEPTH, lambda r: fmt_length_cm(r.depth_cm), numeric=True),
)
