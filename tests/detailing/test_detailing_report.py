"""Tests for src/detailing/detailing_report.py."""

from src.detailing.detailed_bar import DetailedBar
from src.detailing.detailed_clamps import DetailedClamps
from src.detailing.detailing_beam import DetailingBeam
from src.detailing.detailing_report import build_report
from src.detailing.lap_splice import LapSplice
from src.detailing.span_stirrups import SpanStirrups
from src.properties.steel import Steel
from src.reinforcement.stirrups import StirrupZone
from src.structural_elements.rebar import HookGeometry
from src.structural_elements.support import Support


def _beam() -> DetailingBeam:
    """Build a one-span detailing beam with a hooked bottom run, one clamp set and stirrups in three zones"""
    bar = DetailedBar(
        diameter_mm=16,
        steel=Steel.CA50,
        quantity=2,
        is_bottom=True,
        is_tensioned=True,
        layer_index=0,
        y=4.43,
        start=25.0,
        end=235.0,
        right_hook=HookGeometry(pin_diameter=8.0, tip_length=12.8),
        right_hook_length=14.7,
        source_positions=(125.0,),
    )
    clamps = DetailedClamps(
        diameter_mm=12.5,
        steel=Steel.CA50,
        quantity=1,
        width=12.7,
        leg_length=50.9,
        left=False,
        is_bottom=True,
        position=235.0,
        source_position=125.0,
    )
    stirrups = SpanStirrups(
        start_pillar_id="P1",
        end_pillar_id="P2",
        zones=(
            StirrupZone(10.0, 60.0, 12.0),
            StirrupZone(60.0, 190.0, 24.0),
            StirrupZone(190.0, 240.0, 12.0),
        ),
        diameter_mm=6.3,
        steel=Steel.CA50,
    )
    return DetailingBeam(
        beam_id="V1",
        width=20.0,
        height=60.0,
        nominal_covering=2.5,
        steel=Steel.CA50,
        supports=(Support(0.0, -10.0, 10.0), Support(250.0, 240.0, 260.0)),
        bars=[bar],
        clamps=[clamps],
        stirrups=[stirrups],
    )


class TestBuildReport:
    """The report lists the section, bars of each face, clamps and stirrups."""

    def test_title_and_section(self) -> None:
        report = build_report(_beam())
        assert "Beam V1 — detailing" in report, "The title should name the beam"
        assert "20 x 60 cm" in report, "The section should be listed"
        assert "-10.0 – 260.0 cm" in report, "The extent should be listed"

    def test_bar_row(self) -> None:
        report = build_report(_beam())
        row = next(line for line in report.splitlines() if "2φ16" in line)
        for cell in ("25.0", "235.0", "no", "14.7", "224.7", "main", "125.00"):
            assert cell in row, f"The bar row should show {cell!r}"

    def test_empty_face_says_none(self) -> None:
        lines = build_report(_beam()).splitlines()
        top_index = lines.index("Longitudinal bars — top")
        assert lines[top_index + 1] == "  none", "A face without bars says none"

    def test_clamps_and_stirrups(self) -> None:
        report = build_report(_beam())
        clamp_row = next(line for line in report.splitlines() if "1φ12.5" in line)
        assert "right" in clamp_row, "The clamp row should name its side"
        assert "114.5" in clamp_row, "The clamp row should show 2 × 50.9 + 12.7 cm"
        stirrup_rows = [line for line in report.splitlines() if "φ6.3" in line]
        assert len(stirrup_rows) == 3, "Each stirrup zone should get its own row"
        assert "60.0" in stirrup_rows[1] and "190.0" in stirrup_rows[1], (
            "The middle zone row should show its extent (cm)"
        )
        assert "c/24.0" in stirrup_rows[1], "The middle zone row shows its spacing"

    def test_lap_splices(self) -> None:
        beam = _beam()
        lines = build_report(beam).splitlines()
        assert lines[lines.index("Lap splices") + 1] == "  none", "No laps says none"

        beam.lap_splices = [
            LapSplice(
                is_bottom=True,
                layer_index=0,
                start=266,
                end=333,
                quantity=2,
                diameter_mm=10,
            )
        ]
        row = next(line for line in build_report(beam).splitlines() if "2φ10" in line)
        for cell in ("bottom", "266.0", "333.0", "67.0"):
            assert cell in row, f"The lap row should show {cell!r}"

    def test_merged_sources_listed(self) -> None:
        beam = _beam()
        beam.bars[0].source_positions = (125.0, 400.0)
        row = next(line for line in build_report(beam).splitlines() if "2φ16" in line)
        assert "125.00, 400.00" in row, "A merged run lists both sources"

    def test_detailing_beam_report_delegates(self) -> None:
        beam = _beam()
        assert beam.report() == build_report(beam), (
            "DetailingBeam.report should be the built report"
        )
