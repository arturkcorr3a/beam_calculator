"""Paint a push button in a table cell and report clicks on it."""

from PySide6.QtCore import (
    QAbstractItemModel,
    QEvent,
    QModelIndex,
    QPersistentModelIndex,
    QRect,
    Signal,
)
from PySide6.QtGui import QMouseEvent, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionButton,
    QStyleOptionViewItem,
)

type _Index = QModelIndex | QPersistentModelIndex
_PADDING_PX = 3
_BUTTON_WIDTH_PX = 130


class DetailsButtonDelegate(QStyledItemDelegate):
    """Shows the cell text as a button; emits clicked(row) when it is pressed"""

    clicked = Signal(int)

    def _button_rect(self, cell: QRect) -> QRect:
        rect = cell.adjusted(_PADDING_PX, _PADDING_PX, -_PADDING_PX, -_PADDING_PX)
        rect.setWidth(min(rect.width(), _BUTTON_WIDTH_PX))
        return rect

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: _Index
    ) -> None:
        button = QStyleOptionButton()
        button.rect = self._button_rect(option.rect)  # pyright: ignore[reportAttributeAccessIssue]
        button.text = str(index.data())  # pyright: ignore[reportAttributeAccessIssue]
        button.state = QStyle.StateFlag.State_Enabled | QStyle.StateFlag.State_Raised  # pyright: ignore[reportAttributeAccessIssue]
        QApplication.style().drawControl(
            QStyle.ControlElement.CE_PushButton, button, painter
        )

    def editorEvent(
        self,
        event: QEvent,
        model: QAbstractItemModel,
        option: QStyleOptionViewItem,
        index: _Index,
    ) -> bool:
        released = event.type() == QEvent.Type.MouseButtonRelease
        if (
            released
            and isinstance(event, QMouseEvent)
            and self._button_rect(option.rect).contains(event.position().toPoint())  # pyright: ignore[reportAttributeAccessIssue]
        ):
            self.clicked.emit(index.row())
            return True
        return super().editorEvent(event, model, option, index)
