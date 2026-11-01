"""The two beam result tables: spans (loads, shear, stirrups) and design points."""

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from pavement_ui.core.results.beam_result import BeamResult, DesignPoint, SpanResult
from pavement_ui.presentation.formatting.elements import (
    fmt_pillar_chain,
    fmt_point_label,
)
from pavement_ui.presentation.formatting.numbers import fmt_number, fmt_signed
from pavement_ui.presentation.formatting.reinforcement import (
    fmt_clamps_cell,
    fmt_hooks_cell,
    fmt_stirrup,
    fmt_tension_cell,
)
from pavement_ui.presentation.text.strings import results as s
from pavement_ui.presentation.widgets.column_table_model import (
    ColumnSpec,
    ColumnTableModel,
)
from pavement_ui.presentation.widgets.read_only_table import ReadOnlyTable

SPAN_COLUMNS: tuple[ColumnSpec[SpanResult], ...] = (
    ColumnSpec(s.COL_SPAN, lambda r: str(r.index)),
    ColumnSpec(s.COL_STRETCH, lambda r: fmt_pillar_chain((r.start_label, r.end_label))),
    ColumnSpec(s.COL_LENGTH, lambda r: fmt_number(r.length_m, 2), numeric=True),
    ColumnSpec(
        s.COL_EFFECTIVE, lambda r: fmt_number(r.effective_length_m, 2), numeric=True
    ),
    ColumnSpec(s.COL_G, lambda r: fmt_number(r.g_kn_m, 2), numeric=True),
    ColumnSpec(s.COL_Q, lambda r: fmt_number(r.q_kn_m, 2), numeric=True),
    ColumnSpec(s.COL_VK, lambda r: fmt_number(r.vk_kn, 1), numeric=True),
    ColumnSpec(s.COL_VSD, lambda r: fmt_number(r.vsd_kn, 1), numeric=True),
    ColumnSpec(s.COL_STIRRUPS, lambda r: fmt_stirrup(r.stirrup)),
)

POINT_COLUMNS: tuple[ColumnSpec[DesignPoint], ...] = (
    ColumnSpec(s.COL_POINT, fmt_point_label),
    ColumnSpec(s.COL_X, lambda p: fmt_number(p.position_m, 2), numeric=True),
    ColumnSpec(s.COL_MK, lambda p: fmt_signed(p.mk_knm, 1), numeric=True),
    ColumnSpec(s.COL_D, lambda p: fmt_number(p.d_cm, 1), numeric=True),
    ColumnSpec(s.COL_AS_REQ, lambda p: fmt_number(p.as_required_cm2, 2), numeric=True),
    ColumnSpec(s.COL_AS_EF, lambda p: fmt_number(p.as_effective_cm2, 2), numeric=True),
    ColumnSpec(s.COL_TENSION, lambda p: fmt_tension_cell(p.tension_layers)),
    ColumnSpec(s.COL_COMPRESSION, lambda p: fmt_tension_cell(p.compression_layers)),
    ColumnSpec(
        s.COL_HOOKS,
        lambda p: fmt_hooks_cell(p.tension_layers, p.compression_layers),
    ),
    ColumnSpec(
        s.COL_CLAMPS,
        lambda p: fmt_clamps_cell(p.tension_layers, p.compression_layers),
    ),
)


class BeamTables(QWidget):
    """Spans table above the design points table, each with a bold title"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._spans = ColumnTableModel[SpanResult](SPAN_COLUMNS, self)
        self._points = ColumnTableModel[DesignPoint](POINT_COLUMNS, self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        for title, model, name in (
            (s.SPANS_TABLE, self._spans, "beamSpansTable"),
            (s.POINTS_TABLE, self._points, "beamPointsTable"),
        ):
            table = ReadOnlyTable()
            table.setObjectName(name)
            table.setModel(model)
            layout.addWidget(QLabel(f"<b>{title}</b>"))
            layout.addWidget(table, 1)

    def set_result(self, result: BeamResult) -> None:
        self._spans.set_rows(result.spans)
        self._points.set_rows(result.points)
