"""DrawingPanel: a beam's detailing sheet with zoom and PDF and DXF downloads."""

from pathlib import Path

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from pavement_ui.core.ports import DrawingExporter
from pavement_ui.core.results.vector_drawing import VectorDrawing
from pavement_ui.presentation.dialogs.file_dialogs import ask_dxf_path, ask_pdf_path
from pavement_ui.presentation.report.drawing_pdf import export_drawing_pdf
from pavement_ui.presentation.report.report_exporter import write_file
from pavement_ui.presentation.results.drawing.drawing_view import DrawingView
from pavement_ui.presentation.text.strings import dialogs as d
from pavement_ui.presentation.text.strings import results as s


def _button(text: str, name: str) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName(name)
    return button


class DrawingPanel(QWidget):
    """Hint and zoom buttons, the sheet, then Baixar PDF… and Baixar DXF…

    Used by the pavement's DrawingWindow and by the isolated beam calculator.
    """

    def __init__(
        self, exporter: DrawingExporter, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._exporter = exporter
        self._beam_id = ""
        self._sheet: VectorDrawing | None = None
        self.view = DrawingView()
        fit = _button(s.DRAWING_FIT, "drawingFitButton")
        zoom_in = _button(s.DRAWING_ZOOM_IN, "drawingZoomInButton")
        zoom_out = _button(s.DRAWING_ZOOM_OUT, "drawingZoomOutButton")
        pdf = _button(s.DRAWING_PDF, "drawingPdfButton")
        dxf = _button(s.DRAWING_DXF, "drawingDxfButton")
        fit.clicked.connect(self.view.fit)
        zoom_in.clicked.connect(self.view.zoom_in)
        zoom_out.clicked.connect(self.view.zoom_out)
        pdf.clicked.connect(self._download_pdf)
        dxf.clicked.connect(self._download_dxf)
        hint = QLabel(s.DRAWING_HINT)
        hint.setObjectName("hint")
        header = QHBoxLayout()
        header.addStretch(1)
        header.addWidget(hint)
        for button in (fit, zoom_in, zoom_out):
            header.addWidget(button)
        footer = QHBoxLayout()
        footer.addStretch(1)
        for button in (pdf, dxf):
            footer.addWidget(button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(header)
        layout.addWidget(self.view, 1)
        layout.addLayout(footer)

    def set_sheet(self, beam_id: str, sheet: VectorDrawing) -> None:
        """Show a beam's sheet, fitted to the view"""
        self._beam_id, self._sheet = beam_id, sheet
        self.view.set_drawing(sheet)

    def _file_name(self) -> str:
        return s.DRAWING_FILE_NAME.format(id=self._beam_id)

    def _download_pdf(self) -> None:
        sheet = self._sheet
        if sheet is None:
            return
        path = ask_pdf_path(
            self, self._file_name() + d.PDF_EXTENSION, d.EXPORT_DRAWING_PDF_TITLE
        )
        if path is None:
            return
        title = s.DRAWING_PDF_TITLE.format(id=self._beam_id)

        def write(target: Path) -> None:
            export_drawing_pdf(sheet, target, title)

        write_file(
            self, path, write, d.EXPORT_DRAWING_PDF_TITLE, d.EXPORT_DRAWING_FAILED
        )

    def _download_dxf(self) -> None:
        sheet, exporter = self._sheet, self._exporter
        if sheet is None:
            return
        path = ask_dxf_path(self, self._file_name() + d.DXF_EXTENSION)
        if path is None:
            return

        def write(target: Path) -> None:
            exporter.write_dxf(sheet, target)

        write_file(self, path, write, d.EXPORT_DXF_TITLE, d.EXPORT_DRAWING_FAILED)
