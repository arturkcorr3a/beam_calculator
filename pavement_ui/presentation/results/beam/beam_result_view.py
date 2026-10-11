"""BeamResultView: tables and section above, moment and shear diagrams below.

Shared by the pavement beam detail (A7) and the isolated beam (A9).
"""

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from pavement_ui.core.results.beam_result import BeamResult
from pavement_ui.presentation.results.beam.beam_tables import BeamTables
from pavement_ui.presentation.results.beam.diagram_layout import DiagramKind
from pavement_ui.presentation.results.beam.diagram_widget import DiagramWidget
from pavement_ui.presentation.results.beam.section_panel import SectionPanel
from pavement_ui.presentation.text.strings import results as s
from pavement_ui.presentation.widgets.titled_panel import TitledPanel

_SECTION_WIDTH_PX = 420


class BeamResultView(QWidget):
    """Every result of one beam"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.tables = BeamTables()
        self.section = SectionPanel()
        self.section.setFixedWidth(_SECTION_WIDTH_PX)
        self.moment = DiagramWidget(DiagramKind.MOMENT)
        self.shear = DiagramWidget(DiagramKind.SHEAR)
        top = QHBoxLayout()
        top.addWidget(self.tables, 1)
        top.addWidget(self.section)
        bottom = QHBoxLayout()
        bottom.addWidget(TitledPanel(s.MOMENT_PANEL, self.moment))
        bottom.addWidget(TitledPanel(s.SHEAR_PANEL, self.shear))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top, 3)
        layout.addLayout(bottom, 2)

    def set_result(self, result: BeamResult) -> None:
        self.tables.set_result(result)
        self.section.set_result(result)
        self.moment.set_result(result)
        self.shear.set_result(result)
