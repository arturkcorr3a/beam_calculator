"""Fields of a new slab."""

from PySide6.QtWidgets import QComboBox, QLineEdit, QVBoxLayout, QWidget

from pavement_ui.core.options import EngineOptions
from pavement_ui.core.session import ProjectSession
from pavement_ui.presentation.panels.element_form import ElementForm
from pavement_ui.presentation.text.option_labels import OptionKind, label
from pavement_ui.presentation.text.strings import panels as s
from pavement_ui.presentation.widgets.combo_helpers import fill_combo, selected_key
from pavement_ui.presentation.widgets.form_section import FormSection
from pavement_ui.presentation.widgets.unit_spin_box import IntUnitSpinBox

_LABEL_WIDTH_PX = 132
_MAX_LOWERED_CM = 200


class SlabForm(ElementForm):
    """Corner pillar IDs (typed), usage of the building category and lowering"""

    def __init__(self, options: EngineOptions, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._options = options
        self._corners = QLineEdit()
        self._corners.setObjectName("slabCorners")
        self._corners.setPlaceholderText(s.SLAB_CORNERS_PLACEHOLDER)
        self._usage = QComboBox()
        self._usage.setObjectName("slabUsage")
        self._lowered = IntUnitSpinBox(0, _MAX_LOWERED_CM, s.UNIT_CM)
        self._lowered.setObjectName("slabLowered")
        section = FormSection(s.SLAB_FORM, _LABEL_WIDTH_PX)
        section.add_row(s.SLAB_CORNERS, self._corners, s.SLAB_CORNERS_HINT)
        self._usage_hint = section.add_row(s.SLAB_USAGE, self._usage, "")
        section.add_row(s.SLAB_LOWERED, self._lowered)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(section)
        self._corners.returnPressed.connect(self.submit_requested)

    def set_category(self, category_key: str) -> None:
        """Offer the usages of a building category (NBR 6120 Table 10)

        A category without usages makes inclusion unavailable.
        """
        usages = self._options.usages_for(category_key)
        fill_combo(self._usage, usages, lambda key: label(OptionKind.USAGE, key))
        category = label(OptionKind.CATEGORY, category_key)
        hint = s.SLAB_USAGE_HINT if usages else s.SLAB_NO_USAGES_HINT
        if self._usage_hint is not None:
            self._usage_hint.setText(hint.format(category=category))
        self.availability_changed.emit(bool(usages))

    def is_available(self) -> bool:
        return self._usage.count() > 0

    def include(self, session: ProjectSession) -> str:
        record = session.add_slab(
            self._corners.text(), selected_key(self._usage) or "", self._lowered.value()
        )
        return record.id

    def focus_first(self) -> None:
        self._corners.setFocus()
        self._corners.selectAll()
