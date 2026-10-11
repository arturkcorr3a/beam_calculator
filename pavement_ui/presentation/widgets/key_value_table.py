"""A two-column read-only table of labeled values."""

from collections.abc import Sequence

from PySide6.QtWidgets import QWidget

from pavement_ui.presentation.widgets.column_table_model import (
    ColumnSpec,
    ColumnTableModel,
)
from pavement_ui.presentation.widgets.read_only_table import ReadOnlyTable

type KeyValue = tuple[str, str]


class KeyValueTable(ReadOnlyTable):
    """Rows of (label, value) without a header row"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        columns: tuple[ColumnSpec[KeyValue], ...] = (
            ColumnSpec("", lambda row: row[0]),
            ColumnSpec("", lambda row: row[1], numeric=True),
        )
        self._model = ColumnTableModel[KeyValue](columns, self)
        self.setModel(self._model)
        self.horizontalHeader().setVisible(False)

    def set_items(self, items: Sequence[KeyValue]) -> None:
        self._model.set_rows(items)
