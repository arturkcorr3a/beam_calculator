"""Dados da laje: usage, type, dimensions, spans and the support of each edge."""

from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QWidget

from pavement_ui.core.results.slab_result import EdgeSupport, SlabResult
from pavement_ui.presentation.formatting.elements import fmt_dims_cm
from pavement_ui.presentation.results.slab.slab_edges_widget import SlabEdgesWidget
from pavement_ui.presentation.results.slab.slab_texts import (
    cm,
    condition_with_neighbor,
    slab_type_with_ratio,
)
from pavement_ui.presentation.text.option_labels import OptionKind, label
from pavement_ui.presentation.text.strings import results as s
from pavement_ui.presentation.widgets.column_table_model import (
    ColumnSpec,
    ColumnTableModel,
)
from pavement_ui.presentation.widgets.key_value_table import KeyValueTable
from pavement_ui.presentation.widgets.read_only_table import ReadOnlyTable

EDGE_COLUMNS: tuple[ColumnSpec[EdgeSupport], ...] = (
    ColumnSpec(s.COL_EDGE, lambda e: label(OptionKind.EDGE, e.edge_key)),
    ColumnSpec(s.COL_CONDITION, condition_with_neighbor),
    ColumnSpec(s.COL_SUPPORT_BEAM, lambda e: e.beam_id),
)


class SlabDataGroup(QGroupBox):
    """Key/value data, the edges table and the edges drawing"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(s.SLAB_DATA, parent)
        self._data = KeyValueTable()
        self._data.setObjectName("slabDataTable")
        self._edges = ColumnTableModel[EdgeSupport](EDGE_COLUMNS, self)
        edges_table = ReadOnlyTable()
        edges_table.setObjectName("slabEdgesTable")
        edges_table.setModel(self._edges)
        self.drawing = SlabEdgesWidget()
        layout = QVBoxLayout(self)
        layout.addWidget(self._data)
        layout.addWidget(edges_table)
        layout.addWidget(self.drawing, 1)

    def set_result(self, result: SlabResult) -> None:
        self._data.set_items(
            [
                (s.ROW_USAGE, label(OptionKind.USAGE, result.usage_key)),
                (s.ROW_TYPE, slab_type_with_ratio(result)),
                (
                    s.ROW_DIMENSIONS,
                    s.CM_VALUE.format(value=fmt_dims_cm(result.lx_cm, result.ly_cm)),
                ),
                (
                    s.ROW_EFFECTIVE,
                    s.CM_VALUE.format(
                        value=fmt_dims_cm(result.lx_ef_cm, result.ly_ef_cm)
                    ),
                ),
                (s.ROW_GOVERNING, cm(result.governing_span_cm, 1)),
            ]
        )
        self._edges.set_rows(result.edges)
        self.drawing.set_result(result)
