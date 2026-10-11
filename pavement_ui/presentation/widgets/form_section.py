"""A titled group of labeled form rows, each with an optional hint."""

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QSizePolicy,
    QWidget,
)

from pavement_ui.presentation.theme import tokens


class FormSection(QGroupBox):
    """``QGroupBox`` with a form layout: labels on the left, fields on the right

    Args:
        title: Group title.
        label_width_px: Minimum width of the label column; it grows to fit the longest label.
    """

    def __init__(
        self, title: str, label_width_px: int = 140, parent: QWidget | None = None
    ) -> None:
        super().__init__(title, parent)
        self._label_width_px = label_width_px
        self._form = QFormLayout(self)
        self._form.setSpacing(tokens.SPACING_PX)
        self._form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

    def add_row(
        self, label: str, field: QWidget, hint: str | None = None
    ) -> QLabel | None:
        """Add a labeled field; a hint becomes a muted label on the next row

        Returns:
            The hint label (to update its text later), or None without a hint.
        """
        caption = QLabel(label)
        caption.setMinimumWidth(self._label_width_px)  # grows for long labels
        if isinstance(field, QComboBox):  # combos show long labels (masonry, usage)
            field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._form.addRow(caption, field)
        if hint is None:
            return None
        hint_label = QLabel(hint)
        hint_label.setObjectName("hint")
        hint_label.setWordWrap(True)
        hint_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self._form.addRow("", hint_label)
        return hint_label

    def add_widget(self, widget: QWidget) -> None:
        """Add a full-width row (e.g. a nested group or a button line)"""
        self._form.addRow(widget)
