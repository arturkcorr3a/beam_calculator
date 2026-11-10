"""Vãos e pilares: span lengths and the pillar under each support."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pavement_ui.core.model.isolated_beam_input import IsolatedPillarInput
from pavement_ui.presentation.isolated.spin_table import SpinColumn, SpinTable
from pavement_ui.presentation.text.strings import isolated as s
from pavement_ui.presentation.text.strings import panels as units

MAX_SPANS = 10
_SPANS = (SpinColumn(s.COL_LENGTH, 2, 0.01, 50.0, units.UNIT_M, 5.0),)
# the engine checks the NBR 6118 minimums (14 cm, 360 cm²) with its own message
_PILLARS = (
    SpinColumn(s.COL_PILLAR_WIDTH, 1, 1.0, 300.0, units.UNIT_CM, 20.0),
    SpinColumn(s.COL_PILLAR_DEPTH, 1, 1.0, 300.0, units.UNIT_CM, 20.0),
)


class SpansPillarsGroup(QGroupBox):
    """Spans table with + / − (1 to MAX_SPANS spans) and the pillars table under it

    Signals:
        changed: A length or pillar changed, or a span was added or removed.
        span_count_changed(int): The number of spans changed.
    """

    changed = Signal()
    span_count_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(s.SPANS_PILLARS, parent)
        self._spans = SpinTable(
            s.COL_SPAN, _SPANS, lambda i: s.SPAN_NAME.format(n=i + 1)
        )
        self._spans.setObjectName("isoSpans")
        self._pillars = SpinTable(
            s.COL_PILLAR, _PILLARS, lambda i: s.PILLAR_NAME.format(n=i + 1)
        )
        self._pillars.setObjectName("isoPillars")
        self._add = QPushButton(s.ADD_SPAN)
        self._add.setObjectName("isoAddSpan")
        self._remove = QPushButton(s.REMOVE_SPAN)
        self._remove.setObjectName("isoRemoveSpan")
        hint = QLabel(s.SPANS_HINT)
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        buttons = QHBoxLayout()
        buttons.addWidget(self._add)
        buttons.addWidget(self._remove)
        buttons.addStretch(1)
        layout = QVBoxLayout(self)
        layout.addWidget(self._spans)
        layout.addLayout(buttons)
        layout.addWidget(self._pillars)
        layout.addWidget(hint)
        self._add.clicked.connect(lambda: self._set_span_count(self.span_count + 1))
        self._remove.clicked.connect(lambda: self._set_span_count(self.span_count - 1))
        self._spans.changed.connect(self.changed)
        self._pillars.changed.connect(self.changed)
        self._set_span_count(1)

    @property
    def span_count(self) -> int:
        return self._spans.rowCount()

    def span_lengths_m(self) -> tuple[float, ...]:
        return tuple(row[0] for row in self._spans.values())

    def pillars(self) -> tuple[IsolatedPillarInput, ...]:
        return tuple(IsolatedPillarInput(w, d) for w, d in self._pillars.values())

    def _set_span_count(self, count: int) -> None:
        count = max(1, min(MAX_SPANS, count))
        self._add.setEnabled(count < MAX_SPANS)
        self._remove.setEnabled(count > 1)
        if count == self.span_count:
            return
        self._spans.blockSignals(True)
        self._pillars.blockSignals(True)
        self._spans.set_row_count(count)
        self._pillars.set_row_count(count + 1)
        self._spans.blockSignals(False)
        self._pillars.blockSignals(False)
        self.span_count_changed.emit(count)
        self.changed.emit()
