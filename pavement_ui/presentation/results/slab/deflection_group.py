"""The ELS-DEF verification of the slab (NBR 6118 §17.3.2)."""

from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QWidget

from pavement_ui.core.results.slab_result import DeflectionCheck
from pavement_ui.presentation.formatting.numbers import fmt_number
from pavement_ui.presentation.results.slab.slab_texts import cm
from pavement_ui.presentation.text.strings import results as s
from pavement_ui.presentation.theme import tokens
from pavement_ui.presentation.widgets.key_value_table import KeyValue, KeyValueTable


class DeflectionGroup(QGroupBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(s.DEFLECTION, parent)
        self._table = KeyValueTable()
        self._table.setObjectName("slabDeflectionTable")
        QVBoxLayout(self).addWidget(self._table)

    def set_check(self, check: DeflectionCheck) -> None:
        moment = s.KNM_M_VALUE
        self._table.set_items(
            [
                (s.ROW_H, cm(check.h_cm)),
                (s.ROW_D, cm(check.d_cm, 1)),
                (s.ROW_CASE, str(check.support_case)),
                (s.ROW_MS, moment.format(value=fmt_number(check.ms_knm_m, 2))),
                (s.ROW_MR, moment.format(value=fmt_number(check.mr_knm_m, 2))),
                (s.ROW_STAGE, s.STAGE_II if check.cracked else s.STAGE_I),
                (
                    s.ROW_INERTIA,
                    s.CM4_M_VALUE.format(value=fmt_number(check.inertia_eq_cm4_m, 0)),
                ),
                (s.ROW_IMMEDIATE, cm(check.immediate_deflection_cm, 2)),
                (s.ROW_LONG_TERM, cm(check.long_term_deflection_cm, 2)),
                (s.ROW_LIMIT, cm(check.limit_cm, 2)),
                KeyValue(
                    s.ROW_VERDICT,
                    s.PASSES if check.passes else s.FAILS,
                    tokens.OK if check.passes else tokens.ERROR,
                ),
            ]
        )
