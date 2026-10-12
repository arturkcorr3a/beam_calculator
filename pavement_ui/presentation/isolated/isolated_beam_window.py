"""Isolated beam calculator window (F11, mockup A9, docs/UI_SPEC.md §11)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pavement_ui.core.ports import IsolatedBeamEngine
from pavement_ui.core.results.outcomes import (
    IsolatedBeamOutcome,
    IsolatedBeamSuccess,
    IsolatedInvalidInput,
    IsolatedNotVerified,
    UnexpectedFailure,
)
from pavement_ui.core.session import ProjectSession
from pavement_ui.presentation.dialogs import messages
from pavement_ui.presentation.execution.engine_executor import EngineExecutor
from pavement_ui.presentation.isolated.beam_scheme_widget import BeamSchemeWidget
from pavement_ui.presentation.isolated.config_summary_group import ConfigSummaryGroup
from pavement_ui.presentation.isolated.isolated_inputs_group import IsolatedInputsGroup
from pavement_ui.presentation.isolated.isolated_results_tabs import IsolatedResultsTabs
from pavement_ui.presentation.isolated.self_weight_card import SelfWeightCard
from pavement_ui.presentation.session_bridge import QtSessionBridge
from pavement_ui.presentation.text.strings import isolated as s
from pavement_ui.presentation.text.strings import results as rs
from pavement_ui.presentation.theme import tokens
from pavement_ui.presentation.widgets.busy_overlay import BusyOverlay
from pavement_ui.presentation.widgets.titled_panel import TitledPanel
from pavement_ui.presentation.widgets.variants import set_variant

_SIZE_PX = (1280, 840)
_LEFT_WIDTH_PX = 340


class IsolatedBeamWindow(QWidget):
    """Non-modal window: inputs on the left, scheme and results on the right

    Any edit clears the results, so they always match the inputs [Decisão].
    The job runs on the shared engine executor: "Dimensionar" waits while any
    job (also a pavement design) is running.
    """

    def __init__(
        self,
        session: ProjectSession,
        bridge: QtSessionBridge,
        executor: EngineExecutor,
        engine: IsolatedBeamEngine,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setObjectName("isolatedBeamWindow")
        self.setWindowTitle(s.TITLE)
        self.resize(*_SIZE_PX)
        self._session, self._executor, self._engine = session, executor, engine
        self._inputs = IsolatedInputsGroup()
        self._summary = ConfigSummaryGroup()
        self._weight = SelfWeightCard()
        self._scheme = BeamSchemeWidget()
        self._results = IsolatedResultsTabs()
        self._design = QPushButton(s.DESIGN)
        self._design.setObjectName("isoDesignButton")
        set_variant(self._design, "primary")
        self._build_layout()
        self._overlay = BusyOverlay(self)
        self._inputs.changed.connect(self._on_inputs_changed)
        self._design.clicked.connect(self._run)
        bridge.config_changed.connect(self._refresh_config)
        executor.busy_changed.connect(self._on_busy)
        self._refresh_config()
        self._on_inputs_changed()
        self._on_busy(executor.busy)

    def _build_layout(self) -> None:
        left = QVBoxLayout()
        for widget in (self._inputs, self._summary, self._weight):
            left.addWidget(widget)
        left.addStretch(1)
        left.addWidget(self._design)
        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setFixedWidth(_LEFT_WIDTH_PX)
        right = QVBoxLayout()
        right.addWidget(TitledPanel(s.SCHEME, self._scheme))
        right.addWidget(self._results, 1)
        body = QHBoxLayout()
        body.addWidget(left_widget)
        body.addLayout(right, 1)
        close = QPushButton(rs.CLOSE)
        close.setObjectName("isoCloseButton")
        close.clicked.connect(self.close)
        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(close)
        layout = QVBoxLayout(self)
        margin = tokens.MARGIN_PX
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.addLayout(body, 1)
        layout.addLayout(footer)

    def _refresh_config(self) -> None:
        self._summary.set_config(self._session.config)

    def _on_inputs_changed(self) -> None:
        data = self._inputs.values()
        weight = self._engine.self_weight_kn_m(data.width_cm, data.height_cm)
        self._weight.set_values(weight, data.width_cm, data.height_cm)
        self._scheme.set_values(data.length_m, weight)
        self._results.clear()

    def _on_busy(self, busy: bool) -> None:
        self._design.setEnabled(not busy)

    def _run(self) -> None:
        if self._executor.busy:
            return
        job = self._engine.make_job(
            self._inputs.values(), self._session.config, self._session.log
        )
        self._overlay.show_busy(s.DESIGNING)
        self._executor.submit(job, self._on_done, self._on_error)

    def _on_done(self, outcome: IsolatedBeamOutcome) -> None:
        self._overlay.hide_busy()
        match outcome:
            case IsolatedBeamSuccess(result=result):
                self._results.set_result(result)
            case IsolatedNotVerified(message=message):
                self._results.clear()
                data = self._inputs.values()
                messages.show_isolated_not_verified(
                    self, message, data.width_cm, data.height_cm
                )
            case IsolatedInvalidInput(message=message):
                self._results.clear()
                messages.show_isolated_input_error(self, message)
            case UnexpectedFailure():
                self._results.clear()
                messages.show_design_unexpected(self, outcome)

    def _on_error(self, message: str, details: str) -> None:
        self._overlay.hide_busy()
        self._results.clear()
        messages.show_design_unexpected(self, UnexpectedFailure(message, details))
