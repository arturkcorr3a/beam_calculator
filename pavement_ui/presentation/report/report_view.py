"""ReportView: a report document shown as a scrollable page."""

from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget

from pavement_ui.presentation.widgets.corner_logo import CornerLogo

_LOGO_HEIGHT_PX = 32
_LOGO_MARGIN_X_PX = 24  # clears the vertical scroll bar
_LOGO_MARGIN_Y_PX = 8


class ReportView(QWidget):
    """Read-only view of a report document"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.browser = QTextBrowser()
        self.browser.setObjectName("reportBrowser")
        self.browser.setOpenLinks(False)
        self._document: QTextDocument | None = None  # the browser does not own it
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.browser)
        self._logo = CornerLogo(
            self, _LOGO_HEIGHT_PX, _LOGO_MARGIN_X_PX, _LOGO_MARGIN_Y_PX, bottom=False
        )

    @property
    def document(self) -> QTextDocument | None:
        return self._document

    def set_document(self, document: QTextDocument) -> None:
        """Show a new document, keeping the scroll position"""
        bar = self.browser.verticalScrollBar()
        position = bar.value()
        self._document = document
        self.browser.setDocument(document)
        bar.setValue(position)
