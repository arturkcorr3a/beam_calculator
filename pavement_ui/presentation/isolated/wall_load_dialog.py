"""Add or edit a wall load: the beam panel's wall form plus the wall height."""

from PySide6.QtWidgets import QWidget

from pavement_ui.core.model.isolated_beam_input import WallLoad
from pavement_ui.core.options import EngineOptions
from pavement_ui.presentation.isolated.load_dialog import LoadDialog
from pavement_ui.presentation.panels.beams.wall_form import WallForm
from pavement_ui.presentation.text.strings import isolated as s
from pavement_ui.presentation.text.strings import panels as units
from pavement_ui.presentation.widgets.unit_spin_box import UnitSpinBox


class WallLoadDialog(LoadDialog):
    """Only tabulated walls (NBR 6120 Table 2) can be chosen, as in the beam panel

    Args:
        load: The wall to edit; None for a new one, with the form's defaults.
        height_m: Wall height of a new wall (m).
    """

    def __init__(
        self,
        load: WallLoad | None,
        height_m: float,
        options: EngineOptions,
        span_count: int,
        parent: QWidget | None = None,
    ) -> None:
        span_index = None if load is None else load.span_index
        super().__init__(s.WALL_DIALOG, span_count, span_index, parent)
        self.setObjectName("isoWallLoadDialog")
        self._wall = WallForm(options)
        self._height = UnitSpinBox(2, 0.01, 20.0, units.UNIT_M, 0.1)
        self._height.setObjectName("isoWallHeight")
        self._height.setValue(height_m)
        if load is not None:
            self._wall.set_record(load.wall)
            self._height.setValue(load.height_m)
        self.form.add_row(s.WALL_HEIGHT, self._height)
        self.add_scope_row()
        self.insert_widget(self._wall)

    def load(self) -> WallLoad:
        """The load as edited"""
        return WallLoad(self._wall.record(), self._height.value(), self.span_index)
