"""The wall standing on a beam, with chained masonry → thickness → coating combos.

Only values tabulated in NBR 6120 Table 2 are offered: the engine looks the wall
up only during the calculation, so a free value would fail late (spec §8.5).
"""

from PySide6.QtWidgets import QComboBox, QWidget

from pavement_ui.core.model.records import WallRecord
from pavement_ui.core.options import EngineOptions, MasonryOption, ThicknessOption
from pavement_ui.presentation.formatting.numbers import fmt_length_cm, fmt_number
from pavement_ui.presentation.text.option_labels import OptionKind, label
from pavement_ui.presentation.text.strings import panels as s
from pavement_ui.presentation.widgets.combo_helpers import (
    fill_combo,
    select_key,
    selected_key,
)
from pavement_ui.presentation.widgets.form_section import FormSection

_LABEL_WIDTH_PX = 132
_DEFAULT_MASONRY = "Hollow ceramic block (Horizontal holes - ABNT NBR 15270-1)"
_DEFAULT_THICKNESS_KEY = str(14.0)
_DEFAULT_COATING_KEY = "1"


class WallForm(FormSection):
    """Masonry type, nominal thickness and coating per face"""

    def __init__(self, options: EngineOptions, parent: QWidget | None = None) -> None:
        super().__init__(s.WALL_FORM, _LABEL_WIDTH_PX, parent)
        self._options = options
        self._masonry = self._combo("wallMasonry")
        self._thickness = self._combo("wallThickness")
        self._coating = self._combo("wallCoating")
        self.add_row(s.WALL_MASONRY, self._masonry)
        self.add_row(s.WALL_THICKNESS, self._thickness)
        self._height_hint = self.add_row(s.WALL_COATING, self._coating, "")
        self._masonry.currentIndexChanged.connect(self._reload_thickness)
        self._masonry.currentIndexChanged.connect(
            lambda: self._masonry.setToolTip(self._masonry.currentText())
        )
        self._thickness.currentIndexChanged.connect(self._reload_coating)
        self._reload_masonry()
        self._apply_defaults()

    @staticmethod
    def _combo(name: str) -> QComboBox:
        combo = QComboBox()
        combo.setObjectName(name)
        return combo

    def _apply_defaults(self) -> None:
        select_key(self._masonry, _DEFAULT_MASONRY)
        select_key(self._thickness, _DEFAULT_THICKNESS_KEY)
        select_key(self._coating, _DEFAULT_COATING_KEY)

    def _masonry_option(self) -> MasonryOption | None:
        key = selected_key(self._masonry)
        return next((m for m in self._options.masonry if m.key == key), None)

    def _thickness_option(self) -> ThicknessOption | None:
        masonry, key = self._masonry_option(), selected_key(self._thickness)
        if masonry is None or key is None:
            return None
        return next((t for t in masonry.thicknesses if str(t.nominal_cm) == key), None)

    def _reload_masonry(self) -> None:
        keys = [m.key for m in self._options.masonry]
        fill_combo(self._masonry, keys, lambda key: label(OptionKind.MASONRY, key))

    def _reload_thickness(self) -> None:
        masonry = self._masonry_option()
        nominals = (
            [] if masonry is None else [t.nominal_cm for t in masonry.thicknesses]
        )
        keys = [str(n) for n in nominals]
        fill_combo(
            self._thickness,
            keys,
            lambda key: s.CM_ITEM.format(value=fmt_length_cm(float(key))),
        )

    def _reload_coating(self) -> None:
        thickness = self._thickness_option()
        keys = [] if thickness is None else [str(c) for c in thickness.coatings_cm]
        fill_combo(self._coating, keys, lambda key: s.COATING_ITEM.format(value=key))

    def set_ceiling_height(self, height_m: float) -> None:
        """Update the hint that the wall height is the project's ceiling height"""
        if self._height_hint is not None:
            self._height_hint.setText(
                s.WALL_HEIGHT_HINT.format(height=fmt_number(height_m, 2))
            )

    def set_record(self, record: WallRecord) -> None:
        """Show a wall; values missing from the catalogue keep the current item"""
        select_key(self._masonry, record.masonry_key)
        select_key(self._thickness, str(record.nominal_thickness_cm))
        select_key(self._coating, str(record.coating_cm))

    def record(self) -> WallRecord:
        """The wall as selected (all values come from the engine's catalogue)"""
        thickness = self._thickness_option()
        return WallRecord(
            masonry_key=selected_key(self._masonry) or "",
            nominal_thickness_cm=thickness.nominal_cm if thickness is not None else 0.0,
            coating_cm=int(selected_key(self._coating) or 0),
        )
