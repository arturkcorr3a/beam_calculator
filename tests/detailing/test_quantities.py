"""Tests for src/detailing/quantities.py.

The beam is 20 x 60 cm, with two clear spans of 225 and 300 cm. φ10 weighs 0.61654 kg/m and φ6.3 weighs 0.24470 kg/m.
"""

from src.detailing.clear_span import ClearSpan
from src.detailing.detailed_bar import DetailedBar
from src.detailing.detailed_clamps import DetailedClamps
from src.detailing.detailed_skin_bars import DetailedSkinBars
from src.detailing.detailing_beam import DetailingBeam
from src.detailing.quantities import (
    PavementQuantities,
    build_quantities,
    quantities_table,
)
from src.detailing.span_stirrups import SpanStirrups
from src.properties.steel import Steel
from src.reinforcement.stirrups import StirrupZone
from src.structural_elements.support import Support
from tests.helpers import assert_approx

_PHI_10 = 0.6165375582  # kg/m
_PHI_6_3 = 0.2447  # kg/m, rounded for the checks below


def _bar(mark: str | None, diameter_mm: float = 10, end: float = 300) -> DetailedBar:
    """Build a run of 2 straight bars from 0 to the given end (cm)"""
    return DetailedBar(
        diameter_mm=diameter_mm,
        steel=Steel.CA50,
        quantity=2,
        is_bottom=True,
        is_tensioned=True,
        layer_index=0,
        y=4.0,
        start=0,
        end=end,
        mark=mark,
    )


def _beam(*bars: DetailedBar, beam_id: str = "V1") -> DetailingBeam:
    """Build a detailing beam with spans of 225 cm (a 10 cm slab on one side) and 300 cm (no slab)"""
    return DetailingBeam(
        beam_id=beam_id,
        width=20.0,
        height=60.0,
        nominal_covering=2.5,
        steel=Steel.CA50,
        supports=(
            Support(0.0, -10.0, 10.0),
            Support(250.0, 235.0, 265.0),
            Support(575.0, 565.0, 585.0),
        ),
        bars=list(bars),
        clear_spans=[
            ClearSpan(start=10, end=235, side_heights=(50.0, 60.0)),
            ClearSpan(start=265, end=565, side_heights=(60.0, 60.0)),
        ],
    )


class TestClearSpan:
    """A clear span runs between the pillars' inner faces."""

    def test_length(self) -> None:
        span = ClearSpan(start=10, end=235, side_heights=(60.0, 60.0))
        assert span.length == 225, "235 − 10 cm"


class TestConcrete:
    """The concrete is the section times the clear spans."""

    def test_volume_between_pillar_faces(self) -> None:
        beam = build_quantities([_beam()]).beams[0]
        assert_approx(beam.concrete_m3, 0.63, "0.20 × 0.60 × (2.25 + 3.00) m³")


class TestFormwork:
    """The formwork covers the bottom and the sides left visible."""

    def test_bottom_and_visible_sides(self) -> None:
        beam = build_quantities([_beam()]).beams[0]
        # (20 + 50 + 60) × 225 + (20 + 60 + 60) × 300 = 29250 + 42000 cm²
        assert_approx(
            beam.formwork_m2, 7.125, "Bottom and both sides of each span (m²)"
        )


