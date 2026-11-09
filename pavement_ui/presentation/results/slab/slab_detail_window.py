"""SlabDetailWindow: the design report of one dimensioned slab."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from pavement_ui.core.results.slab_result import SlabResult
from pavement_ui.presentation.formatting.elements import fmt_dims_cm
from pavement_ui.presentation.formatting.numbers import fmt_number
from pavement_ui.presentation.report.report_builder import ReportBuilder
from pavement_ui.presentation.report.report_exporter import export_report
from pavement_ui.presentation.report.report_view import ReportView
from pavement_ui.presentation.report.slab_report import write_slab_report
from pavement_ui.presentation.results.slab.slab_texts import cm, slab_type
from pavement_ui.presentation.text.option_labels import OptionKind, label
from pavement_ui.presentation.text.strings import report as rs
from pavement_ui.presentation.text.strings import results as s
from pavement_ui.presentation.theme import tokens
from pavement_ui.presentation.widgets.banner import Banner
from pavement_ui.presentation.widgets.value_chip import ValueChip

_SIZE_PX = (1040, 880)
_TITLE_STYLE = "font-size: 20px; font-weight: 600;"


class SlabDetailWindow(QWidget):
    """Header chips, verdict band, the slab's report, Exportar PDF… and Fechar"""

    def __init__(self, result: SlabResult, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setObjectName("slabDetailWindow")
        self.resize(*_SIZE_PX)
        self._title = QLabel()
        self._title.setStyleSheet(_TITLE_STYLE)
        self._chips = [ValueChip("", "") for _ in range(4)]
        self.verdict = Banner()
        self.verdict.setObjectName("slabVerdict")
        self.view = ReportView()
        self._result = result
        export = QPushButton(rs.EXPORT_PDF)
        export.setObjectName("slabExportButton")
        export.clicked.connect(self._export)
        close = QPushButton(s.CLOSE)
        close.clicked.connect(self.close)
        header = QHBoxLayout()
        header.addWidget(self._title)
        for chip in self._chips:
            header.addWidget(chip)
        header.addStretch(1)
        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(export)
        footer.addWidget(close)
        layout = QVBoxLayout(self)
        margin = tokens.MARGIN_PX * 2
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.addLayout(header)
        layout.addWidget(self.verdict)
        layout.addWidget(self.view, 1)
        layout.addLayout(footer)
        self.set_result(result)

    def set_result(self, result: SlabResult) -> None:
        self._result = result
        self.setWindowTitle(s.SLAB_TITLE.format(id=result.slab_id))
        self._title.setText(result.slab_id)
        values = (
            (s.CHIP_H, cm(result.thickness_cm)),
            (
                s.CHIP_DIMENSIONS,
                s.CM_VALUE.format(value=fmt_dims_cm(result.lx_cm, result.ly_cm)),
            ),
            (s.CHIP_TYPE, slab_type(result)),
            (s.CHIP_USAGE, label(OptionKind.USAGE, result.usage_key)),
        )
        for chip, (key, value) in zip(self._chips, values, strict=True):
            chip.set_value(key, value)
        check = result.deflection
        numbers = {
            "deflection": fmt_number(check.long_term_deflection_cm, 2),
            "limit": fmt_number(check.limit_cm, 2),
        }
        if check.passes:
            self.verdict.show_message(
                "ok", s.VERDICT_PASS, s.VERDICT_PASS_TEXT.format(**numbers)
            )
        else:
            self.verdict.show_message(
                "error", s.VERDICT_FAIL, s.VERDICT_FAIL_TEXT.format(**numbers)
            )
        builder = ReportBuilder()
        write_slab_report(builder, result)
        self.view.set_document(builder.document())

    def _export(self) -> None:
        result = self._result

        def write(builder: ReportBuilder) -> None:
            write_slab_report(builder, result)

        export_report(
            self,
            write,
            rs.SLAB_FILE_NAME.format(id=result.slab_id),
            rs.SLAB_REPORT_TITLE.format(id=result.slab_id),
        )
