"""PlanPanel: the titled plan with its zoom and fit buttons."""

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QToolButton, QWidget

from pavement_ui.core.model.element_kind import ElementKind
from pavement_ui.core.results.plan_geometry import PlanGeometry
from pavement_ui.presentation.plan.plan_scene import PlanScene
from pavement_ui.presentation.plan.plan_view import PlanView
from pavement_ui.presentation.text.strings import main_window as s
from pavement_ui.presentation.theme.icons import IconName, icon
from pavement_ui.presentation.widgets.titled_panel import TitledPanel

_ZOOM_BUTTON_STEP = 1.25


class PlanPanel(TitledPanel):
    """Header "Planta do pavimento" + zoom and fit tools around the plan view"""

    def __init__(self, parent: QWidget | None = None) -> None:
        self._scene = PlanScene()
        self.view = PlanView(self._scene)
        super().__init__(s.PLAN_TITLE, self.view, s.PLAN_HINT, parent)
        self._add_button(
            "planZoomIn",
            "zoom_in",
            s.PLAN_ZOOM_IN,
            lambda: self.view.zoom_centered(_ZOOM_BUTTON_STEP),
        )
        self._add_button(
            "planZoomOut",
            "zoom_out",
            s.PLAN_ZOOM_OUT,
            lambda: self.view.zoom_centered(1 / _ZOOM_BUTTON_STEP),
        )
        self._add_button("planFit", "fit", s.PLAN_FIT, self.fit, with_text=True)
        self.item_clicked = self.view.item_clicked
        self.cursor_moved = self.view.cursor_moved

    def _add_button(
        self,
        name: str,
        icon_name: IconName,
        text: str,
        on_click: Callable[[], None],
        with_text: bool = False,
    ) -> None:
        button = QToolButton()
        button.setObjectName(name)
        button.setIcon(icon(icon_name))
        button.setToolTip(text)
        if with_text:
            button.setText(text)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.clicked.connect(on_click)
        self.add_tool(button)

    def refresh(self, geometry: PlanGeometry) -> None:
        """Redraw the plan, fitting it while the user has not zoomed or panned by hand

        "Ajustar à janela" turns the automatic fit back on.
        """
        was_empty = self._scene.bounds is None
        self._scene.rebuild(geometry)
        if self._scene.bounds is not None and (was_empty or not self.view.user_moved):
            self.fit()

    def highlight(self, kind: ElementKind, element_id: str | None) -> None:
        self._scene.highlight(kind, element_id)

    def fit(self) -> None:
        self.view.fit()
