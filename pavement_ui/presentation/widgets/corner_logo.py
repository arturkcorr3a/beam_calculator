"""A logo floating over a corner of its parent widget, ignoring the mouse."""

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QLabel, QWidget

from pavement_ui.presentation.theme.logo import logo_pixmap


class CornerLogo(QLabel):
    """Horizontal logo anchored to the top-right or bottom-right of the parent"""

    def __init__(
        self,
        parent: QWidget,
        height_px: int,
        margin_x_px: int,
        margin_y_px: int,
        bottom: bool,
    ) -> None:
        super().__init__(parent)
        self._margins = (margin_x_px, margin_y_px)
        self._bottom = bottom
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setPixmap(logo_pixmap(height_px, self.devicePixelRatioF()))
        self.adjustSize()
        parent.installEventFilter(self)
        self._place()
        self.raise_()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self._place()
            self.raise_()
        return super().eventFilter(watched, event)

    def _place(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        margin_x, margin_y = self._margins
        x = parent.width() - self.width() - margin_x
        y = parent.height() - self.height() - margin_y if self._bottom else margin_y
        self.move(x, y)
