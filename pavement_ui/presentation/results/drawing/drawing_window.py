"""DrawingWindow: a beam's detailing sheet, with zoom and PDF and DXF downloads."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from pavement_ui.core.ports import DrawingExporter
from pavement_ui.core.results.beam_result import BeamResult
from pavement_ui.core.results.vector_drawing import VectorDrawing
from pavement_ui.presentation.dialogs.file_dialogs import ask_dxf_path, ask_pdf_path
from pavement_ui.presentation.report.drawing_pdf import export_drawing_pdf
from pavement_ui.presentation.report.report_exporter import write_file
from pavement_ui.presentation.results.drawing.drawing_view import DrawingView
from pavement_ui.presentation.text.strings import dialogs as d
from pavement_ui.presentation.text.strings import results as s
from pavement_ui.presentation.theme import tokens

_SIZE_PX = (1280, 860)
_TITLE_STYLE = "font-size: 20px; font-weight: 600;"


def _button(text: str, name: str) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName(name)
    return button


class DrawingWindow(QWidget):
    """Title, zoom buttons and hint, the sheet, and Baixar PDF…, Baixar DXF…, Fechar"""

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
        self._exporter = exporter
        self._beam_id = result.beam_id
        self._sheet = sheet
        self._title = QLabel()
        self._title.setStyleSheet(_TITLE_STYLE)
        self.view = DrawingView()
        fit = _button(s.DRAWING_FIT, "drawingFitButton")
        zoom_in = _button(s.DRAWING_ZOOM_IN, "drawingZoomInButton")
        zoom_out = _button(s.DRAWING_ZOOM_OUT, "drawingZoomOutButton")
        pdf = _button(s.DRAWING_PDF, "drawingPdfButton")
        dxf = _button(s.DRAWING_DXF, "drawingDxfButton")
        close = QPushButton(s.CLOSE)
        fit.clicked.connect(self.view.fit)
        zoom_in.clicked.connect(self.view.zoom_in)
        zoom_out.clicked.connect(self.view.zoom_out)
        pdf.clicked.connect(self._download_pdf)
        dxf.clicked.connect(self._download_dxf)
        close.clicked.connect(self.close)
        hint = QLabel(s.DRAWING_HINT)
        hint.setObjectName("hint")
        header = QHBoxLayout()
        header.addWidget(self._title)
        header.addStretch(1)
        header.addWidget(hint)
        for button in (fit, zoom_in, zoom_out):
            header.addWidget(button)
        footer = QHBoxLayout()
        footer.addStretch(1)
        for button in (pdf, dxf, close):
            footer.addWidget(button)
        layout = QVBoxLayout(self)
        margin = tokens.MARGIN_PX * 2
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.addLayout(header)
        layout.addWidget(self.view, 1)
        layout.addLayout(footer)
        self.set_sheet(result, sheet)

    def set_sheet(self, result: BeamResult, sheet: VectorDrawing) -> None:
        """Show a beam's sheet, fitted to the window"""
        self._beam_id, self._sheet = result.beam_id, sheet
        title = s.DRAWING_TITLE.format(id=result.beam_id)
        self.setWindowTitle(title)
        self._title.setText(title)
        self.view.set_drawing(sheet)

    def _file_name(self) -> str:
        return s.DRAWING_FILE_NAME.format(id=self._beam_id)

    def _download_pdf(self) -> None:
        path = ask_pdf_path(
            self, self._file_name() + d.PDF_EXTENSION, d.EXPORT_DRAWING_PDF_TITLE
        )
        if path is None:
            return
        sheet, title = self._sheet, s.DRAWING_PDF_TITLE.format(id=self._beam_id)

        def write(target: Path) -> None:
            export_drawing_pdf(sheet, target, title)

        write_file(
            self, path, write, d.EXPORT_DRAWING_PDF_TITLE, d.EXPORT_DRAWING_FAILED
        )

    def _download_dxf(self) -> None:
        path = ask_dxf_path(self, self._file_name() + d.DXF_EXTENSION)
        if path is None:
            return
        sheet, exporter = self._sheet, self._exporter

        def write(target: Path) -> None:
            exporter.write_dxf(sheet, target)

        write_file(self, path, write, d.EXPORT_DXF_TITLE, d.EXPORT_DRAWING_FAILED)
