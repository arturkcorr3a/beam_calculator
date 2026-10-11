"""Main window of the application (mockups A1–A3, docs/UI_SPEC.md §8.1)."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMainWindow, QSplitter, QWidget

from pavement_ui.core.model.element_kind import ElementKind
from pavement_ui.core.results.outcomes import DesignSuccess
from pavement_ui.core.session import ProjectSession
from pavement_ui.presentation.dialogs import messages
from pavement_ui.presentation.execution.engine_executor import EngineExecutor
from pavement_ui.presentation.main_window.action_rules import ActionContext
from pavement_ui.presentation.main_window.action_rules import ActionId as A
from pavement_ui.presentation.main_window.app_actions import AppActions
from pavement_ui.presentation.main_window.controllers.config_controller import (
    ConfigController,
)
from pavement_ui.presentation.main_window.controllers.file_controller import (
    FileController,
)
from pavement_ui.presentation.main_window.controllers.pavement_controller import (
    PavementController,
)
from pavement_ui.presentation.main_window.controllers.structure_controller import (
    StructureController,
)
from pavement_ui.presentation.main_window.menu_builder import build_menus, build_toolbar
from pavement_ui.presentation.main_window.status_bar import MainStatusBar
from pavement_ui.presentation.panels.beams.beams_panel import beams_panel
from pavement_ui.presentation.panels.element_tabs import ElementTabs
from pavement_ui.presentation.panels.pillars.pillars_panel import pillars_panel
from pavement_ui.presentation.panels.slabs.slabs_panel import slabs_panel
from pavement_ui.presentation.plan.plan_panel import PlanPanel
from pavement_ui.presentation.results.window_registry import ResultWindows
from pavement_ui.presentation.session_bridge import QtSessionBridge
from pavement_ui.presentation.text.strings import main_window as s
from pavement_ui.presentation.theme import tokens
from pavement_ui.presentation.widgets.busy_overlay import BusyOverlay

_INITIAL_SIZE_PX = (1280, 800)
_MINIMUM_SIZE_PX = (1024, 640)
_SIDE_WIDTH_PX = 440
_SIDE_MIN_WIDTH_PX = 420


class MainWindow(QMainWindow):
    """Top-level window: side tabs, plan, menus, toolbar and status bar

    It only assembles and connects components; flows live in the controllers
    and enabling rules in ``action_rules``.
    """

    def __init__(
        self,
        session: ProjectSession,
        bridge: QtSessionBridge,
        executor: EngineExecutor,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("mainWindow")
        self.resize(*_INITIAL_SIZE_PX)
        self.setMinimumSize(*_MINIMUM_SIZE_PX)
        self._session, self._executor = session, executor
        self._panels = {
            ElementKind.PILLAR: pillars_panel(session, bridge),
            ElementKind.BEAM: beams_panel(session, bridge),
            ElementKind.SLAB: slabs_panel(session, bridge),
        }
        self._tabs = ElementTabs(self._panels, session, bridge)
        self._tabs.setMinimumWidth(_SIDE_MIN_WIDTH_PX)
        self._plan = PlanPanel()
        self.setCentralWidget(self._build_body())
        self._actions = AppActions(self)
        build_menus(self, self._actions)
        build_toolbar(self, self._actions)
        self._status = MainStatusBar(session)
        self.setStatusBar(self._status)
        forms = {kind: panel.form for kind, panel in self._panels.items()}
        self._pavement = PavementController(session, self._tabs, forms, self)
        self._files = FileController(session, self, self._plan.fit)
        self._config = ConfigController(session, self)
        self._structure = StructureController(
            session, executor, self, self._on_design_success
        )
        self._overlay = BusyOverlay(self)
        self._results = ResultWindows(session, bridge, self)
        self._connect_actions()
        self._connect_state(bridge)
        self._refresh()

    def _build_body(self) -> QWidget:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._tabs)
        splitter.addWidget(self._plan)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([_SIDE_WIDTH_PX, _INITIAL_SIZE_PX[0] - _SIDE_WIDTH_PX])
        margin = tokens.MARGIN_PX
        splitter.setContentsMargins(margin, margin, margin, margin)
        return splitter

    def _connect_actions(self) -> None:
        actions, pavement = self._actions, self._pavement
        actions[A.NEW].triggered.connect(self._files.new_project)
        actions[A.OPEN].triggered.connect(self._files.open)
        actions[A.SAVE].triggered.connect(self._files.save)
        actions[A.SAVE_AS].triggered.connect(self._files.save_as)
        actions[A.CONFIG].triggered.connect(self._config.edit)
        actions[A.VALIDATE].triggered.connect(self._structure.validate)
        actions[A.DESIGN].triggered.connect(self._structure.design)
        actions[A.RESULTS].triggered.connect(self._results.open_summary)
        actions[A.QUIT].triggered.connect(self._files.quit)
        actions[A.FOCUS_PILLARS].triggered.connect(
            lambda: pavement.focus(ElementKind.PILLAR)
        )
        actions[A.FOCUS_BEAMS].triggered.connect(
            lambda: pavement.focus(ElementKind.BEAM)
        )
        actions[A.FOCUS_SLABS].triggered.connect(
            lambda: pavement.focus(ElementKind.SLAB)
        )
        actions[A.CLEAR].triggered.connect(pavement.clear)
        actions[A.ABOUT].triggered.connect(lambda: messages.show_about(self))

    def _connect_state(self, bridge: QtSessionBridge) -> None:
        for signal in (
            bridge.records_changed,
            bridge.config_changed,
            bridge.validation_changed,
            bridge.design_started,
            bridge.design_finished,
            bridge.file_changed,
        ):
            signal.connect(self._refresh)
        self._executor.busy_changed.connect(self._on_busy)
        bridge.records_changed.connect(self._refresh_plan)
        for panel in self._panels.values():
            panel.selection_changed.connect(self._plan.highlight)
        self._plan.item_clicked.connect(self._on_plan_click)
        self._plan.cursor_moved.connect(self._status.set_cursor_m)
        self._refresh_plan()

    def _on_design_success(self, success: DesignSuccess) -> None:
        self._results.open_summary()

    def warm_up_engine(self) -> None:
        """Start the engine's worker process now, so the first design does not wait"""
        self._executor.warm_up()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Let a running design finish, then stop the engine's worker process"""
        self._executor.shutdown()
        super().closeEvent(event)

    def _refresh_plan(self) -> None:
        self._plan.refresh(self._session.plan_geometry())

    def _on_plan_click(self, kind: ElementKind, element_id: str) -> None:
        """Show the clicked element's tab and select its row"""
        self._tabs.select(kind)
        self._panels[kind].select_id(element_id)

    def _on_busy(self, busy: bool) -> None:
        for panel in self._panels.values():
            panel.setEnabled(not busy)
        self._status.set_busy(busy)
        if busy:
            self._overlay.show_busy(s.STATUS_DESIGNING)
        else:
            self._overlay.hide_busy()
        self._refresh()

    def _refresh(self) -> None:
        path = self._session.current_path
        self.setWindowTitle(s.window_title(path.name if path else None))
        self._status.refresh()
        self._actions.update_enabled_state(
            ActionContext(
                busy=self._executor.busy,
                has_elements=not self._session.records.is_empty,
                has_results=self._session.last_success is not None,
            )
        )
