"""A colored band with an icon, a bold title and a text (success, error, warning)."""

from typing import Literal

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from pavement_ui.presentation.theme import tokens
from pavement_ui.presentation.theme.icons import IconName, icon

type BannerKind = Literal["ok", "error", "warning"]

_STYLES: dict[BannerKind, tuple[str, str, IconName]] = {
    "ok": (tokens.OK, tokens.OK_BG, "ok"),
    "error": (tokens.ERROR, tokens.ERROR_BG, "error"),
    "warning": (tokens.WARNING, tokens.WARNING_BG, "warning"),
}
_ICON_SIZE_PX = 20


class Banner(QFrame):
    """Status band, e.g. "Dimensionamento concluído." on a green background"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._icon = QLabel()
        self._text = QLabel()
        self._text.setWordWrap(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            tokens.MARGIN_PX, tokens.MARGIN_PX, tokens.MARGIN_PX, tokens.MARGIN_PX
        )
        layout.addWidget(self._icon)
        layout.addWidget(self._text, 1)

    def show_message(self, kind: BannerKind, title: str, text: str = "") -> None:
        """Show a bold title and an optional text in the colors of kind"""
        color, background, icon_name = _STYLES[kind]
        self.setStyleSheet(
            f"Banner {{ background: {background}; border: 1px solid {color};"
            f" border-radius: {tokens.RADIUS_PX}px; }}"
            f" QLabel {{ color: {color}; }}"
        )
        self._icon.setPixmap(
            icon(icon_name, color).pixmap(_ICON_SIZE_PX, _ICON_SIZE_PX)
        )
        self._text.setText(f"<b>{title}</b> {text}".strip())
