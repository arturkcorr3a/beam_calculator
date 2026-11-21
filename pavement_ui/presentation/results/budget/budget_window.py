"""BudgetWindow: the net cost of the beams' steel and concrete."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from pavement_ui.core.results.budget import BudgetResult
from pavement_ui.presentation.formatting.numbers import fmt_money
from pavement_ui.presentation.report.budget_report import write_budget_report
from pavement_ui.presentation.report.report_builder import ReportBuilder
from pavement_ui.presentation.report.report_exporter import export_report
from pavement_ui.presentation.report.report_view import ReportView
from pavement_ui.presentation.text.strings import report as rs
from pavement_ui.presentation.text.strings import results as s
from pavement_ui.presentation.theme import tokens

_SIZE_PX = (900, 760)
_TITLE_STYLE = "font-size: 20px; font-weight: 600;"


class BudgetWindow(QWidget):
    """Total, the budget's report, Exportar PDF… and Fechar"""

    def __init__(
        self, budget: BudgetResult, file_name: str, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setObjectName("budgetWindow")
        self.resize(*_SIZE_PX)
        self._total = QLabel()
        self._total.setObjectName("budgetTotal")
        self._total.setStyleSheet(_TITLE_STYLE)
        self.view = ReportView()
        self._budget, self._file_name = budget, file_name
        export = QPushButton(rs.EXPORT_PDF)
        export.setObjectName("budgetExportButton")
        export.clicked.connect(self._export)
        close = QPushButton(s.CLOSE)
        close.clicked.connect(self.close)
        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(export)
        footer.addWidget(close)
        layout = QVBoxLayout(self)
        margin = tokens.MARGIN_PX * 2
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.addWidget(self._total)
        layout.addWidget(self.view, 1)
        layout.addLayout(footer)
        self.set_budget(budget, file_name)

    def _name(self) -> str:
        return Path(self._file_name).stem

    def set_budget(self, budget: BudgetResult, file_name: str) -> None:
        self._budget, self._file_name = budget, file_name
        self.setWindowTitle(s.BUDGET_TITLE.format(file=file_name))
        self._total.setText(s.BUDGET_TOTAL.format(total=fmt_money(budget.total)))
        builder = ReportBuilder()
        write_budget_report(builder, budget, self._name())
        self.view.set_document(builder.document())

    def _export(self) -> None:
        budget, name = self._budget, self._name()

        def write(builder: ReportBuilder) -> None:
            write_budget_report(builder, budget, name)

        export_report(
            self,
            write,
            rs.BUDGET_FILE_NAME.format(name=name),
            rs.BUDGET_REPORT_TITLE.format(name=name),
        )
