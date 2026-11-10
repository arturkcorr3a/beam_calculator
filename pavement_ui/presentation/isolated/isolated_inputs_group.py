"""Seção: width and height of the isolated beam."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from pavement_ui.presentation.text.strings import isolated as s
from pavement_ui.presentation.text.strings import panels as units
from pavement_ui.presentation.widgets.form_section import FormSection
from pavement_ui.presentation.widgets.unit_spin_box import UnitSpinBox

_LABEL_WIDTH_PX = 120


def _spin(
    name: str, decimals: int, limits: tuple[float, float], unit: str, value: float
) -> UnitSpinBox:
    box = UnitSpinBox(decimals, *limits, unit)
    box.setObjectName(name)
    box.setValue(value)
    return box


class IsolatedInputsGroup(FormSection):
    """Signals:
    changed: b or h was edited.
    """

    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(s.SECTION, _LABEL_WIDTH_PX, parent)
        # the engine refuses b < 12 cm with its own message; the field allows less
        self._width = _spin("isoWidth", 1, (1.0, 200.0), units.UNIT_CM, 14.0)
        self._height = _spin("isoHeight", 1, (0.1, 300.0), units.UNIT_CM, 40.0)
        self.add_row(s.WIDTH, self._width)
        self.add_row(s.HEIGHT, self._height)
        for box in (self._width, self._height):
            box.valueChanged.connect(self.changed)

    @property
    def width_cm(self) -> float:
        return self._width.value()

    @property
    def height_cm(self) -> float:
        return self._height.value()
