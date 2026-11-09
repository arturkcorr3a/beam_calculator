"""Section 4.6 of the beam report: the longitudinal bars, mark by mark."""

from pavement_ui.core.results.beam_design import BarEntry
from pavement_ui.presentation.formatting.numbers import fmt_length_cm, fmt_number
from pavement_ui.presentation.formatting.reinforcement import fmt_bar_diameter
from pavement_ui.presentation.report.report_builder import ReportBuilder
from pavement_ui.presentation.text.strings import formatting as f
from pavement_ui.presentation.text.strings import report as s

_CM_PER_M = 100.0


def _face(bar: BarEntry) -> str:
    face = s.FACE_BOTTOM if bar.bottom else s.FACE_TOP
    if bar.construction:
        return s.FACE_CONSTRUCTION.format(face=face)
    return s.FACE_LAYER.format(face=face, layer=bar.layer)


def _hooks(bar: BarEntry) -> str:
    sides = [
        template.format(value=fmt_length_cm(length))
        for template, length in (
            (f.SIDE_LEFT, bar.left_hook_cm),
            (f.SIDE_RIGHT, bar.right_hook_cm),
        )
        if length > 0
    ]
    return f.SIDE_JOIN.join(sides) if sides else f.NONE


def _row(bar: BarEntry) -> list[str]:
    return [
        bar.mark,
        f"{bar.quantity}{f.PHI}{fmt_bar_diameter(bar.diameter_mm)}",
        _face(bar),
        fmt_number(bar.center_m, 2),
        fmt_number((bar.center_m - bar.start_m) * _CM_PER_M, 1),
        fmt_number((bar.end_m - bar.center_m) * _CM_PER_M, 1),
        _hooks(bar),
        fmt_number(bar.total_length_cm, 1),
    ]


def write_bars(builder: ReportBuilder, bars: tuple[BarEntry, ...]) -> None:
    """Append the table of the beam's longitudinal bar runs; nothing before detailing"""
    if not bars:
        return
    builder.heading(s.BARS, 3)
    builder.paragraph(s.BARS_TEXT, muted=True)
    builder.table(
        [
            s.COL_MARK,
            s.COL_BARS,
            s.COL_FACE,
            s.COL_CENTER,
            s.COL_LEFT,
            s.COL_RIGHT,
            s.COL_HOOKS,
            s.COL_CUT,
        ],
        [_row(bar) for bar in bars],
        left_columns=3,
    )
