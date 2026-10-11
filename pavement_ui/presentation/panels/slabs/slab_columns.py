"""Columns of the registered slabs table."""

from pavement_ui.core.model.records import SlabRecord
from pavement_ui.presentation.text.option_labels import OptionKind, label
from pavement_ui.presentation.text.strings import panels as s
from pavement_ui.presentation.widgets.column_table_model import ColumnSpec

SLAB_COLUMNS: tuple[ColumnSpec[SlabRecord], ...] = (
    ColumnSpec(s.COL_ID, lambda r: r.id),
    ColumnSpec(s.COL_CORNERS, lambda r: s.PILLAR_LIST_JOIN.join(r.corner_ids)),
    ColumnSpec(s.COL_USAGE, lambda r: label(OptionKind.USAGE, r.usage_key)),
    ColumnSpec(s.COL_LOWERED, lambda r: str(r.lowered_cm), numeric=True),
)
