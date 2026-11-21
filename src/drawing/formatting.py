"""Numbers and labels as they are written on the sheet: decimal comma, no trailing zeros"""

import datetime
import re

PHI = "φ"  # φ, present in Arial and DejaVu Sans

CONSTRUCTION_MARK = "(MONTAGEM)"
SKIN_MARK = "(PELE)"
CLAMP_MARK = "(GRAMPO)"

_WHOLE_TOLERANCE = 0.05  # cm
_TEXT_WIDTH_RATIO = 0.9  # estimated character width over cap height; 0.75 (spec §4.2) undershoots DejaVu Sans
_ROMAN = ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"))


def _comma(text: str) -> str:
    """Swap the decimal point for a comma"""
    return text.replace(".", ",")


def fmt_len(value: float) -> str:
    """Return a length: an integer when within 0.05 of one, else one decimal with a comma

    Args:
        value: Length (cm).
    """
    nearest = round(value)
    if abs(value - nearest) < _WHOLE_TOLERANCE:
        return str(int(nearest))
    return _comma(f"{value:.1f}")


def fmt_dec(value: float, decimals: int = 1) -> str:
    """Return a number with fixed decimals and a comma, for m, kg, m³ and m²"""
    return _comma(f"{value:.{decimals}f}")


def fmt_diam(diameter_mm: float) -> str:
    """Return a bar diameter without trailing zeros, with a comma

    Args:
        diameter_mm: Bar diameter φ (mm).
    """
    return _comma(f"{round(diameter_mm, 2):g}")


def fmt_steel(name: str) -> str:
    """Return a steel name as written on the sheet, with a hyphen before the class (CA50 → CA-50)"""
    return re.sub(r"^([A-Za-z]+)(\d)", r"\1-\2", name)


def fmt_roman(number: int) -> str:
    """Return a positive integer below 40 in Roman numerals

    Raises:
        ValueError: If the number is not between 1 and 39.
    """
    if not 1 <= number <= 39:
        raise ValueError(f"Roman numerals are only written from 1 to 39. Got {number}.")
    text = ""
    for value, symbol in _ROMAN:
        while number >= value:
            text += symbol
            number -= value
    return text


def fmt_date(date: datetime.date) -> str:
    """Return a date as dd/mm/yyyy"""
    return date.strftime("%d/%m/%Y")


def piece_label(quantity: int, mark: str, diameter_mm: float, length: float) -> str:
    """Return the label of a bar run or clamp set, such as 2 N3 φ12,5 C=170

    Args:
        quantity: Number of pieces.
        mark: Bar mark (N1, N2, …).
        diameter_mm: Bar diameter φ (mm).
        length: Cut length of one piece (cm).
    """
    return f"{quantity} {mark} {PHI}{fmt_diam(diameter_mm)} C={fmt_len(length)}"


def section_piece_label(quantity: int, mark: str, diameter_mm: float) -> str:
    """Return the label of a bar run in a cross section or a shape, such as 2 N10 φ10"""
    return f"{quantity} {mark} {PHI}{fmt_diam(diameter_mm)}"


def bar_paper_mark(is_construction: bool, layer_index: int) -> str | None:
    """Return the note under a bar's label: (MONTAGEM), (2ª CAMADA), …, or None

    Args:
        is_construction: Whether the bar is a construction bar.
        layer_index: Layer of the bar, 0 being the closest to the face.
    """
    if is_construction:
        return CONSTRUCTION_MARK
    if layer_index >= 1:
        return f"({layer_index + 1}ª CAMADA)"
    return None


def spacing_label(mark: str, spacing: float) -> str:
    """Return a stirrup mark and spacing, such as N9 c/17

    Args:
        spacing: Stirrup spacing (cm).
    """
    return f"{mark} c/{fmt_len(spacing)}"


def zone_quantity_label(quantity: int, diameter_mm: float) -> str:
    """Return the stirrup count of a zone, such as 26 φ5"""
    return f"{quantity} {PHI}{fmt_diam(diameter_mm)}"


def cut_length_label(length: float) -> str:
    """Return a cut length, such as C=130

    Args:
        length: Cut length (cm).
    """
    return f"C={fmt_len(length)}"


def section_title(letter: str) -> str:
    """Return a cross section's title, such as CORTE A-A"""
    return f"CORTE {letter}-{letter}"


def scale_label(scale: float) -> str:
    """Return a scale, such as ESC. 1:25"""
    return f"ESC. 1:{fmt_len(scale)}"


def section_letter(index: int) -> str:
    """Return the letter of the cross section at a 0-based index: A, B, …, Z, AA, AB, …"""
    letters = ""
    index += 1
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def text_width(text: str, height: float) -> float:
    """Return a conservative estimate of a text's width, for the layout

    Not measured with any font, so the layout is the same on every machine.

    Args:
        height: Cap height of the text, in any length unit; the width comes in the same unit.
    """
    return len(text) * _TEXT_WIDTH_RATIO * height
