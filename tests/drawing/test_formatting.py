"""Tests for src/drawing/formatting.py and src/drawing/config.py."""

import datetime

import pytest

from src.drawing.config import DrawingConfig, paper
from src.drawing.formatting import (
    bar_paper_mark,
    cut_length_label,
    fmt_date,
    fmt_dec,
    fmt_diam,
    fmt_len,
    fmt_roman,
    fmt_steel,
    piece_label,
    scale_label,
    section_letter,
    section_piece_label,
    section_title,
    spacing_label,
    text_width,
    zone_quantity_label,
)
from src.errors import EnginePreconditionError
from tests.drawing.helpers import close


class TestNumbers:
    """Numbers use a decimal comma and drop needless decimals."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (411.0, "411"),
            (1858.5, "1858,5"),
            (12.36, "12,4"),
            (129.96, "130"),
            (-19.5, "-19,5"),
        ],
    )
    def test_fmt_len(self, value: float, expected: str) -> None:
        assert fmt_len(value) == expected, f"{value} cm should read {expected}"

    def test_fmt_dec(self) -> None:
        assert fmt_dec(118.66) == "118,7", "One decimal by default, with a comma"
        assert fmt_dec(9.2134, 2) == "9,21", "Two decimals when asked"

    @pytest.mark.parametrize(
        ("diameter", "expected"),
        [(10.0, "10"), (10, "10"), (12.5, "12,5"), (6.3, "6,3")],
    )
    def test_fmt_diam(self, diameter: float, expected: str) -> None:
        assert fmt_diam(diameter) == expected, f"φ{diameter} should read {expected}"

    def test_fmt_steel(self) -> None:
        assert fmt_steel("CA50") == "CA-50", "A hyphen goes before the class"
        assert fmt_steel("CA-60") == "CA-60", "An existing hyphen is kept"

    @pytest.mark.parametrize(("number", "expected"), [(1, "I"), (2, "II"), (4, "IV")])
    def test_fmt_roman(self, number: int, expected: str) -> None:
        assert fmt_roman(number) == expected, f"{number} should read {expected}"

    def test_fmt_roman_out_of_range(self) -> None:
        with pytest.raises(EnginePreconditionError, match="Roman"):
            fmt_roman(0)

    def test_fmt_date(self) -> None:
        assert fmt_date(datetime.date(2026, 11, 7)) == "07/11/2026", "dd/mm/yyyy"


class TestLabels:
    """Labels follow the table of spec §4.2."""

    def test_piece_label(self) -> None:
        assert piece_label(2, "N3", 12.5, 170.0) == "2 N3 φ12,5 C=170", (
            "Quantity, mark, diameter and cut length"
        )

    def test_section_piece_label(self) -> None:
        assert section_piece_label(2, "N10", 10.0) == "2 N10 φ10", "No cut length"

    @pytest.mark.parametrize(
        ("construction", "layer", "expected"),
        [(True, 0, "(MONTAGEM)"), (False, 1, "(2ª CAMADA)"), (False, 0, None)],
    )
    def test_bar_paper_mark(
        self, construction: bool, layer: int, expected: str | None
    ) -> None:
        assert bar_paper_mark(construction, layer) == expected, "Paper mark per role"

    def test_stirrup_zone(self) -> None:
        assert spacing_label("N9", 17.0) == "N9 c/17", "Text over the zone line"
        assert zone_quantity_label(26, 5.0) == "26 φ5", "Text under the zone line"
        assert cut_length_label(130.0) == "C=130", "Cut length of a shape"

    def test_section_titles(self) -> None:
        assert section_title("A") == "CORTE A-A", "Section title"
        assert scale_label(25) == "ESC. 1:25", "Section scale"

    @pytest.mark.parametrize(("index", "letter"), [(0, "A"), (25, "Z"), (26, "AA")])
    def test_section_letter(self, index: int, letter: str) -> None:
        assert section_letter(index) == letter, f"Section {index} is {letter}"

    def test_text_width(self) -> None:
        assert close(text_width("ABCD", 2.0), 7.2), "0.9 × height per char"


class TestPaper:
    """Paper lengths (mm) convert to model lengths (cm) at the sheet scale."""

    def test_paper(self) -> None:
        assert paper(2.5) == 12.5, "2.5 mm at 1:50 is 12.5 cm"

    def test_config_paper_and_magnification(self) -> None:
        config = DrawingConfig()
        assert config.paper(10.0) == 50.0, "10 mm at 1:50 is 50 cm"
        assert config.section_magnification == 2.0, "Sections at 1:25 on a 1:50 sheet"
