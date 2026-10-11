"""ResultsWindow: summary of a successful design (mockup A6)."""

from collections.abc import Callable, Sequence

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pavement_ui.core.results.beam_result import BeamResult
from pavement_ui.core.results.outcomes import DesignSuccess
from pavement_ui.core.results.slab_result import SlabResult
from pavement_ui.presentation.formatting.elements import fmt_count
from pavement_ui.presentation.results.summary.details_button_delegate import (
    DetailsButtonDelegate,
)
from pavement_ui.presentation.results.summary.summary_columns import (
    BEAM_SUMMARY,
    SLAB_SUMMARY,
)
from pavement_ui.presentation.text.strings import formatting as fs
from pavement_ui.presentation.text.strings import results as s
from pavement_ui.presentation.theme import tokens
from pavement_ui.presentation.widgets.banner import Banner
from pavement_ui.presentation.widgets.column_table_model import (
    ColumnSpec,
    ColumnTableModel,
)
from pavement_ui.presentation.widgets.read_only_table import ReadOnlyTable

_SIZE_PX = (1280, 800)
type OpenDetail = Callable[[str], None]


def _table[T](
    columns: Sequence[ColumnSpec[T]],
    name: str,
    ids: Callable[[T], str],
    open_detail: OpenDetail,
) -> tuple[ReadOnlyTable, ColumnTableModel[T]]:
    """A summary table whose button column and double-clicks open the detail of a row."""
    table = ReadOnlyTable()
    table.setObjectName(name)
    model = ColumnTableModel[T](columns, table)
    table.setModel(model)
    delegate = DetailsButtonDelegate(table)
    table.setItemDelegateForColumn(len(columns) - 1, delegate)

    def open_row(row: int) -> None:
        open_detail(ids(model.row_at(row)))

    def open_index(index: QModelIndex) -> None:
        open_row(index.row())

    delegate.clicked.connect(open_row)
    table.doubleClicked.connect(open_index)
    return table, model


class ResultsWindow(QWidget):
    """Success band, beams and slabs tables (each row opens its detail), Fechar"""

    def __init__(
        self,
        open_beam: OpenDetail,
        open_slab: OpenDetail,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setObjectName("resultsWindow")
        self.resize(*_SIZE_PX)
        self.banner = Banner()
        beams, self._beams = _table(
            BEAM_SUMMARY, "resultsBeamTable", lambda b: b.beam_id, open_beam
        )
        slabs, self._slabs = _table(
            SLAB_SUMMARY, "resultsSlabTable", lambda r: r.slab_id, open_slab
        )
        self._beams_group = QGroupBox()
        QVBoxLayout(self._beams_group).addWidget(beams)
        self._slabs_group = QGroupBox()
        QVBoxLayout(self._slabs_group).addWidget(slabs)
        hint = QLabel(s.SUMMARY_HINT)
        hint.setObjectName("hint")
        close = QPushButton(s.CLOSE)
        close.clicked.connect(self.close)
        footer = QHBoxLayout()
        footer.addWidget(hint, 1)
        footer.addWidget(close)
        layout = QVBoxLayout(self)
        margin = tokens.MARGIN_PX * 2
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.addWidget(self.banner)
        layout.addWidget(self._beams_group, 3)
        layout.addWidget(self._slabs_group, 2)
        layout.addLayout(footer)

    def set_results(self, success: DesignSuccess, file_name: str) -> None:
        self.setWindowTitle(s.SUMMARY_TITLE.format(file=file_name))
        beams = fmt_count(len(success.beams), fs.BEAM_SINGULAR, fs.BEAM_PLURAL)
        slabs = fmt_count(len(success.slabs), fs.SLAB_SINGULAR, fs.SLAB_PLURAL)
        self.banner.show_message(
            "ok", s.SUMMARY_DONE, s.SUMMARY_COUNTS.format(beams=beams, slabs=slabs)
        )
        self._beams_group.setTitle(s.SUMMARY_BEAMS.format(n=len(success.beams)))
        self._slabs_group.setTitle(s.SUMMARY_SLABS.format(n=len(success.slabs)))
        rows_beams: Sequence[BeamResult] = success.beams
        rows_slabs: Sequence[SlabResult] = success.slabs
        self._beams.set_rows(rows_beams)
        self._slabs.set_rows(rows_slabs)
