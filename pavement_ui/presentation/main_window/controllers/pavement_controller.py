"""Flows of the Pavimento menu: focus a tab's form, clear the pavement."""

from collections.abc import Mapping

from PySide6.QtWidgets import QWidget

from pavement_ui.core.model.element_kind import ElementKind
from pavement_ui.core.session import ProjectSession
from pavement_ui.presentation.dialogs import messages
from pavement_ui.presentation.panels.element_form import ElementForm
from pavement_ui.presentation.panels.element_tabs import ElementTabs


class PavementController:
    """Runs actFocusPillars/Beams/Slabs and actClear"""

    def __init__(
        self,
        session: ProjectSession,
        tabs: ElementTabs,
        forms: Mapping[ElementKind, ElementForm],
        window: QWidget,
    ) -> None:
        self._session = session
        self._tabs = tabs
        self._forms = forms
        self._window = window

    def focus(self, kind: ElementKind) -> None:
        """Show the tab of kind and put the cursor on its first field"""
        self._tabs.select(kind)
        self._forms[kind].focus_first()

    def clear(self) -> None:
        """Remove every element after confirmation; the numbering continues"""
        if messages.confirm_clear(self._window):
            self._session.clear_pavement()
