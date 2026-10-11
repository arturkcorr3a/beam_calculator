"""BeamDetailWindow: everything about one dimensioned beam (mockup A7)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from pavement_ui.core.results.beam_result import BeamResult
from pavement_ui.presentation.formatting.elements import fmt_pillar_chain
from pavement_ui.presentation.formatting.numbers import fmt_length_cm
from pavement_ui.presentation.results.beam.beam_result_view import BeamResultView
from pavement_ui.presentation.text.strings import results as s
from pavement_ui.presentation.theme import tokens
from pavement_ui.presentation.widgets.value_chip import ValueChip

_SIZE_PX = (1280, 880)
_TITLE_STYLE = "font-size: 20px; font-weight: 600;"


class BeamDetailWindow(QWidget):
    """Header (ID and chips), the beam's results, and Fechar"""

    def __init__(self, result: BeamResult, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setObjectName("beamDetailWindow")
        self.resize(*_SIZE_PX)
        self._title = QLabel()
        self._title.setStyleSheet(_TITLE_STYLE)
        self._chips = [ValueChip("", "") for _ in range(4)]
        self.view = BeamResultView()
        close = QPushButton(s.CLOSE)
        close.clicked.connect(self.close)
        header = QHBoxLayout()
        header.addWidget(self._title)
        for chip in self._chips:
            header.addWidget(chip)
        header.addStretch(1)
        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(close)
        layout = QVBoxLayout(self)
        margin = tokens.MARGIN_PX * 2
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.addLayout(header)
        layout.addWidget(self.view, 1)
        layout.addLayout(footer)
        self.set_result(result)

    def set_result(self, result: BeamResult) -> None:
        self.setWindowTitle(s.BEAM_TITLE.format(id=result.beam_id))
        self._title.setText(result.beam_id)
        values = (
            (s.CHIP_BW, s.CM_VALUE.format(value=fmt_length_cm(result.width_cm))),
            (s.CHIP_H, s.CM_VALUE.format(value=fmt_length_cm(result.height_cm))),
            (s.CHIP_PILLARS, fmt_pillar_chain(result.pillar_ids)),
            (s.CHIP_SPANS, str(len(result.spans))),
        )
        for chip, (key, value) in zip(self._chips, values, strict=True):
            chip.set_value(key, value)
        self.view.set_result(result)
