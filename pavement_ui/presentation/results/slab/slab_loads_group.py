"""Cargas: permanent, variable and service loads of the slab (kN/m²)."""

from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QWidget

from pavement_ui.core.results.slab_result import SlabResult
from pavement_ui.presentation.formatting.numbers import fmt_number
from pavement_ui.presentation.text.strings import results as s
from pavement_ui.presentation.widgets.key_value_table import KeyValueTable


def _load(value: float) -> str:
    return s.KN_M2_VALUE.format(value=fmt_number(value, 2))


class SlabLoadsGroup(QGroupBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(s.LOADS, parent)
        self._table = KeyValueTable()
        self._table.setObjectName("slabLoadsTable")
        QVBoxLayout(self).addWidget(self._table)

    def set_result(self, result: SlabResult) -> None:
        self._table.set_items(
            [
                (s.ROW_G, _load(result.g_kn_m2)),
                (s.ROW_Q, _load(result.q_kn_m2)),
                (s.ROW_SERVICE, _load(result.service_kn_m2)),
            ]
        )
