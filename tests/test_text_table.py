"""Tests for src/text_table.py."""

from src.text_table import format_table


class TestFormatTable:
    """Columns are padded to their widest cell, with no trailing spaces."""

    def test_pads_columns(self) -> None:
        lines = format_table(["A", "Long"], [["wide cell", "x"], ["b", "yy"]], "  ")
        assert lines == [
            "  A          Long",
            "  wide cell  x",
            "  b          yy",
        ], "Each column should be as wide as its widest cell"

    def test_header_only(self) -> None:
        assert format_table(["A", "B"], [], "") == ["A  B"], "No rows, only headers"
