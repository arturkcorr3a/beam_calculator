"""Add or edit a custom load: description, value, g or q and ψ2."""

from PySide6.QtWidgets import QComboBox, QLineEdit, QWidget

from pavement_ui.core.model.isolated_beam_input import CustomLoad
from pavement_ui.presentation.isolated.load_dialog import LoadDialog
from pavement_ui.presentation.text.strings import isolated as s
from pavement_ui.presentation.widgets.unit_spin_box import UnitSpinBox


class CustomLoadDialog(LoadDialog):
    """ψ2 is enabled only for a variable load"""

    def __init__(
        self, load: CustomLoad, span_count: int, parent: QWidget | None = None
    ) -> None:
        super().__init__(s.CUSTOM_DIALOG, span_count, load.span_index, parent)
        self.setObjectName("isoCustomLoadDialog")
        self._label = QLineEdit(load.label)
        self._label.setObjectName("isoLoadLabel")
        self._value = UnitSpinBox(2, 0.0, 1000.0, s.UNIT_KN_M)
        self._value.setObjectName("isoLoadValue")
        self._value.setValue(load.value_kn_m)
        self._kind = QComboBox()
        self._kind.setObjectName("isoLoadKind")
        self._kind.addItem(s.LOAD_PERMANENT, False)
        self._kind.addItem(s.LOAD_VARIABLE, True)
        self._kind.setCurrentIndex(1 if load.variable else 0)
        self._psi_2 = UnitSpinBox(2, 0.0, 1.0, "", 0.1)
        self._psi_2.setObjectName("isoLoadPsi2")
        self._psi_2.setValue(load.psi_2)
        self.form.add_row(s.LOAD_LABEL, self._label)
        self.form.add_row(s.LOAD_VALUE, self._value)
        self.form.add_row(s.LOAD_KIND, self._kind)
        self.form.add_row(s.LOAD_PSI_2, self._psi_2, s.LOAD_PSI_2_HINT)
        self.add_scope_row()
        self._kind.currentIndexChanged.connect(self._on_kind)
        self._on_kind()

    def _variable(self) -> bool:
        return bool(self._kind.currentData())

    def _on_kind(self) -> None:
        self._psi_2.setEnabled(self._variable())

    def load(self) -> CustomLoad:
        """The load as edited"""
        return CustomLoad(
            label=self._label.text().strip() or s.LOAD_LABEL_DEFAULT,
            value_kn_m=self._value.value(),
            variable=self._variable(),
            psi_2=self._psi_2.value(),
            span_index=self.span_index,
        )
