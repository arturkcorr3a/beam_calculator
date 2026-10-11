"""A translucent overlay with a spinner that covers a window and blocks its input."""

from PySide6.QtCore import QEvent, QObject, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from pavement_ui.presentation.theme import tokens

_FRAME_MS = 33  # about 30 frames per second
_STEP_DEG = 12
_SPINNER_PX = 44
_SPINNER_WIDTH_PX = 5.0
_ARC_SPAN_DEG = 100
_BACKGROUND_ALPHA = 200
_TEXT_PT = 12
_TEXT_GAP_PX = 18


class BusyOverlay(QWidget):
    """Covers its parent while busy: input underneath is blocked, a spinner turns"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._covered = parent
        self.setObjectName("busyOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # swallows keys while shown
        self.setCursor(Qt.CursorShape.WaitCursor)
        self._text = ""
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.setInterval(_FRAME_MS)
        self._timer.timeout.connect(self._advance)
        parent.installEventFilter(self)
        self.hide()

    def show_busy(self, text: str) -> None:
        """Cover the parent and start the spinner"""
        self._text = text
        self.setGeometry(self._covered.rect())
        self.raise_()
        self.show()
        self.setFocus()
        self._timer.start()

    def hide_busy(self) -> None:
        self._timer.stop()
        self.hide()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self._covered and event.type() == QEvent.Type.Resize:
            self.setGeometry(self._covered.rect())
        return super().eventFilter(watched, event)

    def _advance(self) -> None:
        self._angle = (self._angle + _STEP_DEG) % 360
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        background = QColor(tokens.WINDOW_BG)
        background.setAlpha(_BACKGROUND_ALPHA)
        painter.fillRect(self.rect(), background)
        center = QRectF(self.rect()).center()
        spinner = QRectF(0, 0, _SPINNER_PX, _SPINNER_PX)
        spinner.moveCenter(center)
        track = QPen(QColor(tokens.BORDER), _SPINNER_WIDTH_PX)
        painter.setPen(track)
        painter.drawEllipse(spinner)
        arc = QPen(QColor(tokens.ACCENT), _SPINNER_WIDTH_PX)
        arc.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(arc)
        painter.drawArc(spinner, -self._angle * 16, _ARC_SPAN_DEG * 16)
        font = QFont(self.font())
        font.setPointSize(_TEXT_PT)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(tokens.TEXT))
        text_box = QRectF(
            0, spinner.bottom() + _TEXT_GAP_PX, self.width(), 2 * _TEXT_PT
        )
        painter.drawText(text_box, Qt.AlignmentFlag.AlignHCenter, self._text)
        painter.end()
