"""Status bar: validation state, element counts, cursor position, config summary."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QLabel, QStatusBar, QWidget

from pavement_ui.core.session import ProjectSession
from pavement_ui.core.state import ValidationStatus
from pavement_ui.presentation.formatting.elements import fmt_counts
from pavement_ui.presentation.formatting.numbers import fmt_number
from pavement_ui.presentation.text.error_translation import translate
from pavement_ui.presentation.text.option_labels import OptionKind, label
from pavement_ui.presentation.text.strings import main_window as s
from pavement_ui.presentation.theme import tokens

_VALIDATION_WIDTH_PX = 420


class MainStatusBar(QStatusBar):
    """Re-reads the session on demand; ``MainWindow`` decides when"""

    def __init__(self, session: ProjectSession, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._session = session
        self._busy = False
        self._validation = QLabel()
        self._validation.setObjectName("statusValidation")
        self._validation.setFixedWidth(_VALIDATION_WIDTH_PX)
        self._counts = QLabel()
        self._cursor = QLabel()
        self._config = QLabel()
        self.addWidget(self._validation)
        self.addWidget(self._counts, 1)
        self.addPermanentWidget(self._cursor)
        self.addPermanentWidget(self._config)
        self.refresh()

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.refresh()

    def set_cursor_m(self, x_m: float | None, y_m: float | None) -> None:
        """Show the plan cursor position (m), or nothing when outside the plan"""
        if x_m is None or y_m is None:
            self._cursor.clear()
            return
        self._cursor.setText(
            s.STATUS_CURSOR.format(x=fmt_number(x_m, 2), y=fmt_number(y_m, 2))
        )

    def refresh(self) -> None:
        self._refresh_validation()
        self._counts.setText(fmt_counts(self._session.records.counts()))
        config = self._session.config
        self._config.setText(
            s.STATUS_CONFIG.format(
                concrete=config.concrete_key,
                steel=config.steel_key,
                category=label(OptionKind.CATEGORY, config.building_category_key),
                height=fmt_number(config.ceiling_height_m, 2),
            )
        )

    def _refresh_validation(self) -> None:
        validation = self._session.validation
        color, tooltip = tokens.TEXT, ""
        if self._busy:
            text = s.STATUS_DESIGNING
        elif validation.status is ValidationStatus.VALID:
            text, color = s.STATUS_VALID, tokens.OK
        elif validation.status is ValidationStatus.INVALID:
            tooltip = translate(validation.message or "")
            text, color = s.STATUS_INVALID.format(message=tooltip), tokens.ERROR
        else:
            text = s.STATUS_NOT_VALIDATED
        metrics = QFontMetrics(self._validation.font())
        self._validation.setText(
            metrics.elidedText(text, Qt.TextElideMode.ElideRight, _VALIDATION_WIDTH_PX)
        )
        self._validation.setToolTip(tooltip)
        self._validation.setStyleSheet(f"color: {color};")
