"""Fields of a new pillar."""

from PySide6.QtWidgets import QVBoxLayout, QWidget

from pavement_ui.core.session import ProjectSession
from pavement_ui.presentation.panels.element_form import ElementForm
from pavement_ui.presentation.text.strings import panels as s
from pavement_ui.presentation.widgets.form_section import FormSection
from pavement_ui.presentation.widgets.unit_spin_box import UnitSpinBox

_LABEL_WIDTH_PX = 140
_COORD_LIMIT_M = 10_000.0
# Below the engine's 14 cm on purpose: the engine refuses with the normative message
_SIZE_RANGE_CM = (1.0, 1_000.0)


def _coordinate(name: str) -> UnitSpinBox:
    box = UnitSpinBox(2, -_COORD_LIMIT_M, _COORD_LIMIT_M, s.UNIT_M, 0.5)
    box.setObjectName(name)
    return box


def _size(name: str, default_cm: float) -> UnitSpinBox:
    box = UnitSpinBox(1, *_SIZE_RANGE_CM, s.UNIT_CM)
    box.setObjectName(name)
    box.setValue(default_cm)
    return box


class PillarForm(ElementForm):
    """Center coordinates (m) and section dimensions (cm)"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._x = _coordinate("pillarX")
        self._y = _coordinate("pillarY")
        self._width = _size("pillarWidth", 20.0)
        self._depth = _size("pillarDepth", 30.0)
        section = FormSection(s.PILLAR_FORM, _LABEL_WIDTH_PX)
        section.add_row(s.PILLAR_X, self._x)
        section.add_row(s.PILLAR_Y, self._y)
        section.add_row(s.PILLAR_WIDTH, self._width)
        section.add_row(s.PILLAR_DEPTH, self._depth)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(section)
        self._depth.lineEdit().returnPressed.connect(self.submit_requested)

    def include(self, session: ProjectSession) -> str:
        record = session.add_pillar(
            self._x.value(), self._y.value(), self._width.value(), self._depth.value()
        )
        return record.id

    def focus_first(self) -> None:
        self._x.setFocus()
        self._x.selectAll()
