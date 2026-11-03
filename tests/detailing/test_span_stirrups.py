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
