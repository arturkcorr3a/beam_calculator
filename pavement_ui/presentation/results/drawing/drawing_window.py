"""DrawingWindow: a beam's detailing sheet, with zoom and PDF and DXF downloads."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from pavement_ui.core.ports import DrawingExporter
from pavement_ui.core.results.beam_result import BeamResult
from pavement_ui.core.results.vector_drawing import VectorDrawing
from pavement_ui.presentation.results.drawing.drawing_panel import DrawingPanel
from pavement_ui.presentation.text.strings import results as s
from pavement_ui.presentation.theme import tokens

_SIZE_PX = (1280, 860)
_TITLE_STYLE = "font-size: 20px; font-weight: 600;"


class DrawingWindow(QWidget):
    """Title, the DrawingPanel (zoom, sheet, Baixar PDF…, Baixar DXF…) and Fechar"""

    def __init__(
        self,
        result: BeamResult,
        sheet: VectorDrawing,
        exporter: DrawingExporter,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setObjectName("drawingWindow")
        self.resize(*_SIZE_PX)
        self._title = QLabel()
        self._title.setStyleSheet(_TITLE_STYLE)
        self.panel = DrawingPanel(exporter)
        close = QPushButton(s.CLOSE)
        close.clicked.connect(self.close)
        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(close)
        layout = QVBoxLayout(self)
        margin = tokens.MARGIN_PX * 2
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.addWidget(self._title)
        layout.addWidget(self.panel, 1)
        layout.addLayout(footer)
        self.set_sheet(result, sheet)

    def set_sheet(self, result: BeamResult, sheet: VectorDrawing) -> None:
        """Show a beam's sheet, fitted to the window"""
        title = s.DRAWING_TITLE.format(id=result.beam_id)
        self.setWindowTitle(title)
        self._title.setText(title)
        self.panel.set_sheet(result.beam_id, sheet)
