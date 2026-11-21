"""Fields of a new continuous beam."""

from PySide6.QtWidgets import QCheckBox, QComboBox, QLineEdit, QVBoxLayout, QWidget

from pavement_ui.core.options import EngineOptions
from pavement_ui.core.session import ProjectSession
from pavement_ui.presentation.panels.beams.wall_form import WallForm
from pavement_ui.presentation.panels.element_form import ElementForm
from pavement_ui.presentation.text.option_labels import OptionKind, label
from pavement_ui.presentation.text.strings import panels as s
from pavement_ui.presentation.widgets.combo_helpers import fill_combo, selected_key
from pavement_ui.presentation.widgets.form_section import FormSection
from pavement_ui.presentation.widgets.unit_spin_box import UnitSpinBox

_LABEL_WIDTH_PX = 132
_REFERENCE_WIDTH_PX = 96


class BeamForm(ElementForm):
    """Pillar IDs (typed), reference pillar, bw, alignment and the wall on top"""

    def __init__(self, options: EngineOptions, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pillar_ids = QLineEdit()
        self._pillar_ids.setObjectName("beamPillarIds")
        self._pillar_ids.setPlaceholderText(s.BEAM_PILLARS_PLACEHOLDER)
        self._reference = QLineEdit()
        self._reference.setObjectName("beamReference")
        self._reference.setPlaceholderText(s.BEAM_REFERENCE_PLACEHOLDER)
        self._reference.setMaximumWidth(_REFERENCE_WIDTH_PX)
        self._width = UnitSpinBox(1, 1.0, 200.0, s.UNIT_CM)
        self._width.setObjectName("beamWidth")
        self._width.setValue(14.0)
        # every alignment is offered: incompatibility only shows on validation [Manual]
        self._alignment = QComboBox()
        self._alignment.setObjectName("beamAlignment")
        fill_combo(
            self._alignment,
            options.alignments,
            lambda k: label(OptionKind.ALIGNMENT, k),
        )
        self._has_wall = QCheckBox(s.WALL_PRESENT)
        self._has_wall.setObjectName("beamHasWall")
        self._has_wall.setChecked(True)
        self.wall = WallForm(options)
        self._has_wall.toggled.connect(self.wall.setEnabled)
        section = FormSection(s.BEAM_FORM, _LABEL_WIDTH_PX)
        section.add_row(s.BEAM_PILLARS, self._pillar_ids, s.BEAM_PILLARS_HINT)
        section.add_row(s.BEAM_REFERENCE, self._reference)
        section.add_row(s.BEAM_WIDTH, self._width)
        section.add_row(s.BEAM_ALIGNMENT, self._alignment)
        section.add_widget(self._has_wall)
        section.add_widget(self.wall)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(section)
        for field in (self._pillar_ids, self._reference):
            field.returnPressed.connect(self.submit_requested)

    def include(self, session: ProjectSession) -> str:
        record = session.add_beam(
            self._pillar_ids.text(),
            self._reference.text(),
            self._width.value(),
            selected_key(self._alignment) or "",
            self.wall.record() if self._has_wall.isChecked() else None,
        )
        return record.id

    def focus_first(self) -> None:
        self._pillar_ids.setFocus()
        self._pillar_ids.selectAll()
