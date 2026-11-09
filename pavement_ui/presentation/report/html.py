"""Small HTML pieces of the report, in the subset QTextDocument renders."""

from collections.abc import Sequence
from html import escape

from pavement_ui.presentation.theme import tokens

_TABLE = (
    '<table border="1" cellspacing="0" cellpadding="3" width="100%" '
    f'style="border-color: {tokens.BORDER}; border-style: solid; '
    'margin-top: 4px; margin-bottom: 8px;">'
)
_HEADER_CELL = f'<th style="background-color: {tokens.CHROME_BG};" align="{{align}}">'


def heading(text: str, level: int, page_break: bool = False) -> str:
    """Return a heading; page_break starts it on a new page when printed"""
    style = ' style="page-break-before: always;"' if page_break else ""
    return f"<h{level}{style}>{escape(text)}</h{level}>"


def paragraph(text: str, muted: bool = False) -> str:
    color = f' style="color: {tokens.TEXT_MUTED};"' if muted else ""
    return f"<p{color}>{escape(text)}</p>"


def table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    left_columns: int = 1,
    bold_rows: Sequence[int] = (),
) -> str:
    """Return a table; the first left_columns are left-aligned, the others right-aligned

    Args:
        bold_rows: Indexes of rows written in bold, such as totals.
    """

    def align(index: int) -> str:
        return "left" if index < left_columns else "right"

    parts = [_TABLE, "<tr>"]
    parts += [
        _HEADER_CELL.format(align=align(i)) + escape(h) + "</th>"
        for i, h in enumerate(headers)
    ]
    parts.append("</tr>")
    for row_index, row in enumerate(rows):
        bold = row_index in bold_rows
        parts.append("<tr>")
        for i, cell in enumerate(row):
            text = f"<b>{escape(cell)}</b>" if bold else escape(cell)
            parts.append(f'<td align="{align(i)}">{text}</td>')
        parts.append("</tr>")
    parts.append("</table>")
    return "".join(parts)


def key_values(rows: Sequence[tuple[str, str]]) -> str:
    """Return a two-column table of names and values, without a header"""
    parts = [_TABLE.replace('width="100%"', 'width="60%"')]
    for key, value in rows:
        parts.append(
            f'<tr><td style="background-color: {tokens.CHROME_BG};">{escape(key)}</td>'
            f'<td align="right">{escape(value)}</td></tr>'
        )
    parts.append("</table>")
    return "".join(parts)


def figure_row(images: Sequence[tuple[str, float, float]], caption: str) -> str:
    """Return images side by side, vertically centered, with one caption under them

    Args:
        images: Name, width and height (px) of each image, left to right.
    """
    cells = "".join(
        f'<td align="center" valign="middle"><img src="{name}" '
        f'width="{width:.0f}" height="{height:.0f}"/></td>'
        for name, width, height in images
    )
    return (
        f'<table border="0" cellspacing="0" cellpadding="0" align="center">'
        f"<tr>{cells}</tr></table>"
        f'<p align="center" style="color: {tokens.TEXT_MUTED};"><i>'
        f"{escape(caption)}</i></p>"
    )


def figure(name: str, width_px: float, height_px: float, caption: str) -> str:
    """Return a centered image resource with its caption under it"""
    return (
        f'<p align="center"><img src="{name}" width="{width_px:.0f}" '
        f'height="{height_px:.0f}"/></p>'
        f'<p align="center" style="color: {tokens.TEXT_MUTED};"><i>'
        f"{escape(caption)}</i></p>"
    )
