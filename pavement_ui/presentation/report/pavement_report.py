"""The whole pavement's report: a summary, every beam, every slab and the beams' quantities."""

from pavement_ui.core.results.outcomes import DesignSuccess
from pavement_ui.presentation.formatting.numbers import fmt_number
from pavement_ui.presentation.formatting.reinforcement import fmt_bar_diameter
from pavement_ui.presentation.report.beam_report import write_beam_report
from pavement_ui.presentation.report.report_builder import ReportBuilder
from pavement_ui.presentation.report.slab_report import write_slab_report
from pavement_ui.presentation.text.strings import report as s


def _write_quantities(builder: ReportBuilder, success: DesignSuccess) -> None:
    quantities = success.quantities
    builder.heading(s.QUANTITIES, 1, page_break=True)
    builder.paragraph(s.QUANTITIES_TEXT, muted=True)
    builder.table(
        [s.COL_BEAM, s.COL_STEEL, s.COL_CONCRETE, s.COL_FORMWORK],
        [
            *(
                [
                    beam.beam_id,
                    fmt_number(beam.steel_kg, 1),
                    fmt_number(beam.concrete_m3, 3),
                    fmt_number(beam.formwork_m2, 2),
                ]
                for beam in quantities.beams
            ),
            [
                s.TOTAL,
                fmt_number(quantities.steel_kg, 1),
                fmt_number(quantities.concrete_m3, 3),
                fmt_number(quantities.formwork_m2, 2),
            ],
        ],
        bold_rows=(len(quantities.beams),),
    )
    builder.table(
        [s.COL_DIAMETER, s.COL_LENGTH_M, s.COL_MASS],
        [
            *(
                [
                    fmt_bar_diameter(steel.diameter_mm),
                    fmt_number(steel.length_m, 2),
                    fmt_number(steel.mass_kg, 1),
                ]
                for steel in quantities.steel
            ),
            [
                s.TOTAL,
                fmt_number(quantities.steel_length_m, 2),
                fmt_number(quantities.steel_kg, 1),
            ],
        ],
        bold_rows=(len(quantities.steel),),
    )


def write_pavement_report(
    builder: ReportBuilder, success: DesignSuccess, name: str
) -> None:
    """Append the report of every beam, then every slab, each on new pages

    Args:
        name: Project name, for the title.
    """
    builder.heading(s.PAVEMENT_REPORT_TITLE.format(name=name), 1)
    builder.heading(s.PAVEMENT_SUMMARY, 2)
    builder.paragraph(
        s.PAVEMENT_SUMMARY_TEXT.format(
            beams=len(success.beams), slabs=len(success.slabs)
        )
    )
    for beam in success.beams:
        write_beam_report(builder, beam, success, page_break=True)
    for slab in success.slabs:
        write_slab_report(builder, slab, page_break=True)
    _write_quantities(builder, success)
