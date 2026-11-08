"""Sheet data that the DetailingBeam does not hold; the only drawing module that reads APP_CONFIG"""

import datetime
from dataclasses import dataclass

from src.config import APP_CONFIG
from src.drawing.formatting import fmt_roman


@dataclass(frozen=True)
class SheetInfo:
    """What the notes and the title block show besides the beams

    Attributes:
        concrete: Concrete class (C30), or None when unknown.
        exposure_class: Environmental aggressiveness class in Roman numerals (II), or None when unknown.
        pavement_name: Name of the pavement, or None without one.
        file_name: Name of the DXF file the sheet is written to; empty on screen.
    """

    concrete: str | None
    exposure_class: str | None
    pavement_name: str | None
    date: datetime.date
    file_name: str = ""


def read_sheet_info(pavement_name: str | None = None) -> SheetInfo:
    """Return the sheet data, reading the concrete and the exposure class from APP_CONFIG

    Args:
        pavement_name: Name of the pavement, such as the example or saved file's name.
    """
    return SheetInfo(
        concrete=APP_CONFIG.pavement_concrete.name,
        exposure_class=fmt_roman(int(APP_CONFIG.exposure_class)),
        pavement_name=pavement_name,
        date=datetime.date.today(),
    )
