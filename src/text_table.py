def format_table(headers: list[str], rows: list[list[str]], indent: str) -> list[str]:
    """Lay out rows under headers in left-aligned columns, each padded to its widest cell

    Args:
        headers: Column titles.
        rows: Cells of each row, one per column.
        indent: Prefix of every line.

    Returns:
        The header line followed by one line per row, without trailing spaces.
    """
    widths = [
        max(len(cell) for cell in column)
        for column in zip(headers, *rows, strict=False)
    ]
    return [
        indent
        + "  ".join(
            cell.ljust(width) for cell, width in zip(row, widths, strict=True)
        ).rstrip()
        for row in [headers, *rows]
    ]
