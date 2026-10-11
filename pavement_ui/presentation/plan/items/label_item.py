"""A text label with a fixed pixel size that the Y-up plan never flips."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter
from PySide6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

from pavement_ui.presentation.theme import tokens

_Align = Qt.AlignmentFlag


class LabelItem(QGraphicsItem):
    """Text anchored at its position, drawn in screen pixels

    With ``ItemIgnoresTransformations`` the item's local coordinates are pixels
    with Y down, whatever the zoom or the plan's Y-up flip.

    Args:
        anchor: Which side of the text sits at the position (e.g. AlignLeft |
            AlignBottom puts the text above-right of it).
        offset_px: Extra shift (dx, dy) in pixels, Y down.
    """

    def __init__(  # noqa: PLR0913 — one parameter per visual property
        self,
        text: str,
        point_size: float,
        bold: bool = False,
        anchor: _Align = _Align.AlignCenter,
        offset_px: tuple[float, float] = (0.0, 0.0),
        parent: QGraphicsItem | None = None,
    ) -> None:
        super().__init__(parent)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self._text = text
        self._font = QFont()
        self._font.setPointSizeF(point_size)
        self._font.setBold(bold)
        self._color = QColor(tokens.TEXT)
        self._rect = self._text_rect(anchor, offset_px)

    def _text_rect(self, anchor: _Align, offset_px: tuple[float, float]) -> QRectF:
        size = QFontMetricsF(self._font).size(0, self._text)
        x = -size.width() / 2
        if anchor & _Align.AlignLeft:
            x = 0.0
        elif anchor & _Align.AlignRight:
            x = -size.width()
        y = -size.height() / 2
        if anchor & _Align.AlignTop:
            y = 0.0
        elif anchor & _Align.AlignBottom:
            y = -size.height()
        return QRectF(QPointF(x + offset_px[0], y + offset_px[1]), size)

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def boundingRect(self) -> QRectF:
        return self._rect

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        painter.setFont(self._font)
        painter.setPen(self._color)
        painter.drawText(self._rect, _Align.AlignCenter, self._text)
