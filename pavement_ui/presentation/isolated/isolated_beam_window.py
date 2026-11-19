"""Isolated beam calculator window (F11)."""

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from pavement_ui.core.model.isolated_beam_input import IsolatedBeamInput
from pavement_ui.core.ports import DrawingExporter, IsolatedBeamEngine
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
from pavement_ui.presentation.isolated.loads_group import LoadsGroup
from pavement_ui.presentation.isolated.spans_pillars_group import SpansPillarsGroup
from pavement_ui.presentation.session_bridge import QtSessionBridge
from pavement_ui.presentation.text.strings import isolated as s
from pavement_ui.presentation.text.strings import results as rs
from pavement_ui.presentation.theme import tokens
from pavement_ui.presentation.widgets.busy_overlay import BusyOverlay
from pavement_ui.presentation.widgets.titled_panel import TitledPanel
from pavement_ui.presentation.widgets.variants import set_variant

_SIZE_PX = (1280, 840)
_LEFT_WIDTH_PX = 460


class IsolatedBeamWindow(QWidget):
    """Non-modal window: inputs on the left (scrolling), scheme and results on the right

    Any edit (also of the project settings) clears the results, so they always
    match the inputs [Decisão]. The job runs on the shared engine executor:
    "Dimensionar" and the settings button wait while any job (also a pavement
    design) is running. edit_config opens the settings dialog over the given window.
    """

    def __init__(
        self,
        session: ProjectSession,
        bridge: QtSessionBridge,
        executor: EngineExecutor,
        engine: IsolatedBeamEngine,
        exporter: DrawingExporter,
        edit_config: Callable[[QWidget], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setObjectName("isolatedBeamWindow")
        self.setWindowTitle(s.TITLE)
        self.resize(*_SIZE_PX)
        self._session, self._executor, self._engine = session, executor, engine
        self._inputs = IsolatedInputsGroup()
        self._spans = SpansPillarsGroup()
        self._loads = LoadsGroup(engine, session.options)
        self._summary = ConfigSummaryGroup()
        self._scheme = BeamSchemeWidget()
        self._results = IsolatedResultsTabs(exporter)
        self._design = QPushButton(s.DESIGN)
        self._design.setObjectName("isoDesignButton")
        set_variant(self._design, "primary")
        self._build_layout()
        self._overlay = BusyOverlay(self)
        self._spans.span_count_changed.connect(self._loads.set_span_count)
        for group in (self._inputs, self._spans, self._loads):
            group.changed.connect(self._on_inputs_changed)
        self._design.clicked.connect(self._run)
        self._summary.edit_requested.connect(lambda: edit_config(self))
        bridge.config_changed.connect(self._refresh_config)
        executor.busy_changed.connect(self._on_busy)
        self._refresh_config()
        self._on_inputs_changed()
        self._on_busy(executor.busy)

    def _build_layout(self) -> None:
        inputs = QWidget()
        column = QVBoxLayout(inputs)
        column.setContentsMargins(0, 0, tokens.SPACING_PX, 0)
        for widget in (self._inputs, self._spans, self._loads, self._summary):
            column.addWidget(widget)
        column.addStretch(1)
        scroll = QScrollArea()
        scroll.setObjectName("isoInputsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(inputs)
        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.addWidget(scroll, 1)
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
        config = self._session.config
        self._summary.set_config(config)
        self._loads.set_wall_height(config.ceiling_height_m)
        self._results.clear()

    def _values(self) -> IsolatedBeamInput:
        return IsolatedBeamInput(
            width_cm=self._inputs.width_cm,
            height_cm=self._inputs.height_cm,
            span_lengths_m=self._spans.span_lengths_m(),
            pillars=self._spans.pillars(),
            loads=self._loads.loads(),
        )

    def _on_inputs_changed(self) -> None:
        self._loads.set_section(self._inputs.width_cm, self._inputs.height_cm)
        self._scheme.set_values(
            self._spans.span_lengths_m(),
            [pillar.width_cm for pillar in self._spans.pillars()],
            self._loads.span_totals(),
        )
        self._results.clear()

    def _on_busy(self, busy: bool) -> None:
        self._design.setEnabled(not busy)
        self._summary.set_edit_enabled(not busy)

    def _run(self) -> None:
        if self._executor.busy:
            return
        job = self._engine.make_job(
            self._values(), self._session.config, self._session.log
        )
        self._overlay.show_busy(s.DESIGNING)
        self._executor.submit(job, self._on_done, self._on_error)

    def _on_done(self, outcome: IsolatedBeamOutcome) -> None:
        self._overlay.hide_busy()
        match outcome:
            case IsolatedBeamSuccess():
                self._results.set_result(outcome)
            case IsolatedNotVerified(message=message):
                self._results.clear()
                messages.show_isolated_not_verified(
                    self, message, self._inputs.width_cm, self._inputs.height_cm
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
