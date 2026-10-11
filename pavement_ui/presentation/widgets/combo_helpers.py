"""Combo boxes whose items carry stable keys as item data."""

from collections.abc import Callable, Sequence

from PySide6.QtWidgets import QComboBox


def fill_combo(
    combo: QComboBox, keys: Sequence[str], label_of: Callable[[str], str]
) -> None:
    """Replace the items: one per key, shown with its label, keeping the key as data

    The current key is kept when it is still available, otherwise the first
    item is selected. ``currentIndexChanged`` is emitted exactly once, so
    dependent fields always refresh.
    """
    previous = selected_key(combo)
    combo.blockSignals(True)
    combo.clear()
    for key in keys:
        combo.addItem(label_of(key), key)
    index = combo.findData(previous) if previous is not None else -1
    if index < 0:
        index = 0 if keys else -1
    combo.setCurrentIndex(index)
    combo.blockSignals(False)
    combo.currentIndexChanged.emit(combo.currentIndex())


def selected_key(combo: QComboBox) -> str | None:
    """Key of the current item, or None if the combo is empty"""
    data = combo.currentData()
    return data if isinstance(data, str) else None


def select_key(combo: QComboBox, key: str) -> bool:
    """Select the item of key; False if it is not in the combo"""
    index = combo.findData(key)
    if index < 0:
        return False
    combo.setCurrentIndex(index)
    return True
