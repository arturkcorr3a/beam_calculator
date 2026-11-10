"""Base of the load dialogs: a form, the span the load acts on, OK and Cancelar."""

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QVBoxLayout,
    QWidget,
)

from pavement_ui.presentation.text.strings import dialogs as d
from pavement_ui.presentation.text.strings import isolated as s
from pavement_ui.presentation.widgets.form_section import FormSection
from pavement_ui.presentation.widgets.variants import set_variant

_Button = QDialogButtonBox.StandardButton
_LABEL_WIDTH_PX = 132
_WIDTH_PX = 460


class LoadDialog(QDialog):
    """Modal dialog; subclasses add their rows to ``form`` and read ``span_index``

    Args:
        span_count: Number of spans of the beam.
        span_index: Zero-based span selected at first; None for every span.
    """

    def __init__(
        self,
        title: str,
        span_count: int,
        span_index: int | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(_WIDTH_PX)
        self.form = FormSection(title, _LABEL_WIDTH_PX)
        self._scope = QComboBox()
        self._scope.setObjectName("isoLoadScope")
        self._scope.addItem(s.ALL_SPANS, None)
        for index in range(span_count):
            self._scope.addItem(s.SPAN_NAME.format(n=index + 1), index)
        found = self._scope.findData(span_index)
        self._scope.setCurrentIndex(max(found, 0))
        self._layout = QVBoxLayout(self)
        self._layout.addWidget(self.form)
        self._layout.addWidget(self._buttons())

    def _buttons(self) -> QDialogButtonBox:
        buttons = QDialogButtonBox(_Button.Ok | _Button.Cancel)
        ok = buttons.button(_Button.Ok)
        ok.setText(d.CONFIG_OK)
        ok.setDefault(True)
        set_variant(ok, "primary")
        buttons.button(_Button.Cancel).setText(d.CANCEL)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        return buttons

    def add_scope_row(self) -> None:
        """Add the "Aplicar no vão" row; call after the subclass rows"""
        self.form.add_row(s.LOAD_SCOPE, self._scope)

    def insert_widget(self, widget: QWidget) -> None:
        """Add a widget above the form (e.g. a nested form section)"""
        self._layout.insertWidget(0, widget)

    @property
    def span_index(self) -> int | None:
        data = self._scope.currentData()
        return data if isinstance(data, int) else None
