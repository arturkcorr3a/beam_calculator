"""A bordered "key value" label for detail-window headers (e.g. "bw 14 cm")."""

from PySide6.QtWidgets import QLabel, QWidget

from pavement_ui.presentation.theme import tokens


class ValueChip(QLabel):
    """Muted key followed by its value, inside a rounded border"""

    def __init__(self, key: str, value: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"border: 1px solid {tokens.BORDER}; border-radius: {tokens.RADIUS_PX}px;"
            f" background: {tokens.SURFACE}; padding: 2px 8px;"
        )
        self.set_value(key, value)

    def set_value(self, key: str, value: str) -> None:
        self.setText(f'<span style="color:{tokens.TEXT_MUTED}">{key}</span> {value}')
