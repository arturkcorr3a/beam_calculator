"""Tests for src/detailing/span_stirrups.py."""

import pytest

from src.detailing.span_stirrups import SpanStirrups
from src.properties.steel import Steel
from src.reinforcement.stirrups import StirrupZone


def _stirrups(*zones: StirrupZone) -> SpanStirrups:
    """Build φ6.3 span stirrups between P1 and P2 with the given zones"""
    return SpanStirrups(
        start_pillar_id="P1",
        end_pillar_id="P2",
        zones=zones,
        diameter_mm=6.3,
        steel=Steel.CA50,
        outer_width=15.0,
        outer_height=55.0,
        cut_length=150.0,
    )


class TestExtent:
    """The stirrups run from the first zone's start to the last zone's end."""

    def test_start_and_end_from_zones(self) -> None:
        stirrups = _stirrups(
            StirrupZone(10.0, 60.0, 12.0), StirrupZone(60.0, 235.0, 24.0)
        )
        assert (stirrups.start, stirrups.end) == (10.0, 235.0), (
            "Extent should come from the outer zones (cm)"
        )


class TestQuantity:
    """Each zone takes as many gaps as its spacing asks for; one stirrup closes the span."""

    def test_exact_division(self) -> None:
        stirrups = _stirrups(StirrupZone(10.0, 235.0, 15.0))
        assert stirrups.zone_quantities == (16,), "225 / 15 = 15 gaps, 16 stirrups"
        assert stirrups.quantity == 16, "One zone is the whole span"

    def test_division_rounds_up(self) -> None:
        stirrups = _stirrups(StirrupZone(10.0, 240.0, 15.0))
        assert stirrups.quantity == 17, "230 / 15 = 15.3 → 16 gaps, 17 stirrups"

    def test_float_drift_adds_no_stirrup(self) -> None:
        stirrups = _stirrups(StirrupZone(10.0, 235.00000001, 15.0))
        assert stirrups.quantity == 16, "225.00000001 cm is still 15 gaps"

    def test_three_zones(self) -> None:
        stirrups = _stirrups(
            StirrupZone(10.0, 61.0, 12.0),
            StirrupZone(61.0, 190.0, 24.0),
            StirrupZone(190.0, 235.0, 12.0),
        )
        assert stirrups.zone_quantities == (5, 6, 5), (
            "51 / 12 → 5, 129 / 24 → 6, 45 / 12 → 4, plus the closing stirrup"
        )
        assert stirrups.quantity == 16, "5 + 6 + 5 stirrups"


class TestValidation:
    """Zones must exist, have length and touch each other."""

    def test_no_zones_raise(self) -> None:
        with pytest.raises(ValueError, match="at least one zone"):
            _stirrups()

    def test_zone_without_length_raises(self) -> None:
        with pytest.raises(ValueError, match="must end after it starts"):
            _stirrups(StirrupZone(60.0, 60.0, 12.0))

    def test_gap_between_zones_raises(self) -> None:
        with pytest.raises(ValueError, match="must touch"):
            _stirrups(StirrupZone(10.0, 60.0, 12.0), StirrupZone(61.0, 235.0, 24.0))

    def test_overlapping_zones_raise(self) -> None:
        with pytest.raises(ValueError, match="must touch"):
            _stirrups(StirrupZone(10.0, 60.0, 12.0), StirrupZone(55.0, 235.0, 24.0))
