"""Errors for values missing from the reference tables"""

from src.errors.input import InputError


class TableLookupError(InputError, KeyError):
    """A value is not in a reference table

    Caught as ``KeyError`` (the NBR 6120 lookups) or ``ValueError`` (the
    thickness and price lookups), as the engine raised them before.

    Attributes:
        table: Name of the table (e.g. "ABNT NBR 6120:2019 — Table 2").
        value: The value that was not found; None for a thickness left unset.
    """

    def __init__(self, message: str, *, table: str, value: str | float | None) -> None:
        super().__init__(message)
        self.table = table
        self.value = value


class SteelPriceNotFoundError(TableLookupError):
    """SINAPI has no price for a bar grade and diameter

    Attributes:
        steel: Name of the steel (e.g. "CA50").
        diameter_mm: Bar diameter (mm).
    """

    def __init__(self, *, steel: str, diameter_mm: float) -> None:
        super().__init__(
            f"No SINAPI price for {steel} φ{diameter_mm:g} mm.",
            table="SINAPI 10/2026 — steel prices",
            value=diameter_mm,
        )
        self.steel = steel
        self.diameter_mm = diameter_mm
