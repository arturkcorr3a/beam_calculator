"""Columns of the registered beams table."""

from pavement_ui.core.model.records import BeamRecord
from pavement_ui.presentation.formatting.numbers import fmt_length_cm
from pavement_ui.presentation.text.option_labels import OptionKind, label, short_label
from pavement_ui.presentation.text.strings import panels as s
from pavement_ui.presentation.widgets.column_table_model import ColumnSpec


def _wall_cell(record: BeamRecord) -> str:
    wall = record.wall
    return s.WALL_CELL.format(
        masonry=short_label(OptionKind.MASONRY, wall.masonry_key),
        thickness=fmt_length_cm(wall.nominal_thickness_cm),
    )


def _wall_tooltip(record: BeamRecord) -> str:
    wall = record.wall
    return s.WALL_TOOLTIP.format(
        masonry=label(OptionKind.MASONRY, wall.masonry_key),
        thickness=fmt_length_cm(wall.nominal_thickness_cm),
        coating=wall.coating_cm,
    )


BEAM_COLUMNS: tuple[ColumnSpec[BeamRecord], ...] = (
    ColumnSpec(s.COL_ID, lambda r: r.id),
    ColumnSpec(s.COL_PILLARS, lambda r: s.PILLAR_LIST_JOIN.join(r.pillar_ids)),
    ColumnSpec(s.COL_REFERENCE, lambda r: r.reference_id),
    ColumnSpec(s.COL_BW, lambda r: fmt_length_cm(r.width_cm), numeric=True),
    ColumnSpec(
        s.COL_ALIGNMENT, lambda r: short_label(OptionKind.ALIGNMENT, r.alignment_key)
    ),
    ColumnSpec(s.COL_WALL, _wall_cell, tooltip=_wall_tooltip),
)
