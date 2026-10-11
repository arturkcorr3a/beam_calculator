"""The live own-weight load of the section, with its formula."""

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from pavement_ui.presentation.formatting.numbers import fmt_number
from pavement_ui.presentation.text.strings import isolated as s
from pavement_ui.presentation.theme import tokens

_CM_PER_M = 100.0
_VALUE_STYLE = f"font-size: 22px; font-weight: 600; color: {tokens.ACCENT};"


class SelfWeightCard(QFrame):
    """ "Carga de peso próprio": value (kN/m) in large type and 25 kN/m³ × b × h"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("isoSelfWeight")
        self.setStyleSheet(
            f"#isoSelfWeight {{ background: {tokens.SURFACE}; border: 1px solid {tokens.BORDER};"
            f" border-radius: {tokens.RADIUS_PX}px; }}"
        )
        title = QLabel(f"<b>{s.SELF_WEIGHT}</b>")
        self.value = QLabel()
        self.value.setStyleSheet(_VALUE_STYLE)
        self.formula = QLabel()
        self.formula.setObjectName("hint")
        layout = QVBoxLayout(self)
        for widget in (title, self.value, self.formula):
            layout.addWidget(widget)

    def set_values(self, weight_kn_m: float, width_cm: float, height_cm: float) -> None:
        """Show the engine's own weight for a b × h section (cm)"""
        self.value.setText(s.SELF_WEIGHT_VALUE.format(value=fmt_number(weight_kn_m, 2)))
        self.formula.setText(
            s.SELF_WEIGHT_FORMULA.format(
                b=fmt_number(width_cm / _CM_PER_M, 2),
                h=fmt_number(height_cm / _CM_PER_M, 2),
            )
        )
