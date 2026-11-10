"""Results of the isolated beam: its report and its drawing, or an empty-state hint."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pavement_ui.core.ports import DrawingExporter
from pavement_ui.core.results.outcomes import IsolatedBeamSuccess
from pavement_ui.presentation.report.beam_report import write_beam_report
from pavement_ui.presentation.report.report_builder import ReportBuilder
from pavement_ui.presentation.report.report_exporter import export_report
from pavement_ui.presentation.report.report_view import ReportView
from pavement_ui.presentation.results.drawing.drawing_panel import DrawingPanel
from pavement_ui.presentation.text.strings import isolated as s
from pavement_ui.presentation.text.strings import report as rs


class IsolatedResultsTabs(QStackedWidget):
    """Tabs Relatório (as the pavement beam's, with Exportar PDF…) and Desenho

    The Desenho tab is disabled when the beam has no detailing sheet.
    """

    def __init__(
        self, exporter: DrawingExporter, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._success: IsolatedBeamSuccess | None = None
        empty = QLabel(s.EMPTY)
        empty.setObjectName("hint")
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.report = ReportView()
        export = QPushButton(rs.EXPORT_PDF)
        export.setObjectName("isoExportButton")
        export.clicked.connect(self._export)
        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(export)
        report_tab = QWidget()
        column = QVBoxLayout(report_tab)
        column.addWidget(self.report, 1)
        column.addLayout(footer)
        self.drawing = DrawingPanel(exporter)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("isoResultTabs")
        self.tabs.addTab(report_tab, s.TAB_REPORT)
        self._drawing_tab = self.tabs.addTab(self.drawing, s.TAB_DRAWING)
        self.tabs.currentChanged.connect(self._on_tab)
        self.addWidget(empty)
        self.addWidget(self.tabs)

    @property
    def has_result(self) -> bool:
        return self.currentWidget() is self.tabs

    def set_result(self, success: IsolatedBeamSuccess) -> None:
        self._success = success
        builder = ReportBuilder()
        self._write(builder)
        self.report.set_document(builder.document())
        sheet = success.result.sheet
        self.tabs.setTabEnabled(self._drawing_tab, sheet is not None)
        if sheet is not None:
            self.drawing.set_sheet(success.result.beam_id, sheet)
        self.setCurrentWidget(self.tabs)
        self._on_tab(self.tabs.currentIndex())

    def clear(self) -> None:
        self._success = None
        self.setCurrentIndex(0)

    def _write(self, builder: ReportBuilder) -> None:
        success = self._success
        if success is not None:
            write_beam_report(
                builder, success.result, success.materials, success.quantity
            )

    def _on_tab(self, index: int) -> None:
        if index == self._drawing_tab:  # fit once the view has its real size
            self.drawing.view.fit()

    def _export(self) -> None:
        if self._success is None:
            return
        beam_id = self._success.result.beam_id
        export_report(
            self,
            self._write,
            rs.BEAM_FILE_NAME.format(id=beam_id),
            rs.BEAM_REPORT_TITLE.format(id=beam_id),
        )
