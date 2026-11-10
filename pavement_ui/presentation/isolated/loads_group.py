"""Cargas: the list of loads on the beam, added, edited and removed with dialogs."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pavement_ui.core.model.isolated_beam_input import (
    CustomLoad,
    IsolatedLoadInput,
    OwnWeightLoad,
    WallLoad,
)
from pavement_ui.core.options import EngineOptions
from pavement_ui.core.ports import IsolatedBeamEngine
from pavement_ui.presentation.formatting.numbers import fmt_number
from pavement_ui.presentation.isolated import load_rows
from pavement_ui.presentation.isolated.custom_load_dialog import CustomLoadDialog
from pavement_ui.presentation.isolated.wall_load_dialog import WallLoadDialog
from pavement_ui.presentation.text.strings import isolated as s

_TABLE_HEIGHT_PX = 180
_FIRST_NUMBER_COL = 2  # g and q
_NUMBER_ALIGN = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter


def _button(text: str, name: str) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName(name)
    return button


class LoadsGroup(QGroupBox):
    """Table Carga · Vão · g · q, with live values, and its buttons

    Own weight is at most once and always on every span, so it has no dialog.

    Signals:
        changed: A load was added, edited or removed.
    """

    changed = Signal()

    def __init__(
        self,
        engine: IsolatedBeamEngine,
        options: EngineOptions,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(s.LOADS, parent)
        self._engine, self._options = engine, options
        self._loads: list[IsolatedLoadInput] = [OwnWeightLoad()]
        self._section = (14.0, 40.0)  # b, h (cm)
        self._span_count = 1
        self._wall_height_m = 2.5
        self._table = QTableWidget(0, 4)
        self._table.setObjectName("isoLoads")
        self._table.setHorizontalHeaderLabels(
            [s.COL_LOAD, s.COL_LOAD_SPAN, s.COL_G, s.COL_Q]
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setFixedHeight(_TABLE_HEIGHT_PX)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._own = _button(s.ADD_OWN_WEIGHT, "isoAddOwnWeight")
        self._edit = _button(s.EDIT_LOAD, "isoEditLoad")
        self._remove = _button(s.REMOVE_LOAD, "isoRemoveLoad")
        wall = _button(s.ADD_WALL, "isoAddWall")
        custom = _button(s.ADD_CUSTOM, "isoAddCustom")
        hint = QLabel(s.LOADS_HINT)
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        buttons = QGridLayout()
        for index, button in enumerate(
            (self._own, wall, custom, self._edit, self._remove)
        ):
            buttons.addWidget(button, index // 3, index % 3)
        layout = QVBoxLayout(self)
        layout.addWidget(self._table)
        layout.addLayout(buttons)
        layout.addWidget(hint)
        self._own.clicked.connect(lambda: self._add(OwnWeightLoad()))
        wall.clicked.connect(lambda: self._open(None, WallLoad))
        custom.clicked.connect(lambda: self._open(None, CustomLoad))
        self._edit.clicked.connect(self._edit_selected)
        self._remove.clicked.connect(self._remove_selected)
        self._table.itemSelectionChanged.connect(self._update_buttons)
        self._table.cellDoubleClicked.connect(lambda: self._edit_selected())
        self._refresh()

    def loads(self) -> tuple[IsolatedLoadInput, ...]:
        return tuple(self._loads)

    def span_totals(self) -> list[load_rows.LoadValues]:
        """g and q on each span (kN/m)"""
        return load_rows.span_totals(self._loads, self._values(), self._span_count)

    def set_section(self, width_cm: float, height_cm: float) -> None:
        self._section = (width_cm, height_cm)
        self._refresh()

    def set_span_count(self, count: int) -> None:
        """Keep the loads of the remaining spans; drop those only on removed ones"""
        self._span_count = count
        self._loads = [
            load
            for load in self._loads
            if load.span_index is None or load.span_index < count
        ]
        self._refresh()

    def set_wall_height(self, height_m: float) -> None:
        """Height of a new wall: the project's ceiling height (m)"""
        self._wall_height_m = height_m

    def _values(self) -> list[load_rows.LoadValues]:
        return [
            load_rows.load_values(load, self._engine, *self._section)
            for load in self._loads
        ]

    def _selected(self) -> int | None:
        rows = self._table.selectionModel().selectedRows()
        return rows[0].row() if rows else None

    def _add(self, load: IsolatedLoadInput) -> None:
        self._loads.append(load)
        self._refresh(len(self._loads) - 1)
        self.changed.emit()

    def _open(self, row: int | None, kind: type[WallLoad] | type[CustomLoad]) -> None:
        """Add (row None) or edit a wall or custom load through its dialog"""
        current = None if row is None else self._loads[row]
        if kind is WallLoad:
            wall = current if isinstance(current, WallLoad) else None
            dialog = WallLoadDialog(
                wall, self._wall_height_m, self._options, self._span_count, self
            )
        else:
            custom = (
                current
                if isinstance(current, CustomLoad)
                else CustomLoad(s.LOAD_LABEL_DEFAULT, 1.0)
            )
            dialog = CustomLoadDialog(custom, self._span_count, self)
        if not dialog.exec():
            return
        if row is None:
            self._add(dialog.load())
            return
        self._loads[row] = dialog.load()
        self._refresh(row)
        self.changed.emit()

    def _edit_selected(self) -> None:
        row = self._selected()
        if row is None:
            return
        load = self._loads[row]
        if isinstance(load, WallLoad):
            self._open(row, WallLoad)
        elif isinstance(load, CustomLoad):
            self._open(row, CustomLoad)

    def _remove_selected(self) -> None:
        row = self._selected()
        if row is None:
            return
        del self._loads[row]
        self._refresh(min(row, len(self._loads) - 1))
        self.changed.emit()

    def _refresh(self, select: int | None = None) -> None:
        self._table.setRowCount(len(self._loads))
        for row, (load, value) in enumerate(
            zip(self._loads, self._values(), strict=True)
        ):
            texts = (
                load_rows.description(load),
                load_rows.scope(load),
                fmt_number(value.g_kn_m, 2),
                fmt_number(value.q_kn_m, 2),
            )
            for col, text in enumerate(texts):
                item = QTableWidgetItem(text)
                item.setToolTip(text)
                if col >= _FIRST_NUMBER_COL:
                    item.setTextAlignment(_NUMBER_ALIGN)
                self._table.setItem(row, col, item)
        if select is not None and select >= 0:
            self._table.selectRow(select)
        self._update_buttons()

    def _update_buttons(self) -> None:
        row = self._selected()
        self._own.setEnabled(
            not any(isinstance(load, OwnWeightLoad) for load in self._loads)
        )
        self._remove.setEnabled(row is not None)
        self._edit.setEnabled(
            row is not None and not isinstance(self._loads[row], OwnWeightLoad)
        )
