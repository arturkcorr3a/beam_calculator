"""The Pilares / Vigas / Lajes tabs, titled with their current counts."""

from collections.abc import Mapping

from PySide6.QtWidgets import QTabWidget, QWidget

from pavement_ui.core.model.element_kind import ElementKind
from pavement_ui.core.session import ProjectSession
from pavement_ui.presentation.session_bridge import QtSessionBridge
from pavement_ui.presentation.text.strings import panels as s

_TITLES = {
    ElementKind.PILLAR: s.TAB_PILLARS,
    ElementKind.BEAM: s.TAB_BEAMS,
    ElementKind.SLAB: s.TAB_SLABS,
}


class ElementTabs(QTabWidget):
    """One tab per element kind, in the order pillars, beams, slabs"""

    def __init__(
        self,
        panels: Mapping[ElementKind, QWidget],
        session: ProjectSession,
        bridge: QtSessionBridge,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("elementTabs")
        self._session = session
        self._kinds = tuple(_TITLES)
        for kind in self._kinds:
            self.addTab(panels[kind], "")
        bridge.records_changed.connect(self._refresh_titles)
        self._refresh_titles()

    def select(self, kind: ElementKind) -> None:
        self.setCurrentIndex(self._kinds.index(kind))

    def _refresh_titles(self) -> None:
        counts = self._session.records.counts()
        for index, kind in enumerate(self._kinds):
            self.setTabText(index, _TITLES[kind].format(n=counts.of(kind)))
