"""Tests for src/detailing/bar_schedule.py."""

from dataclasses import replace

from src.detailing.bar_schedule import ScheduleRow, build_schedule, schedule_table
from src.detailing.detailed_bar import DetailedBar
from src.detailing.detailed_clamps import DetailedClamps
from src.detailing.detailing_beam import DetailingBeam
from src.detailing.span_stirrups import SpanStirrups
from src.properties.steel import Steel
from src.reinforcement.stirrups import StirrupZone
from src.structural_elements.support import Support


def _bar(mark: str | None, end: float = 300, quantity: int = 2) -> DetailedBar:
    """Build a straight φ10 run from 0 to the given end (cm)"""
    return DetailedBar(
        diameter_mm=10,
        steel=Steel.CA50,
        quantity=quantity,
        is_bottom=True,
        is_tensioned=True,
        layer_index=0,
        y=4.0,
        start=0,
        end=end,
        mark=mark,
    )


def _beam(*bars: DetailedBar) -> DetailingBeam:
    """Build a detailing beam with the given bars"""
    return DetailingBeam(
        beam_id="V1",
        width=20.0,
        height=60.0,
        nominal_covering=2.5,
        steel=Steel.CA50,
        supports=(Support(0.0, -10.0, 10.0), Support(500.0, 490.0, 510.0)),
        bars=list(bars),
    )


class TestBuildSchedule:
    """The schedule has one row per mark, adding up the pieces."""

    def test_adds_quantities_across_beams(self) -> None:
        rows = build_schedule([_beam(_bar("N1")), _beam(_bar("N1", quantity=3))])
        assert rows == [
            ScheduleRow(
                mark="N1", kind="bar", diameter_mm=10, quantity=5, unit_length=300
            )
        ], "2 + 3 bars of the same mark"
        assert rows[0].total_length == 1500, "5 × 300 cm"

    def test_rows_in_mark_order(self) -> None:
        rows = build_schedule([_beam(_bar("N10", 500), _bar("N2", 400), _bar("N1"))])
        assert [row.mark for row in rows] == ["N1", "N2", "N10"], (
            "Numeric order: N10 comes after N2"
        )

    def test_unmarked_items_left_out(self) -> None:
        assert build_schedule([_beam(_bar(None))]) == [], "No mark, no row"

    def test_clamps(self) -> None:
        beam = _beam()
        beam.clamps = [
            DetailedClamps(
                diameter_mm=12.5,
                steel=Steel.CA50,
                quantity=1,
                width=12,
                leg_length=51,
                left=True,
                is_bottom=True,
                position=3,
                source_position=125,
                mark="N1",
            )
        ]
        row = build_schedule([beam])[0]
        assert (row.kind, row.quantity, row.unit_length) == ("clamp", 1, 114), (
            "One clamp of 2 × 51 + 12 cm"
        )

    def test_stirrups_add_up_across_spans(self) -> None:
        beam = _beam()
        stirrups = SpanStirrups(
            start_pillar_id="P1",
            end_pillar_id="P2",
            zones=(StirrupZone(10.0, 490.0, 15.0),),
            diameter_mm=6.3,
            steel=Steel.CA50,
            outer_width=15.0,
            outer_height=55.0,
            cut_length=150.0,
            mark="N1",
        )
        beam.stirrups = [stirrups, replace(stirrups, start_pillar_id="P2")]
        rows = build_schedule([beam, beam])
        assert len(rows) == 1, "The same stirrup in every span shares a row"
        row = rows[0]
        assert (row.kind, row.unit_length) == ("stirrup", 150.0), "Stirrup, 150 cm"
        assert row.quantity == 4 * 33, "4 spans of 480 / 15 + 1 = 33 stirrups"
        assert row.total_length == 19800, "132 × 150 cm"


class TestScheduleTable:
    """The table shows whole centimeters."""

    def test_empty(self) -> None:
        assert schedule_table([]) == ["  none"], "No rows says none"

    def test_bar_row(self) -> None:
        rows = build_schedule([_beam(_bar("N1"))])
        assert schedule_table(rows)[1].split() == [
            "N1",
            "bar",
            "φ10",
            "2",
            "300",
            "600",
        ], "Mark, kind, diameter, quantity, unit and total lengths"
