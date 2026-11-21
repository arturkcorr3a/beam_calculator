"""A checkable list of the registered pillars."""

from collections.abc import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget

from pavement_ui.core.model.records import PillarRecord
from pavement_ui.presentation.formatting.numbers import fmt_number
from pavement_ui.presentation.text.strings import panels as s

_VISIBLE_ROWS = 5
_ROW_PADDING_PX = 8


class PillarChecklist(QListWidget):
    """Pick pillars among the registered ones, shown by ID and position

    Args:
        max_checked: How many pillars can be checked; once reached, the
            unchecked ones are disabled. None for no limit.

    Signals:
        checked_changed: The set of checked pillars changed.
    """

    checked_changed = Signal()

    def __init__(
        self, max_checked: int | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._max_checked = max_checked
        self.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        row_px = self.fontMetrics().height() + _ROW_PADDING_PX
        self.setMaximumHeight(_VISIBLE_ROWS * row_px + 2 * self.frameWidth())
        self.itemChanged.connect(self._on_item_changed)

    def set_pillars(self, pillars: Sequence[PillarRecord]) -> None:
        """Show these pillars in registration order

        Pillars that are still present keep their check; removed ones lose it.
        """
        kept = set(self.checked_ids())
        self.blockSignals(True)
        self.clear()
        for pillar in pillars:
            item = QListWidgetItem(
                s.PILLAR_CHOICE.format(
                    id=pillar.id,
                    x=fmt_number(pillar.x_m, 2),
                    y=fmt_number(pillar.y_m, 2),
                )
            )
            item.setData(Qt.ItemDataRole.UserRole, pillar.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            checked = pillar.id in kept
            item.setCheckState(
                Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
            )
            self.addItem(item)
        self._apply_limit()
        self.blockSignals(False)
        self.checked_changed.emit()

    def checked_ids(self) -> tuple[str, ...]:
        """IDs of the checked pillars, in registration order"""
        return tuple(
            item.data(Qt.ItemDataRole.UserRole)
            for item in self._items()
            if item.checkState() == Qt.CheckState.Checked
        )

    def _items(self) -> list[QListWidgetItem]:
        return [self.item(row) for row in range(self.count())]

    def _on_item_changed(self) -> None:
        self.blockSignals(True)
        self._apply_limit()
        self.blockSignals(False)
        self.checked_changed.emit()

    def _apply_limit(self) -> None:
        full = (
            self._max_checked is not None
            and len(self.checked_ids()) >= self._max_checked
        )
        for item in self._items():
            enabled = not full or item.checkState() == Qt.CheckState.Checked
            flags = item.flags()
            item.setFlags(
                flags | Qt.ItemFlag.ItemIsEnabled
                if enabled
                else flags & ~Qt.ItemFlag.ItemIsEnabled
            )
