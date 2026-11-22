"""Unit tests for src.data.sinapi_2026_10.steel_prices.model (SteelPrice, SteelPriceTable)."""

import pytest

from src.data.sinapi_2026_10.steel_prices.data import STEEL_PRICES
from src.errors import SteelPriceNotFoundError
from src.properties.steel import Steel


class TestPriceFor:
    """Cut and bent bars are preferred; straight rebar fills the gaps."""

    @pytest.mark.parametrize(
        ("diameter_mm", "code", "price"),
        [
            (6.3, 34449, 9.31),
            (10.0, 43058, 7.90),
            (12.5, 43058, 7.90),
            (16.0, 43058, 7.90),
            (20.0, 43058, 7.90),
        ],
    )
    def test_ca50_cut_and_bent(
        self, diameter_mm: float, code: int, price: float
    ) -> None:
        item = STEEL_PRICES.price_for(Steel.CA50, diameter_mm)
        assert item.code == code, f"φ{diameter_mm} should come cut and bent"
        assert item.price_per_kg == price, f"SINAPI {code} costs R$ {price}/kg"

    @pytest.mark.parametrize(
        ("diameter_mm", "code", "price"),
        [(8.0, 33, 8.42), (25.0, 43056, 7.93), (32.0, 43057, 8.71)],
    )
    def test_ca50_falls_back_to_rebar(
        self, diameter_mm: float, code: int, price: float
    ) -> None:
        item = STEEL_PRICES.price_for(Steel.CA50, diameter_mm)
        assert item.code == code, f"φ{diameter_mm} has no cut-and-bent item"
        assert not item.cut_and_bent, "the fallback is straight rebar"
        assert item.price_per_kg == price, f"SINAPI {code} costs R$ {price}/kg"

    def test_ca60_cut_and_bent(self) -> None:
        assert STEEL_PRICES.price_for(Steel.CA60, 5.0).code == 43061, "CA-60 φ5"

    def test_ca25_rebar(self) -> None:
        assert STEEL_PRICES.price_for(Steel.CA25, 16.0).code == 43054, "CA-25 φ16"

    def test_grade_must_match(self) -> None:
        item = STEEL_PRICES.price_for(Steel.CA60, 8.0)
        assert item.code == 43060, "CA-60 φ8 is not priced as CA-50 φ8"

    @pytest.mark.parametrize(
        ("steel", "diameter_mm"),
        [(Steel.CA50, 22.0), (Steel.CA50, 40.0), (Steel.CA60, 10.0)],
    )
    def test_unpriced_diameter_raises(self, steel: Steel, diameter_mm: float) -> None:
        with pytest.raises(SteelPriceNotFoundError, match="No SINAPI price"):
            STEEL_PRICES.price_for(steel, diameter_mm)


class TestCoversAvailableSizes:
    """The budget prices every size the engine can choose."""

    @pytest.mark.parametrize(
        ("steel", "diameter_mm"),
        [(steel, size) for steel in Steel for size in steel.available_sizes],
    )
    def test_available_size_has_a_price(self, steel: Steel, diameter_mm: float) -> None:
        item = STEEL_PRICES.price_for(steel, diameter_mm)
        assert item.price_per_kg > 0, f"{steel.name} φ{diameter_mm:g} needs a price"
