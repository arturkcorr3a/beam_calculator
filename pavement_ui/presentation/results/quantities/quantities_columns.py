"""Columns of the quantities tables."""

from pavement_ui.core.results.quantities import (
    BeamQuantity,
    ScheduleEntry,
    SteelByDiameter,
)
from pavement_ui.presentation.formatting.numbers import fmt_number
from pavement_ui.presentation.formatting.reinforcement import fmt_bar_diameter
from pavement_ui.presentation.text.strings import results as s
from pavement_ui.presentation.widgets.column_table_model import ColumnSpec

_KIND_LABELS = {"bar": s.KIND_BAR, "clamp": s.KIND_CLAMP, "stirrup": s.KIND_STIRRUP}

STEEL_COLUMNS: tuple[ColumnSpec[SteelByDiameter], ...] = (
    ColumnSpec(s.COL_DIAMETER, lambda r: fmt_bar_diameter(r.diameter_mm), numeric=True),
    ColumnSpec(s.COL_LENGTH_M, lambda r: fmt_number(r.length_m, 2), numeric=True),
    ColumnSpec(s.COL_MASS, lambda r: fmt_number(r.mass_kg, 1), numeric=True),
)

BEAM_COLUMNS: tuple[ColumnSpec[BeamQuantity], ...] = (
    ColumnSpec(s.COL_ID, lambda r: r.beam_id),
    ColumnSpec(s.COL_STEEL, lambda r: fmt_number(r.steel_kg, 1), numeric=True),
    ColumnSpec(s.COL_CONCRETE, lambda r: fmt_number(r.concrete_m3, 2), numeric=True),
    ColumnSpec(s.COL_FORMWORK, lambda r: fmt_number(r.formwork_m2, 2), numeric=True),
)

SCHEDULE_COLUMNS: tuple[ColumnSpec[ScheduleEntry], ...] = (
    ColumnSpec(s.COL_MARK, lambda r: r.mark),
    ColumnSpec(s.COL_KIND, lambda r: _KIND_LABELS[r.kind_key]),
    ColumnSpec(s.COL_DIAMETER, lambda r: fmt_bar_diameter(r.diameter_mm), numeric=True),
    ColumnSpec(s.COL_QUANTITY, lambda r: fmt_number(r.quantity, 0), numeric=True),
    ColumnSpec(s.COL_UNIT, lambda r: fmt_number(r.unit_length_cm, 0), numeric=True),
    ColumnSpec(s.COL_TOTAL, lambda r: fmt_number(r.total_length_cm, 0), numeric=True),
)
