"""The beams' budget: price references, steel by diameter, concrete and total."""

from pavement_ui.core.results.budget import BudgetResult
from pavement_ui.presentation.formatting.numbers import fmt_money, fmt_number
from pavement_ui.presentation.formatting.reinforcement import fmt_bar_diameter
from pavement_ui.presentation.report.report_builder import ReportBuilder
from pavement_ui.presentation.text.option_labels import OptionKind, label
from pavement_ui.presentation.text.strings import report as s


def _write_references(builder: ReportBuilder, budget: BudgetResult) -> None:
    builder.heading(s.BUDGET_REFERENCES, 2)
    builder.key_values(
        [
            (s.ROW_STEEL, s.STEEL_REFERENCE.format(reference=budget.steel_reference)),
            (
                s.ROW_CONCRETE,
                s.CONCRETE_REFERENCE.format(
                    date=budget.priced_at.strftime(s.DATE_TIME_FORMAT)
                ),
            ),
        ]
    )


def _write_steel(builder: ReportBuilder, budget: BudgetResult) -> None:
    builder.heading(
        s.BUDGET_STEEL.format(grade=label(OptionKind.STEEL, budget.steel_grade)), 2
    )
    builder.paragraph(s.BUDGET_STEEL_TEXT, muted=True)
    rows = [
        [
            fmt_bar_diameter(line.diameter_mm),
            str(line.sinapi_code),
            line.description,
            fmt_number(line.mass_kg, 2),
            fmt_number(line.price_per_kg, 2),
            fmt_number(line.cost, 2),
        ]
        for line in budget.steel
    ]
    rows.append(
        [
            s.TOTAL,
            "",
            "",
            fmt_number(sum(line.mass_kg for line in budget.steel), 2),
            "",
            fmt_number(budget.steel_cost, 2),
        ]
    )
    builder.table(
        [
            s.COL_DIAMETER,
            s.COL_SINAPI,
            s.COL_DESCRIPTION,
            s.COL_MASS,
            s.COL_PRICE_KG,
            s.COL_COST,
        ],
        rows,
        left_columns=3,
        bold_rows=[len(rows) - 1],
    )


def _write_concrete(builder: ReportBuilder, budget: BudgetResult) -> None:
    builder.heading(s.BUDGET_CONCRETE, 2)
    builder.table(
        [s.COL_CLASS, s.COL_VOLUME, s.COL_PRICE_M3, s.COL_COST],
        [
            [
                label(OptionKind.CONCRETE, budget.concrete_class),
                fmt_number(budget.concrete_m3, 3),
                fmt_number(budget.concrete_price_per_m3, 2),
                fmt_number(budget.concrete_cost, 2),
            ]
        ],
    )


def _write_summary(builder: ReportBuilder, budget: BudgetResult) -> None:
    builder.heading(s.BUDGET_SUMMARY, 2)
    builder.table(
        [s.COL_ITEM, s.COL_COST],
        [
            [s.ROW_STEEL, fmt_money(budget.steel_cost)],
            [s.ROW_CONCRETE, fmt_money(budget.concrete_cost)],
            [s.TOTAL, fmt_money(budget.total)],
        ],
        bold_rows=[2],
    )


def write_budget_report(
    builder: ReportBuilder, budget: BudgetResult, name: str
) -> None:
    """Append the budget to the builder

    Args:
        name: Pavement name, for the title.
    """
    builder.heading(s.BUDGET_REPORT_TITLE.format(name=name), 1)
    builder.paragraph(s.BUDGET_TEXT, muted=True)
    _write_references(builder, budget)
    _write_steel(builder, budget)
    _write_concrete(builder, budget)
    _write_summary(builder, budget)
