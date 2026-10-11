"""A preset read-only table view: single-row selection, registration order."""

from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableView, QWidget


class ReadOnlyTable(QTableView):
    """Table with no editing and no sorting; the last column stretches"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSortingEnabled(False)
        self.setAlternatingRowColors(False)
        self.verticalHeader().setVisible(False)
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

    def selected_row(self) -> int | None:
        """Index of the selected row, or None"""
        rows = self.selectionModel().selectedRows() if self.selectionModel() else []
        return rows[0].row() if rows else None

    def select_row_index(self, row: int) -> None:
        """Select a row and scroll to it"""
        self.selectRow(row)
        self.scrollTo(self.model().index(row, 0))
