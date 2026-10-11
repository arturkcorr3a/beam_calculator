"""A two-column read-only table of labeled values."""

from collections.abc import Sequence
from dataclasses import dataclass

from PySide6.QtWidgets import QWidget

from pavement_ui.presentation.widgets.column_table_model import (
    ColumnSpec,
    ColumnTableModel,
)
from pavement_ui.presentation.widgets.read_only_table import ReadOnlyTable


@dataclass(frozen=True, slots=True)
class KeyValue:
    """One row: a label, its formatted value and an optional value color (hex)"""

    label: str
    value: str
    color: str | None = None


_COLUMNS: tuple[ColumnSpec[KeyValue], ...] = (
    ColumnSpec("", lambda row: row.label),
    ColumnSpec(
        "",
        lambda row: row.value,
        tooltip=lambda row: row.value,
        color=lambda row: row.color,
    ),
)


class KeyValueTable(ReadOnlyTable):
    """Rows of label and value without a header row; values are plain text"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = ColumnTableModel[KeyValue](_COLUMNS, self)
        self.setModel(self._model)
        self.horizontalHeader().setVisible(False)

    def set_items(self, items: Sequence[KeyValue | tuple[str, str]]) -> None:
        self._model.set_rows(
            [item if isinstance(item, KeyValue) else KeyValue(*item) for item in items]
        )