class TestSteel:
    """The steel comes from the bar schedule, added up by diameter."""

    def test_length_and_mass_of_a_mark(self) -> None:
        beam = build_quantities([_beam(_bar("N1"))]).beams[0]
        assert len(beam.steel) == 1, "One diameter"
        item = beam.steel[0]
        assert item.diameter_mm == 10, "φ10"
        assert_approx(item.length_m, 6.0, "2 bars of 3 m")
        assert_approx(item.mass_kg, 6 * _PHI_10, "6 m of φ10 (kg)", abs_tol=1e-6)

    def test_diameters_sorted_and_added(self) -> None:
        beam = build_quantities(
            [_beam(_bar("N1"), _bar("N2", diameter_mm=6.3), _bar("N3", end=100))]
        ).beams[0]
        assert [item.diameter_mm for item in beam.steel] == [6.3, 10], "Thinnest first"
        assert_approx(beam.steel[1].length_m, 8.0, "6 m + 2 m of φ10")
        assert_approx(
            beam.steel_mass_kg,
            8 * _PHI_10 + 6 * _PHI_6_3,
            "Total mass (kg)",
            abs_tol=1e-3,
        )

    def test_clamps_and_stirrups_count(self) -> None:
        beam = _beam()
        beam.clamps = [
            DetailedClamps(
                diameter_mm=10,
                steel=Steel.CA50,
                quantity=2,
                width=12,
                leg_length=44,
                left=True,
                is_bottom=True,
                position=3,
                source_position=125,
                mark="N1",
            )
        ]
        beam.stirrups = [
            SpanStirrups(
                start_pillar_id="P1",
                end_pillar_id="P2",
                zones=(StirrupZone(10.0, 235.0, 15.0),),
                diameter_mm=10,
                steel=Steel.CA50,
                outer_width=15.0,
                outer_height=55.0,
                cut_length=150.0,
                mark="N2",
            )
        ]
        steel = build_quantities([beam]).beams[0].steel
        assert_approx(
            steel[0].length_m, 2.0 + 24.0, "2 clamps of 1 m + 16 stirrups of 1.5 m"
        )

    def test_unmarked_items_left_out(self) -> None:
        beam = build_quantities([_beam(_bar(None))]).beams[0]
        assert beam.steel == (), "Only the schedule's items count"
        assert beam.steel_mass_kg == 0, "No marks, no mass"


class TestPavementTotals:
    """The pavement adds up its beams."""

    def test_totals(self) -> None:
        quantities = build_quantities(
            [
                _beam(_bar("N1"), beam_id="V1"),
                _beam(_bar("N1"), _bar("N2", diameter_mm=6.3), beam_id="V2"),
            ]
        )
        assert [beam.beam_id for beam in quantities.beams] == ["V1", "V2"], "In order"
        assert [item.diameter_mm for item in quantities.steel] == [6.3, 10], (
            "Steel by diameter across the beams"
        )
        assert_approx(quantities.steel[1].length_m, 12.0, "6 m of φ10 in each beam")
        assert_approx(quantities.concrete_m3, 1.26, "2 × 0.63 m³")
        assert_approx(quantities.formwork_m2, 14.25, "2 × 7.125 m²")

    def test_no_beams(self) -> None:
        quantities = build_quantities([])
        assert quantities == PavementQuantities(beams=(), steel=()), (
            "Nothing to measure"
        )


class TestQuantitiesTable:
    """The table lists the steel by diameter and each beam, with totals."""

    def test_rows(self) -> None:
        lines = quantities_table(build_quantities([_beam(_bar("N1"))]))
        assert lines[1].split() == ["φ10", "6.00", "3.7"], "Length (m) and mass (kg)"
        assert lines[2].split() == ["Total", "6.00", "3.7"], "Steel total"
        assert lines[5].split() == ["V1", "3.7", "0.63", "7.12"], (
            "Steel, concrete and formwork of the beam"
        )
        assert lines[6].split()[0] == "Total", "Totals close the table"


def _skin(
    start: float = 10.0,
    end: float = 235.0,
    diameter_mm: float = 8,
    mark: str | None = None,
) -> DetailedSkinBars:
    """Build the skin bars of span P1–P2: two rows, at 15 and 25 cm"""
    return DetailedSkinBars(
        start_pillar_id="P1",
        end_pillar_id="P2",
        diameter_mm=diameter_mm,
        steel=Steel.CA50,
        heights=(15.0, 25.0),
        start=start,
        end=end,
        mark=mark,
    )


class TestSkinSteel:
    """Skin bars count in the steel through the bar schedule."""

    def test_skin_mass(self) -> None:
        beam = _beam()
        beam.skin_bars = [_skin(mark="N1", diameter_mm=10)]
        item = build_quantities([beam]).beams[0].steel[0]
        assert_approx(item.length_m, 9.0, "4 bars of 2.25 m")
        assert_approx(item.mass_kg, 9 * _PHI_10, "9 m of φ10 (kg)", abs_tol=1e-6)
