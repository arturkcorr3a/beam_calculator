"""Tests for src/calculators/lap_splice_calculator.py.

Every case uses CA-50 in C30 (f_ctd = 0.14482 kN/cm²). In a good bond zone, f_bd = 0.32585 kN/cm² and l_b = 33.357φ; in a poor one, l_b = 47.653φ.
"""

import pytest

from src.calculators.lap_splice_calculator import (
    alpha_0t,
    compression_lap_length,
    construction_lap_length,
    tension_lap_length,
)
from src.config import APP_CONFIG
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from tests.helpers import assert_approx


@pytest.fixture(autouse=True)
def pinned_concrete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the project concrete to C30 for every test in this module"""
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C30)


class TestAlpha0t:
    """α_0t follows Table 9.4, taking the next column for shares in between."""

    @pytest.mark.parametrize(
        ("share", "expected"),
        [
            (0.0, 1.2),
            (0.20, 1.2),
            (0.21, 1.4),
            (0.25, 1.4),
            (0.30, 1.6),
            (1 / 3, 1.6),
            (0.34, 1.8),
            (0.50, 1.8),
            (0.51, 2.0),
            (1.0, 2.0),
        ],
    )
    def test_table_9_4(self, share: float, expected: float) -> None:
        assert alpha_0t(share) == expected, f"α_0t for {share:.0%} spliced"


class TestTensionLapLength:
    """l_0t = α_0t l_b,nec, at least 0.3 α_0t l_b, 15φ and 20 cm."""

    def test_all_spliced_in_good_zone(self) -> None:
        assert_approx(
            tension_lap_length(10, Steel.CA50, True, area_ratio=1.0, share=1.0),
            66.71460023518753,
            "φ10: 2.0 × 33.357 cm",
        )

    def test_few_spliced(self) -> None:
        assert_approx(
            tension_lap_length(10, Steel.CA50, True, area_ratio=1.0, share=0.2),
            40.02876014111252,
            "φ10, 20 % spliced: 1.2 × 33.357 cm",
        )

    def test_poor_bond_zone(self) -> None:
        assert_approx(
            tension_lap_length(10, Steel.CA50, False, area_ratio=1.0, share=1.0),
            95.30657176455362,
            "φ10 in a poor zone: 2.0 × 47.653 cm",
        )

    def test_minimum_from_basic_length(self) -> None:
        assert_approx(
            tension_lap_length(10, Steel.CA50, True, area_ratio=0.1, share=1.0),
            20.01438007055626,
            "φ10 with A_s,calc/A_s,ef = 0.1: 0.3 × 2.0 × 33.357 cm governs",
        )

    def test_minimum_fifteen_diameters(self) -> None:
        assert_approx(
            tension_lap_length(16, Steel.CA50, True, area_ratio=0.1, share=0.2),
            24.0,
            "φ16 with a small ratio and α_0t = 1.2: 15φ = 24 cm governs",
        )

    def test_minimum_twenty_centimeters(self) -> None:
        assert_approx(
            tension_lap_length(6.3, Steel.CA50, True, area_ratio=0.1, share=1.0),
            20.0,
            "φ6.3 with a small ratio: 20 cm governs",
        )


class TestCompressionLapLength:
    """l_0c = l_b,nec, at least 0.6 l_b, 15φ and 20 cm."""

    def test_necessary_length_governs(self) -> None:
        assert_approx(
            compression_lap_length(10, Steel.CA50, True, area_ratio=1.0),
            33.357300117593766,
            "φ10: l_b,nec = l_b = 33.357 cm",
        )

    def test_minimum_from_basic_length(self) -> None:
        assert_approx(
            compression_lap_length(10, Steel.CA50, True, area_ratio=0.1),
            20.01438007055626,
            "φ10 with a small ratio: 0.6 × 33.357 cm governs",
        )


class TestConstructionLapLength:
    """Construction bars lap by l_0c,min: the greatest of 0.6 l_b, 15φ and 20 cm."""

    def test_basic_length_governs(self) -> None:
        assert_approx(
            construction_lap_length(12.5, Steel.CA50, True),
            25.01797508819532,
            "φ12.5: 0.6 × 41.697 cm",
        )

    def test_twenty_centimeters_govern(self) -> None:
        assert_approx(
            construction_lap_length(6.3, Steel.CA50, True),
            20.0,
            "φ6.3: 0.6 × 21.0 = 12.6 cm < 20 cm",
        )
