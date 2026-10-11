"""Numbers in the pt-BR locale: decimal comma, dot as thousands separator."""

from PySide6.QtCore import QLocale

_MINUS = "\N{MINUS SIGN}"


def fmt_number(value: float, decimals: int) -> str:
    """Format a number, e.g. ``fmt_number(9.18, 2)`` → "9,18", ``fmt_number(4267, 0)`` → "4.267" """
    text = QLocale().toString(float(value), "f", decimals)
    zero = QLocale().toString(0.0, "f", decimals)
    return zero if text == f"-{zero}" else text  # no "-0,0"


def fmt_signed(value: float, decimals: int) -> str:
    """Format with the typographic minus sign (U+2212), e.g. -45.7 → "−45,7" """
    return fmt_number(value, decimals).replace("-", _MINUS)


def fmt_with_unit(value: float, decimals: int, unit: str) -> str:
    """Format a number followed by its unit, e.g. "2,80 m" """
    return f"{fmt_number(value, decimals)} {unit}"


def fmt_length_cm(value_cm: float) -> str:
    """Format a section dimension (cm): no decimals when whole, else one (e.g. "14", "12,5")"""
    decimals = 0 if float(value_cm).is_integer() else 1
    return fmt_number(value_cm, decimals)
