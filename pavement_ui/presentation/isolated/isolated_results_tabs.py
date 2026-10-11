"""Results of the isolated beam in three tabs, or an empty-state hint."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QStackedWidget, QTabWidget, QWidget

from pavement_ui.core.results.beam_result import BeamResult
from pavement_ui.presentation.results.beam.beam_tables import BeamTables
from pavement_ui.presentation.results.beam.diagram_layout import DiagramKind
from pavement_ui.presentation.results.beam.diagram_widget import DiagramWidget
from pavement_ui.presentation.results.beam.section_panel import SectionPanel
from pavement_ui.presentation.text.strings import isolated as s
from pavement_ui.presentation.text.strings import results as rs
from pavement_ui.presentation.widgets.titled_panel import TitledPanel


class IsolatedResultsTabs(QStackedWidget):
    """Reuses the pavement beam components (tables, section, diagrams)"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        empty = QLabel(s.EMPTY)
        empty.setObjectName("hint")
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tables = BeamTables()
        self.section = SectionPanel()
        self.moment = DiagramWidget(DiagramKind.MOMENT)
        self.shear = DiagramWidget(DiagramKind.SHEAR)
        diagrams = QWidget()
        row = QHBoxLayout(diagrams)
        row.addWidget(TitledPanel(rs.MOMENT_PANEL, self.moment))
        row.addWidget(TitledPanel(rs.SHEAR_PANEL, self.shear))
        self.tabs = QTabWidget()
        self.tabs.setObjectName("isoResultTabs")
        self.tabs.addTab(self.tables, s.TAB_TABLES)
        self.tabs.addTab(self.section, s.TAB_SECTION)
        self.tabs.addTab(diagrams, s.TAB_DIAGRAMS)
        self.addWidget(empty)
        self.addWidget(self.tabs)

    @property
    def has_result(self) -> bool:
        return self.currentWidget() is self.tabs

    def set_result(self, result: BeamResult) -> None:
        self.tables.set_result(result)
        self.section.set_result(result)
        self.moment.set_result(result)
        self.shear.set_result(result)
        self.setCurrentWidget(self.tabs)

    def clear(self) -> None:
        self.setCurrentIndex(0)
