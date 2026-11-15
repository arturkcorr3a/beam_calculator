"""Assembly of the Lajes tab."""

from PySide6.QtWidgets import QWidget

from pavement_ui.core.model.element_kind import ElementKind
from pavement_ui.core.model.records import SlabRecord
from pavement_ui.core.session import ProjectSession
from pavement_ui.presentation.panels.element_panel import ElementPanel, PanelTexts
from pavement_ui.presentation.panels.slabs.slab_columns import SLAB_COLUMNS
from pavement_ui.presentation.panels.slabs.slab_form import SlabForm
from pavement_ui.presentation.session_bridge import QtSessionBridge
from pavement_ui.presentation.text.strings import panels as s

_TEXTS = PanelTexts(s.SLAB_ADD, s.SLAB_HINT, s.SLAB_LIST, s.SLAB_REMOVE)


def slabs_panel(
    session: ProjectSession, bridge: QtSessionBridge, parent: QWidget | None = None
) -> ElementPanel[SlabRecord]:
    """Build the slabs panel; usages follow the building category

    Registered slabs keep their usage when the category changes [Manual].
    """
    form = SlabForm(session.options)
    panel = ElementPanel[SlabRecord](
        ElementKind.SLAB,
        form,
        SLAB_COLUMNS,
        lambda records: records.slabs,
        _TEXTS,
        session,
        bridge,
        parent,
    )
    panel.setObjectName("slabsPanel")
    shown_category: list[str | None] = [None]

    def follow_config() -> None:
        category = session.config.building_category_key
        if category != shown_category[0]:
            shown_category[0] = category
            form.set_category(category)

    bridge.config_changed.connect(follow_config)
    follow_config()
    return panel
