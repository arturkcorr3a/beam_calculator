"""Assembly of the Vigas tab."""

from PySide6.QtWidgets import QWidget

from pavement_ui.core.model.element_kind import ElementKind
from pavement_ui.core.model.records import BeamRecord
from pavement_ui.core.session import ProjectSession
from pavement_ui.presentation.panels.beams.beam_columns import BEAM_COLUMNS
from pavement_ui.presentation.panels.beams.beam_form import BeamForm
from pavement_ui.presentation.panels.element_panel import ElementPanel, PanelTexts
from pavement_ui.presentation.session_bridge import QtSessionBridge
from pavement_ui.presentation.text.strings import panels as s

_TEXTS = PanelTexts(s.BEAM_ADD, s.BEAM_HINT, s.BEAM_LIST, s.BEAM_REMOVE)


def beams_panel(
    session: ProjectSession, bridge: QtSessionBridge, parent: QWidget | None = None
) -> ElementPanel[BeamRecord]:
    """Build the beams panel; the wall hint follows the ceiling height"""
    form = BeamForm(session.options)
    panel = ElementPanel[BeamRecord](
        ElementKind.BEAM,
        form,
        BEAM_COLUMNS,
        lambda records: records.beams,
        _TEXTS,
        session,
        bridge,
        parent,
    )
    panel.setObjectName("beamsPanel")

    def follow_config() -> None:
        form.wall.set_ceiling_height(session.config.ceiling_height_m)

    bridge.config_changed.connect(follow_config)
    follow_config()
    return panel
