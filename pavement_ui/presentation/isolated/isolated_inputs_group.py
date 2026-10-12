"""Entradas: length and section of the isolated beam."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from pavement_ui.core.model.isolated_beam_input import IsolatedBeamInput
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
    changed: Any input was edited.
    """

    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(s.INPUTS, _LABEL_WIDTH_PX, parent)
        # the engine refuses b < 12 cm with its own message; the field allows less
        self._length = _spin("isoLength", 2, (0.01, 50.0), units.UNIT_M, 5.0)
        self._width = _spin("isoWidth", 1, (1.0, 200.0), units.UNIT_CM, 14.0)
        self._height = _spin("isoHeight", 1, (0.1, 300.0), units.UNIT_CM, 40.0)
        self.add_row(s.LENGTH, self._length)
        self.add_row(s.WIDTH, self._width)
        self.add_row(s.HEIGHT, self._height)
        for box in (self._length, self._width, self._height):
            box.valueChanged.connect(self.changed)

    def values(self) -> IsolatedBeamInput:
        return IsolatedBeamInput(
            length_m=self._length.value(),
            width_cm=self._width.value(),
            height_cm=self._height.value(),
        )
