"""Assembly of the Pilares tab."""

from PySide6.QtWidgets import QWidget

from pavement_ui.core.model.element_kind import ElementKind
from pavement_ui.core.model.records import PillarRecord
from pavement_ui.core.session import ProjectSession
from pavement_ui.presentation.panels.element_panel import ElementPanel, PanelTexts
from pavement_ui.presentation.panels.pillars.pillar_columns import PILLAR_COLUMNS
from pavement_ui.presentation.panels.pillars.pillar_form import PillarForm
from pavement_ui.presentation.session_bridge import QtSessionBridge
from pavement_ui.presentation.text.strings import panels as s

_TEXTS = PanelTexts(s.PILLAR_ADD, s.PILLAR_HINT, s.PILLAR_LIST, s.PILLAR_REMOVE)


def pillars_panel(
    session: ProjectSession, bridge: QtSessionBridge, parent: QWidget | None = None
) -> ElementPanel[PillarRecord]:
    """Build the pillars panel"""
    panel = ElementPanel[PillarRecord](
        ElementKind.PILLAR,
        PillarForm(),
        PILLAR_COLUMNS,
        lambda records: records.pillars,
        _TEXTS,
        session,
        bridge,
        parent,
    )
    panel.setObjectName("pillarsPanel")
    return panel
