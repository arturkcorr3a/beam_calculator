"""ResultWindows: at most one summary, one quantities and one detail window per element."""

from PySide6.QtWidgets import QWidget

from pavement_ui.core.results.outcomes import DesignSuccess
from pavement_ui.core.session import ProjectSession
from pavement_ui.presentation.results.beam.beam_detail_window import BeamDetailWindow
from pavement_ui.presentation.results.quantities.quantities_window import (
    QuantitiesWindow,
)
from pavement_ui.presentation.results.slab.slab_detail_window import SlabDetailWindow
from pavement_ui.presentation.results.summary.results_window import ResultsWindow
from pavement_ui.presentation.session_bridge import QtSessionBridge
from pavement_ui.presentation.text.strings.common import UNTITLED


def _show(window: QWidget) -> None:
    window.show()
    window.raise_()
    window.activateWindow()


class ResultWindows:
    """Open, raise, refresh and close the results windows (docs/UI_SPEC.md §10)

    After each finished design the open windows show the new results; a detail
    whose element no longer exists is closed. Without results (failed design,
    new or opened project) every results window is closed.
    """

    def __init__(
        self, session: ProjectSession, bridge: QtSessionBridge, parent: QWidget
    ) -> None:
        self._session = session
        self._parent = parent
        self._summary: ResultsWindow | None = None
        self._quantities: QuantitiesWindow | None = None
        self._beams: dict[str, BeamDetailWindow] = {}
        self._slabs: dict[str, SlabDetailWindow] = {}
        bridge.design_finished.connect(self._on_design_finished)

    def _file_name(self) -> str:
        path = self._session.current_path
        return path.name if path is not None else UNTITLED

    def open_summary(self) -> None:
        success = self._session.last_success
        if success is None:
            return
        if self._summary is None:
            self._summary = ResultsWindow(
                self.open_beam, self.open_slab, self.open_quantities, self._parent
            )
        self._summary.set_results(success, self._file_name())
        _show(self._summary)

    def open_quantities(self) -> None:
        success = self._session.last_success
        if success is None:
            return
        if self._quantities is None:
            self._quantities = QuantitiesWindow(self._parent)
        self._quantities.set_results(success.quantities, self._file_name())
        _show(self._quantities)

    def open_beam(self, beam_id: str) -> None:
        success = self._session.last_success
        result = (
            next((b for b in success.beams if b.beam_id == beam_id), None)
            if success
            else None
        )
        if success is None or result is None:
            return
        window = self._beams.get(beam_id)
        if window is None:
            window = self._beams[beam_id] = BeamDetailWindow(
                result, success, self._parent
            )
        _show(window)

    def open_slab(self, slab_id: str) -> None:
        success = self._session.last_success
        result = (
            next((r for r in success.slabs if r.slab_id == slab_id), None)
            if success
            else None
        )
        if result is None:
            return
        window = self._slabs.get(slab_id)
        if window is None:
            window = self._slabs[slab_id] = SlabDetailWindow(result, self._parent)
        _show(window)

    def _on_design_finished(self) -> None:
        success = self._session.last_success
        if success is None:
            self.close_all()
            return
        self._refresh(success)

    def _refresh(self, success: DesignSuccess) -> None:
        if self._summary is not None:
            self._summary.set_results(success, self._file_name())
        if self._quantities is not None:
            self._quantities.set_results(success.quantities, self._file_name())
        beams = {b.beam_id: b for b in success.beams}
        for beam_id in list(self._beams):
            if beam_id in beams:
                self._beams[beam_id].set_result(beams[beam_id], success)
            else:
                self._beams.pop(beam_id).close()
        slabs = {r.slab_id: r for r in success.slabs}
        for slab_id in list(self._slabs):
            if slab_id in slabs:
                self._slabs[slab_id].set_result(slabs[slab_id])
            else:
                self._slabs.pop(slab_id).close()

    def close_all(self) -> None:
        for window in (*self._beams.values(), *self._slabs.values()):
            window.close()
        self._beams.clear()
        self._slabs.clear()
        if self._summary is not None:
            self._summary.close()
        if self._quantities is not None:
            self._quantities.close()
