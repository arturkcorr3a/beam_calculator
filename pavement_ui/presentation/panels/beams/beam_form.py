"""Fields of a new continuous beam."""

from collections.abc import Sequence

from PySide6.QtWidgets import QCheckBox, QComboBox, QVBoxLayout, QWidget

from pavement_ui.core.model.records import PillarRecord
from pavement_ui.core.options import EngineOptions
from pavement_ui.core.session import ProjectSession
from pavement_ui.presentation.panels.beams.wall_form import WallForm
from pavement_ui.presentation.panels.element_form import ElementForm
from pavement_ui.presentation.text.option_labels import OptionKind, label
from pavement_ui.presentation.text.strings import panels as s
from pavement_ui.presentation.widgets.combo_helpers import fill_combo, selected_key
from pavement_ui.presentation.widgets.form_section import FormSection
from pavement_ui.presentation.widgets.pillar_checklist import PillarChecklist
from pavement_ui.presentation.widgets.unit_spin_box import UnitSpinBox

_LABEL_WIDTH_PX = 132


class BeamForm(ElementForm):
    """Supporting pillars (checked), reference pillar, bw, alignment and the wall on top"""

    def __init__(self, options: EngineOptions, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pillars = PillarChecklist()
        self._pillars.setObjectName("beamPillars")
        self._pillars.checked_changed.connect(self._refresh_reference)
        # the engine requires the reference to be one of the beam's pillars
        self._reference = QComboBox()
        self._reference.setObjectName("beamReference")
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
        self._pillars_hint = section.add_row(
            s.BEAM_PILLARS, self._pillars, s.BEAM_PILLARS_HINT
        )
        section.add_row(s.BEAM_REFERENCE, self._reference)
        section.add_row(s.BEAM_WIDTH, self._width)
        section.add_row(s.BEAM_ALIGNMENT, self._alignment)
        section.add_widget(self._has_wall)
        section.add_widget(self.wall)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(section)

    def set_pillars(self, pillars: Sequence[PillarRecord]) -> None:
        """Offer the registered pillars; removed ones lose their check"""
        self._pillars.set_pillars(pillars)
        if self._pillars_hint is not None:
            self._pillars_hint.setText(
                s.BEAM_PILLARS_HINT if pillars else s.NO_PILLARS_HINT
            )

    def _refresh_reference(self) -> None:
        ids = self._pillars.checked_ids()
        fill_combo(self._reference, ids, lambda pillar_id: pillar_id)

    def include(self, session: ProjectSession) -> str:
        record = session.add_beam(
            self._pillars.checked_ids(),
            selected_key(self._reference) or "",
            self._width.value(),
            selected_key(self._alignment) or "",
            self.wall.record() if self._has_wall.isChecked() else None,
        )
        return record.id

    def focus_first(self) -> None:
        self._pillars.setFocus()
