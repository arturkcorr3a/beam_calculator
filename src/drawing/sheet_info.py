"""Sheet data that the DetailingBeam does not hold; the only drawing module that reads APP_CONFIG"""

import datetime
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from src.config import APP_CONFIG
from src.drawing.formatting import fmt_roman

TIME_ZONE = ZoneInfo("America/Sao_Paulo")


@dataclass(frozen=True)
class SheetInfo:
    """What the notes and the title block show besides the beams

    Attributes:
        concrete: Concrete class (C30), or None when unknown.
        exposure_class: Environmental aggressiveness class in Roman numerals (II), or None when unknown.
        pavement_name: Name of the pavement, shown as the project's name, or None without one.
        date: Day the sheet is generated, in the Brasília time zone.
        sheet_number: Number of this sheet among the exported ones, from 1.
        sheet_total: Number of sheets exported together.
    """

    concrete: str
    exposure_class: str
    pavement_name: str | None
    date: datetime.date
    sheet_number: int = 1
    sheet_total: int = 1


def read_sheet_info(
    pavement_name: str | None = None, sheet_number: int = 1, sheet_total: int = 1
) -> SheetInfo:
    """Return the sheet data, reading the concrete and the exposure class from APP_CONFIG

    Args:
        pavement_name: Name of the pavement, such as the example or saved file's name.
        sheet_number: Number of the sheet among the exported ones, from 1.
        sheet_total: Number of sheets exported together.
    """
    return SheetInfo(
        concrete=APP_CONFIG.pavement_concrete.name,
        exposure_class=fmt_roman(int(APP_CONFIG.exposure_class)),
        pavement_name=pavement_name,
        date=datetime.datetime.now(TIME_ZONE).date(),
        sheet_number=sheet_number,
        sheet_total=sheet_total,
    )
