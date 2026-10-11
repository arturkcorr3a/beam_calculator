"""A panel with a header bar (title, hint, tools on the right) and a body."""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from pavement_ui.presentation.theme import tokens


class TitledPanel(QFrame):
    """Framed panel: header with a bold title and optional tools, then the body widget"""

    def __init__(
        self, title: str, body: QWidget, hint: str = "", parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("titledPanel")
        self.setStyleSheet(
            f"#titledPanel {{ background: {tokens.SURFACE}; border: 1px solid {tokens.BORDER};"
            f" border-radius: {tokens.RADIUS_PX}px; }}"
        )
        self._title = QLabel(f"<b>{title}</b>")
        self._tools = QHBoxLayout()
        header = QHBoxLayout()
        header.addWidget(self._title)
        if hint:
            hint_label = QLabel(hint)
            hint_label.setObjectName("hint")
            header.addWidget(hint_label)
        header.addStretch(1)
        header.addLayout(self._tools)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            tokens.MARGIN_PX, tokens.MARGIN_PX, tokens.MARGIN_PX, tokens.MARGIN_PX
        )
        layout.addLayout(header)
        layout.addWidget(body, 1)

    def add_tool(self, widget: QWidget) -> None:
        """Add a widget (button, combo) to the right side of the header"""
        self._tools.addWidget(widget)

    def set_title(self, title: str) -> None:
        self._title.setText(f"<b>{title}</b>")
