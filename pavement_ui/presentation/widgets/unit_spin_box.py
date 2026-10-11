"""Numeric inputs with a unit suffix, in the pt-BR locale."""

from PySide6.QtCore import QLocale, Qt
from PySide6.QtWidgets import QAbstractSpinBox, QDoubleSpinBox, QSpinBox, QWidget

from pavement_ui.presentation.theme.fonts import mono_font


def _style(box: QAbstractSpinBox) -> None:
    box.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    box.setFont(mono_font())
    box.setLocale(QLocale())
    box.setKeyboardTracking(False)


class UnitSpinBox(QDoubleSpinBox):
    """Decimal input such as "20,0 cm"

    Args:
        decimals: Digits after the comma.
        minimum: Smallest accepted value, in the unit.
        maximum: Largest accepted value, in the unit.
        unit: Unit shown after the value (e.g. "cm"); empty for none.
        step: Increment of the arrows, in the unit.
    """

    def __init__(
        self,
        decimals: int,
        minimum: float,
        maximum: float,
        unit: str = "",
        step: float = 1.0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        _style(self)
        self.setDecimals(decimals)
        self.setRange(minimum, maximum)
        self.setSingleStep(step)
        if unit:
            self.setSuffix(f" {unit}")


class IntUnitSpinBox(QSpinBox):
    """Integer input such as "0 cm"

    Args:
        minimum: Smallest accepted value, in the unit.
        maximum: Largest accepted value, in the unit.
        unit: Unit shown after the value; empty for none.
    """

    def __init__(
        self, minimum: int, maximum: int, unit: str = "", parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        _style(self)
        self.setRange(minimum, maximum)
        if unit:
            self.setSuffix(f" {unit}")
