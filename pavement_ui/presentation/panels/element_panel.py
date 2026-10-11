"""ElementPanel: a form to include elements, the table of registered ones, and removal."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from pavement_ui.core.errors import EngineRuleError
from pavement_ui.core.model.element_kind import ElementKind
from pavement_ui.core.model.pavement_records import PavementRecords
from pavement_ui.core.session import ProjectSession
from pavement_ui.presentation.dialogs import messages
from pavement_ui.presentation.panels.element_form import ElementForm
from pavement_ui.presentation.session_bridge import QtSessionBridge
from pavement_ui.presentation.theme import tokens
from pavement_ui.presentation.theme.icons import icon
from pavement_ui.presentation.widgets.column_table_model import (
    ColumnSpec,
    ColumnTableModel,
)
from pavement_ui.presentation.widgets.read_only_table import ReadOnlyTable
from pavement_ui.presentation.widgets.variants import set_variant


class _Identified(Protocol):
    @property
    def id(self) -> str: ...


@dataclass(frozen=True, slots=True)
class PanelTexts:
    """Visible texts of one panel"""

    add: str
    hint: str
    list_title: str
    remove: str


class ElementPanel[R: _Identified](QWidget):
    """Include, list and remove one kind of element (docs/UI_SPEC.md §8.3)

    Signals:
        selection_changed: (kind, id or None) when the table selection changes.
    """

    selection_changed = Signal(object, object)

    def __init__(
        self,
        kind: ElementKind,
        form: ElementForm,
        columns: Sequence[ColumnSpec[R]],
        rows_of: Callable[[PavementRecords], Sequence[R]],
        texts: PanelTexts,
        session: ProjectSession,
        bridge: QtSessionBridge,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._kind, self._form, self._rows_of, self._session = (
            kind,
            form,
            rows_of,
            session,
        )
        self._add = QPushButton(texts.add)
        set_variant(self._add, "primary")
        self._remove = QPushButton(icon("trash", tokens.ERROR), texts.remove)
        set_variant(self._remove, "destructive")
        self._model = ColumnTableModel[R](columns, self)
        self._table = ReadOnlyTable()
        self._table.setModel(self._model)
        self._build_layout(texts)
        self._connect(bridge)
        self._refresh()

    def _build_layout(self, texts: PanelTexts) -> None:
        hint = QLabel(texts.hint)
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        add_row = QHBoxLayout()
        add_row.addWidget(hint, 1)
        add_row.addWidget(self._add, 0, Qt.AlignmentFlag.AlignTop)
        remove_row = QHBoxLayout()
        remove_row.addStretch(1)
        remove_row.addWidget(self._remove)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            tokens.MARGIN_PX, tokens.MARGIN_PX, tokens.MARGIN_PX, tokens.MARGIN_PX
        )
        layout.addWidget(self._form)
        layout.addLayout(add_row)
        layout.addWidget(QLabel(f"<b>{texts.list_title}</b>"))
        layout.addWidget(self._table, 1)
        layout.addLayout(remove_row)

    def _connect(self, bridge: QtSessionBridge) -> None:
        self._add.clicked.connect(self._on_add)
        self._form.submit_requested.connect(self._on_add)
        self._form.availability_changed.connect(self._add.setEnabled)
        self._remove.clicked.connect(self._on_remove)
        shortcut = QShortcut(QKeySequence(QKeySequence.StandardKey.Delete), self._table)
        shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
        shortcut.activated.connect(self._on_remove)
        self._table.selectionModel().selectionChanged.connect(self._on_selection)
        self._model.modelReset.connect(self._on_selection)
        bridge.records_changed.connect(self._refresh)

    @property
    def form(self) -> ElementForm:
        return self._form

    def selected_id(self) -> str | None:
        row = self._table.selected_row()
        return None if row is None else self._model.row_at(row).id

    def select_id(self, element_id: str | None) -> None:
        """Select the row of element_id (clears the selection if absent)"""
        ids = [row.id for row in self._model.rows()]
        if element_id in ids:
            self._table.select_row_index(ids.index(element_id))
        else:
            self._table.clearSelection()

    def _refresh(self) -> None:
        selected = self.selected_id()
        self._model.set_rows(self._rows_of(self._session.records))
        self.select_id(selected)
        self._add.setEnabled(self._form.is_available())

    def _on_add(self) -> None:
        if not self._add.isEnabled():
            return
        try:
            new_id = self._form.include(self._session)
        except EngineRuleError as error:
            messages.show_inclusion_error(self, self._kind, error.message)
            return
        self.select_id(new_id)

    def _on_remove(self) -> None:
        element_id = self.selected_id()
        if element_id is not None and self.isEnabled():
            self._session.remove(self._kind, element_id)

    def _on_selection(self) -> None:
        element_id = self.selected_id()
        self._remove.setEnabled(element_id is not None)
        self.selection_changed.emit(self._kind, element_id)
