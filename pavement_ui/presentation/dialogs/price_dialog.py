"""Ask the user for a unit price."""

from PySide6.QtWidgets import QInputDialog, QWidget

from pavement_ui.presentation.text.strings import dialogs as s

_MAX_CONCRETE_PRICE = 100_000.0  # R$/m³, only bounds the spin box
_DECIMALS = 2


def ask_concrete_price(parent: QWidget | None) -> float | None:
    """Ask the concrete price (R$/m³), not negative; None if cancelled"""
    dialog = QInputDialog(parent)
    dialog.setWindowTitle(s.BUDGET_TITLE)
    dialog.setLabelText(s.BUDGET_PRICE_LABEL)
    dialog.setInputMode(QInputDialog.InputMode.DoubleInput)
    dialog.setDoubleDecimals(_DECIMALS)
    dialog.setDoubleRange(0.0, _MAX_CONCRETE_PRICE)
    if not dialog.exec():
        return None
    return dialog.doubleValue()
